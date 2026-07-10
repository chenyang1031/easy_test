"""
业务断言：基于 jsonpath-ng，在 Locust 协程内执行（无 ORM）。

断言失败仅影响失败计数与 error_classification，不计入响应时间统计（在收到响应后执行）。
"""
from __future__ import annotations

from typing import Any

from jsonpath_ng import parse


def _first_match_value(response_json: Any, jsonpath_expr: str):
    expr = parse(jsonpath_expr)
    matches = expr.find(response_json)
    if not matches:
        return None
    return matches[0].value


def evaluate_assertion_rule(response_json: Any, rule: dict[str, Any]) -> tuple[bool, str | None]:
    """
    单条断言；成功返回 (True, None)，失败返回 (False, reason)。
    """
    op = rule["op"]
    path = rule["jsonpath"]
    actual = _first_match_value(response_json, path)
    if op == "not_null":
        ok = actual is not None
        return (ok, None if ok else f"path {path!r} 值为 null 或不存在")
    expect = rule.get("expect")
    if actual is None:
        return False, f"path {path!r} 无匹配"
    if op == "eq":
        ok = actual == expect
        return (ok, None if ok else f"期望 {expect!r} 实际 {actual!r}")
    if op == "ne":
        ok = actual != expect
        return (ok, None if ok else f"期望不等于 {expect!r} 但实际为 {actual!r}")
    if op in ("gt", "ge", "lt", "le"):
        try:
            a = float(actual)
            e = float(expect)
        except (TypeError, ValueError):
            return False, f"无法将值转为数值比较: actual={actual!r} expect={expect!r}"
        if op == "gt":
            ok = a > e
        elif op == "ge":
            ok = a >= e
        elif op == "lt":
            ok = a < e
        else:
            ok = a <= e
        return (ok, None if ok else f"比较 {op} 失败: {a} vs {e}")
    if op == "contains":
        s_actual = str(actual)
        s_expect = str(expect)
        ok = s_expect in s_actual
        return (ok, None if ok else f"字符串不包含 {expect!r}")
    return False, f"未知操作符 {op!r}"


def run_assertions(response_json: Any, assertions: list[dict[str, Any]]) -> tuple[bool, str | None]:
    """
    执行全部断言；全部通过返回 (True, None)，否则返回 (False, 首条失败原因)。
    """
    for rule in assertions:
        ok, err = evaluate_assertion_rule(response_json, rule)
        if not ok:
            return False, err
    return True, None
