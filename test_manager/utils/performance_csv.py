"""
CSV 参数化：解析、占位符替换、并发安全读取策略（兼容 gevent 协程）。

Locust 多协程下使用 gevent.lock.RLock 保护共享行指针；
「每用户一行」在 HttpUser.on_start 中分配固定行索引。
"""
from __future__ import annotations

import csv
import re
from typing import Any

import gevent.lock

from test_manager.utils.performance_config import (
    CSV_STRATEGY_PER_ITERATION,
    CSV_STRATEGY_PER_USER,
    PerformanceConfigError,
)

_PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")


def load_csv_rows(file_path: str, encoding: str = "utf-8-sig") -> list[dict[str, str]]:
    """
    读取 CSV 为 dict 行列表；首行为表头。跳过空行。
    编码默认 utf-8-sig 以兼容 Excel 导出的 BOM。
    """
    rows: list[dict[str, str]] = []
    try:
        with open(file_path, "r", encoding=encoding, newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise PerformanceConfigError("CSV 无表头")
            for raw in reader:
                if not raw:
                    continue
                line = {k.strip(): (v if v is not None else "").strip() for k, v in raw.items() if k}
                if not any(line.values()) and not any(line.keys()):
                    continue
                if not any(v for v in line.values()):
                    continue
                rows.append(line)
    except UnicodeDecodeError as e:
        raise PerformanceConfigError(
            f"CSV 编码解析失败，请使用 UTF-8（含 BOM 亦可）: {e}"
        ) from e
    except OSError as e:
        raise PerformanceConfigError(f"无法读取 CSV 文件: {e}") from e
    if not rows:
        raise PerformanceConfigError("CSV 无有效数据行")
    return rows


def replace_placeholders_str(s: str, row: dict[str, str]) -> str:
    def repl(m: re.Match) -> str:
        key = m.group(1)
        return str(row.get(key, ""))

    return _PLACEHOLDER_RE.sub(repl, s)


def replace_placeholders_obj(obj: Any, row: dict[str, str]) -> Any:
    """在 str / dict / list 嵌套结构中替换 {{col}} 占位符（含 JSON body）。"""
    if isinstance(obj, str):
        return replace_placeholders_str(obj, row)
    if isinstance(obj, dict):
        return {k: replace_placeholders_obj(v, row) for k, v in obj.items()}
    if isinstance(obj, list):
        return [replace_placeholders_obj(i, row) for i in obj]
    return obj


class CsvRowProvider:
    """
    高并发安全：per_iteration 使用 RLock + 递增索引；
    per_user 由外部在 User 实例上设置固定 index，调用 get_row_for_user。
    """

    def __init__(self, rows: list[dict[str, str]], strategy: str):
        self._rows = rows
        self._strategy = strategy
        self._lock = gevent.lock.RLock()
        self._iter_idx = 0
        self._user_seq = 0

    @property
    def row_count(self) -> int:
        return len(self._rows)

    def assign_user_index(self) -> int:
        """在 HttpUser.on_start 中调用，返回稳定行号（仅 per_user 模式使用）。"""
        with self._lock:
            idx = self._user_seq % len(self._rows)
            self._user_seq += 1
            return idx

    def get_row_for_iteration(self) -> dict[str, str]:
        """per_iteration：每请求轮询下一行。"""
        with self._lock:
            r = self._rows[self._iter_idx % len(self._rows)]
            self._iter_idx += 1
            return dict(r)

    def get_row_for_user_index(self, user_index: int) -> dict[str, str]:
        return dict(self._rows[user_index % len(self._rows)])
