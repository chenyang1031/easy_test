"""
性能测试报告聚合（get_report），与视图解耦，便于单测。

兼容：旧结果无新字段时由迁移保证默认 0 / {}；若 ORM 未加载新列则 getattr 兜底。
"""
from __future__ import annotations

from typing import Any

from django.db.models import Avg, Max

from test_manager.models import PerformanceTestResult


def build_performance_report_dict(task) -> dict[str, Any] | None:
    """
    聚合指定任务的结果，返回 report 字典；无数据返回 None。
    """
    results = PerformanceTestResult.objects.filter(task=task)
    if not results.exists():
        return None

    agg = results.aggregate(
        max_qps=Max("requests_per_second"),
        avg_rt_50=Avg("response_time_50"),
        avg_rt_90=Avg("response_time_90"),
        max_active_users=Max("active_users"),
        avg_failure_rate=Avg("failure_rate"),
        avg_p95=Avg("p95"),
        avg_p99=Avg("p99"),
        max_p95=Max("p95"),
        max_p99=Max("p99"),
        max_rt=Max("max_response_time"),
    )

    last = results.order_by("-timestamp").first()
    err_cls = {}
    if last is not None:
        err_cls = getattr(last, "error_classification", None) or {}

    def _num(key: str, default: float = 0.0) -> float:
        v = agg.get(key)
        if v is None:
            return default
        return float(v)

    report: dict[str, Any] = {
        "max_qps": round(_num("max_qps"), 2),
        "avg_response_time_50_ms": round(_num("avg_rt_50"), 2),
        "avg_response_time_90_ms": round(_num("avg_rt_90"), 2),
        "max_active_users": int(agg.get("max_active_users") or 0),
        "avg_failure_rate_percent": round(_num("avg_failure_rate"), 2),
        # 阶段2 扩展指标（旧数据为 0）
        "avg_p95_ms": round(_num("avg_p95"), 2),
        "avg_p99_ms": round(_num("avg_p99"), 2),
        "max_p95_ms": round(_num("max_p95"), 2),
        "max_p99_ms": round(_num("max_p99"), 2),
        "max_response_time_ms": round(_num("max_rt"), 2),
        "error_classification": err_cls if err_cls else {},
    }
    return report


def serialize_report_response(task, report: dict[str, Any] | None) -> dict[str, Any]:
    """统一 API 外层结构。"""
    base = {
        "task_id": task.id,
        "task_name": task.name,
        "status": task.status,
        "executed_at": task.executed_at,
        "finished_at": task.finished_at,
        "report": report,
    }
    if report is None:
        base["message"] = "暂无压测结果数据"
    return base
