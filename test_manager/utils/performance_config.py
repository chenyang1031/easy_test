"""
性能测试 extra_config / 阶段负载 / 断言 的配置校验（阶段2 单机增强）。

设计目标：尽量少改表结构，复杂配置放入 extra_config JSON；
阶段3 分布式可在任务层增加 worker 列表等字段，与本模块校验独立扩展。
"""
from __future__ import annotations

from typing import Any

# 单 CSV 文件大小上限（字节）
PERF_CSV_MAX_BYTES = 10 * 1024 * 1024

# 支持的断言操作符（与文档《性能测试阶段2单机增强配置说明》一致）
ASSERTION_OPS = frozenset({"eq", "ne", "gt", "ge", "lt", "le", "not_null", "contains"})

# CSV 读取策略
CSV_STRATEGY_PER_USER = "per_user"
CSV_STRATEGY_PER_ITERATION = "per_iteration"
CSV_STRATEGIES = frozenset({CSV_STRATEGY_PER_USER, CSV_STRATEGY_PER_ITERATION})


class PerformanceConfigError(ValueError):
    """性能任务配置非法"""


def validate_assertions_config(extra_config: dict | None) -> list[dict[str, Any]]:
    """
    校验 extra_config['assertions']，返回规范化后的断言列表。
    无 assertions 时返回 []（兼容旧任务：仅 HTTP 状态码判定）。
    """
    if not extra_config:
        return []
    raw = extra_config.get("assertions")
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise PerformanceConfigError("extra_config.assertions 必须为数组")
    out: list[dict[str, Any]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise PerformanceConfigError(f"assertions[{i}] 必须为对象")
        jp = item.get("jsonpath")
        op = item.get("op")
        if not jp or not isinstance(jp, str):
            raise PerformanceConfigError(f"assertions[{i}].jsonpath 必填且为字符串")
        if not op or op not in ASSERTION_OPS:
            raise PerformanceConfigError(
                f"assertions[{i}].op 非法，支持: {', '.join(sorted(ASSERTION_OPS))}"
            )
        if op != "not_null" and "expect" not in item:
            raise PerformanceConfigError(f"assertions[{i}] 在 op={op} 时必须提供 expect")
        row = {"jsonpath": jp.strip(), "op": op, "expect": item.get("expect")}
        out.append(row)
    return out


def validate_stages_config(
    stages: list | None,
    run_time: int,
) -> list[dict[str, int]]:
    """
    校验多阶段负载配置；无 stages 时返回 []（使用 total_users/spawn_rate/run_time）。
    规则：每阶段 duration_sec/users/spawn_rate 为正整数；所有阶段 duration_sec 之和等于 run_time。
    """
    if stages is None:
        return []
    if not isinstance(stages, list):
        raise PerformanceConfigError("extra_config.stages 必须为数组")
    if len(stages) == 0:
        return []
    normalized: list[dict[str, int]] = []
    total_dur = 0
    for i, st in enumerate(stages):
        if not isinstance(st, dict):
            raise PerformanceConfigError(f"stages[{i}] 必须为对象")
        try:
            d = int(st["duration_sec"])
            u = int(st["users"])
            sp = int(st["spawn_rate"])
        except (KeyError, TypeError, ValueError) as e:
            raise PerformanceConfigError(
                f"stages[{i}] 需包含正整数 duration_sec/users/spawn_rate: {e}"
            ) from e
        if d <= 0 or u <= 0 or sp <= 0:
            raise PerformanceConfigError(
                f"stages[{i}] 的 duration_sec/users/spawn_rate 必须为正整数"
            )
        total_dur += d
        normalized.append({"duration_sec": d, "users": u, "spawn_rate": sp})
    if run_time <= 0:
        raise PerformanceConfigError("run_time 必须为正整数")
    if total_dur != run_time:
        raise PerformanceConfigError(
            f"阶段 duration_sec 之和 ({total_dur}) 必须等于 run_time ({run_time})"
        )
    return normalized


def validate_think_time_ms(extra_config: dict | None) -> int:
    if not extra_config:
        return 0
    v = extra_config.get("think_time_ms", 0)
    try:
        n = int(v)
    except (TypeError, ValueError):
        raise PerformanceConfigError("think_time_ms 必须为整数") from None
    if n < 0:
        raise PerformanceConfigError("think_time_ms 不能为负数")
    return n


def validate_csv_read_strategy(extra_config: dict | None) -> str:
    if not extra_config:
        return CSV_STRATEGY_PER_ITERATION
    s = extra_config.get("csv_read_strategy", CSV_STRATEGY_PER_ITERATION)
    if s not in CSV_STRATEGIES:
        raise PerformanceConfigError(
            f"csv_read_strategy 必须为 {CSV_STRATEGY_PER_USER} 或 {CSV_STRATEGY_PER_ITERATION}"
        )
    return s


def validate_extra_config_for_task(extra_config: dict | None, run_time: int) -> dict[str, Any]:
    """
    任务保存或执行前统一校验 extra_config。
    返回解析结果摘要，供执行器使用（避免重复解析）。
    """
    ec = extra_config or {}
    validate_assertions_config(ec)
    stages = ec.get("stages")
    stages_norm = validate_stages_config(stages, run_time) if stages is not None else []
    validate_think_time_ms(ec)
    validate_csv_read_strategy(ec)
    return {
        "assertions": validate_assertions_config(ec),
        "stages": stages_norm,
        "think_time_ms": validate_think_time_ms(ec),
        "csv_read_strategy": validate_csv_read_strategy(ec),
    }


def validate_csv_file_size(uploaded) -> None:
    """上传接口校验 CSV 文件大小（Django UploadedFile 或 FileField）。"""
    if not uploaded:
        return
    size = getattr(uploaded, "size", None)
    if size is not None and size > PERF_CSV_MAX_BYTES:
        raise PerformanceConfigError(
            f"CSV 文件大小不能超过 {PERF_CSV_MAX_BYTES // (1024 * 1024)}MB"
        )
