# -*- coding: utf-8 -*-
"""
Apifox 项目导出 JSON 中的「环境 / 环境变量」解析与导入。

平台侧使用 Environment.variables（JSONField）存储键值，说明文案写入 __var_descriptions__，
与 env_variables_compat / 前端 Environment 表单约定一致。无独立 EnvironmentVariable 表。

仅导入「启用」的变量；禁用项跳过，不写入数据库。
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Tuple

from test_manager.env_variables_compat import ENV_VAR_DESCRIPTIONS_KEY, variables_for_runtime
from test_manager.models import Environment, Project


def empty_apifox_environment_import_stats(skip_reason: str) -> Dict[str, Any]:
    """无导入或跳过时的统一统计结构（与 apply_apifox_environment_import 返回字段对齐）。"""
    return {
        "applied": False,
        "skipped": True,
        "skip_reason": skip_reason,
        "environments": [],
        "totals": {
            "imported_total": 0,
            "overwritten": 0,
            "new": 0,
            "environments_created": 0,
            "environments_reused": 0,
        },
    }


# Apifox 导出中环境列表的常见键名（不同版本可能只含其一）
_ENVIRONMENT_ROOT_KEYS = ("environments", "environmentList", "environment")


def _normalize_base_url(raw: Any) -> str:
    """将 Apifox 中的服务地址规范为 Django URLField 可接受的字符串。"""
    s = str(raw or "").strip()
    if not s:
        return "http://localhost"
    if "://" not in s:
        return "http://" + s.lstrip("/")
    return s


def _extract_environment_base_url(env_obj: Dict[str, Any]) -> str:
    """从单个 Apifox 环境对象中推断 base_url（用于新建 Environment）。"""
    for key in ("baseUrl", "baseURL", "preUrl", "hostUrl", "url"):
        v = env_obj.get(key)
        if v:
            return _normalize_base_url(v)
    servers = env_obj.get("servers") or env_obj.get("urls") or env_obj.get("services")
    if isinstance(servers, list) and servers:
        s0 = servers[0]
        if isinstance(s0, dict):
            u = s0.get("url") or s0.get("baseUrl") or s0.get("baseURL")
            if u:
                return _normalize_base_url(u)
    return "http://localhost"


def _coerce_bool_enabled(row: Dict[str, Any]) -> bool:
    """解析 Apifox 变量是否启用：enabled / enable / isDisabled 等。"""
    if "enabled" in row:
        return bool(row.get("enabled"))
    if "enable" in row:
        return bool(row.get("enable"))
    if "isDisabled" in row:
        return not bool(row.get("isDisabled"))
    if "disabled" in row:
        return not bool(row.get("disabled"))
    # 未声明时默认启用（与 Apifox 常见行为一致）
    return True


def _variable_value_from_row(row: Dict[str, Any]) -> Any:
    """变量值：优先 value，其次 initialValue / defaultValue。"""
    if "value" in row and row["value"] is not None:
        return row.get("value")
    if "initialValue" in row and row["initialValue"] is not None:
        return row.get("initialValue")
    if "defaultValue" in row and row["defaultValue"] is not None:
        return row.get("defaultValue")
    return ""


def _iter_apifox_environment_dicts(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从 Apifox 根对象收集环境定义列表。"""
    out: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return out

    for root_key in _ENVIRONMENT_ROOT_KEYS:
        block = data.get(root_key)
        if isinstance(block, list):
            for item in block:
                if isinstance(item, dict):
                    out.append(item)
        elif isinstance(block, dict):
            out.append(block)

    # 少数导出将环境嵌在 projectSetting 下
    ps = data.get("projectSetting")
    if isinstance(ps, dict):
        for root_key in _ENVIRONMENT_ROOT_KEYS:
            block = ps.get(root_key)
            if isinstance(block, list):
                for item in block:
                    if isinstance(item, dict):
                        out.append(item)
            elif isinstance(block, dict):
                out.append(block)

    return out


def _normalize_variable_rows(raw_variables: Any) -> List[Dict[str, Any]]:
    """
    将 Apifox 的 variables 规范为统一结构。
    支持 list[dict] 或 dict（少见）两种形态。
    """
    rows: List[Dict[str, Any]] = []
    if isinstance(raw_variables, dict):
        iterable = [{"name": k, "value": v} for k, v in raw_variables.items()]
    elif isinstance(raw_variables, list):
        iterable = raw_variables
    else:
        return rows

    for row in iterable:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or row.get("key") or row.get("id") or "").strip()
        if not name or name == ENV_VAR_DESCRIPTIONS_KEY:
            continue
        enabled = _coerce_bool_enabled(row)
        value = _variable_value_from_row(row)
        description = str(row.get("description") or row.get("desc") or "").strip()
        rows.append(
            {
                "name": name,
                "value": value,
                "description": description,
                "enabled": enabled,
            }
        )
    return rows


def parse_apifox_environments_from_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    解析 Apifox 导出 JSON，返回可序列化载荷（供预览返回、确认回传或从文件二次解析）。

    Returns:
        {
          "environments": [
            {
              "name": str,
              "base_url": str,
              "variables": [
                 {"name", "value", "description", "enabled"}  # enabled 仅用于过滤前展示
              ]
            },
            ...
          ]
        }
    """
    result: List[Dict[str, Any]] = []
    for env_obj in _iter_apifox_environment_dicts(data):
        name = str(
            env_obj.get("name")
            or env_obj.get("title")
            or env_obj.get("label")
            or env_obj.get("id")
            or ""
        ).strip()
        if not name:
            continue
        base_url = _extract_environment_base_url(env_obj)
        variables = _normalize_variable_rows(env_obj.get("variables"))
        result.append(
            {
                "name": name,
                "base_url": base_url,
                "variables": variables,
            }
        )

    return {"environments": result}


def _split_descriptions(variables: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """从 Environment.variables 中拆出运行时变量与说明表。"""
    if not isinstance(variables, dict):
        return {}, {}
    merged = copy.deepcopy(variables)
    desc = merged.pop(ENV_VAR_DESCRIPTIONS_KEY, None)
    if isinstance(desc, dict):
        descriptions = {str(k): str(v) for k, v in desc.items()}
    else:
        descriptions = {}
    return merged, descriptions


def _import_row_is_enabled(row: Dict[str, Any]) -> bool:
    """与解析阶段一致：缺省为启用。"""
    if "enabled" in row:
        return bool(row.get("enabled"))
    if "enable" in row:
        return bool(row.get("enable"))
    return True


def _merge_variables_into_environment(
    env: Environment,
    import_rows: List[Dict[str, Any]],
) -> Dict[str, int]:
    """
    将 Apifox 导入行合并进已有 Environment.variables。
    规则：仅处理启用行；同名覆盖；新名追加；未出现在导入中的旧键保留。

    Returns:
        imported_total, overwritten, new_added
    """
    enabled_rows = [r for r in import_rows if _import_row_is_enabled(r)]
    if not enabled_rows:
        return {"imported_total": 0, "overwritten": 0, "new": 0}

    current = env.variables if isinstance(env.variables, dict) else {}
    runtime_before, descriptions_before = _split_descriptions(current)
    existing_keys = set(variables_for_runtime(runtime_before).keys())

    imported_total = 0
    overwritten = 0
    new_added = 0

    merged_values = copy.deepcopy(runtime_before)
    descriptions = copy.deepcopy(descriptions_before)

    for row in enabled_rows:
        key = row["name"]
        val = row.get("value")
        desc_text = str(row.get("description") or "")

        imported_total += 1
        if key in existing_keys:
            overwritten += 1
        else:
            new_added += 1
            existing_keys.add(key)

        merged_values[key] = val
        descriptions[key] = desc_text

    # 清理无变量的说明项（可选一致性）
    for k in list(descriptions.keys()):
        if k not in merged_values:
            descriptions.pop(k, None)

    out: Dict[str, Any] = copy.deepcopy(merged_values)
    if descriptions:
        out[ENV_VAR_DESCRIPTIONS_KEY] = descriptions

    env.variables = out
    env.save(update_fields=["variables", "updated_at"])

    return {
        "imported_total": imported_total,
        "overwritten": overwritten,
        "new": new_added,
    }


def apply_apifox_environment_import(
    platform_project: Project,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    将 parse_apifox_environments_from_json（或等价结构）写入平台 Environment。

    Args:
        platform_project: 平台项目（Environment.project 外键）
        payload: {"environments": [ {...}, ... ]}

    Returns:
        统计信息字典，便于 API 响应。
    """
    if not isinstance(payload, dict):
        st = empty_apifox_environment_import_stats("invalid_payload")
        st["skipped"] = True
        return st

    env_list = payload.get("environments")
    if not isinstance(env_list, list) or not env_list:
        st = empty_apifox_environment_import_stats("no_environments_in_payload")
        st["applied"] = True
        return st

    # 合并导出中重复的同名环境块：变量行按顺序拼接，后者覆盖前者（与单次合并逻辑一致）
    merged_blocks: Dict[str, Dict[str, Any]] = {}
    block_order: List[str] = []
    for block in env_list:
        if not isinstance(block, dict):
            continue
        blk_name = str(block.get("name") or "").strip()
        if not blk_name:
            continue
        base_url = str(block.get("base_url") or "").strip() or "http://localhost"
        base_url = _normalize_base_url(base_url)
        variables = block.get("variables")
        if not isinstance(variables, list):
            variables = []
        if blk_name not in merged_blocks:
            merged_blocks[blk_name] = {"name": blk_name, "base_url": base_url, "variables": []}
            block_order.append(blk_name)
        merged_blocks[blk_name]["variables"].extend(variables)
        # 保留最后一次出现的 base_url（更接近用户在 Apifox 中的最终选择）
        merged_blocks[blk_name]["base_url"] = base_url

    totals = {"imported_total": 0, "overwritten": 0, "new": 0, "environments_created": 0, "environments_reused": 0}
    details: List[Dict[str, Any]] = []

    for name in block_order:
        block = merged_blocks[name]
        base_url = str(block.get("base_url") or "").strip() or "http://localhost"
        base_url = _normalize_base_url(base_url)
        variables = block.get("variables") or []

        env_obj = Environment.objects.filter(project=platform_project, name=name).first()
        created = False
        if env_obj is None:
            env_obj = Environment.objects.create(
                name=name[:100],
                project=platform_project,
                base_url=base_url,
                variables={},
            )
            created = True
            totals["environments_created"] += 1
        else:
            totals["environments_reused"] += 1

        counts = _merge_variables_into_environment(env_obj, variables)
        totals["imported_total"] += counts["imported_total"]
        totals["overwritten"] += counts["overwritten"]
        totals["new"] += counts["new"]

        details.append(
            {
                "name": name,
                "environment_created": created,
                "imported_total": counts["imported_total"],
                "overwritten": counts["overwritten"],
                "new": counts["new"],
            }
        )

    return {
        "applied": True,
        "skipped": False,
        "skip_reason": None,
        "environments": details,
        "totals": totals,
    }
