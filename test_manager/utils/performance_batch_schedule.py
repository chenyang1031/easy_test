"""
性能测试批量执行任务调度器

负责管理批量任务的执行流程，支持串行和并行两种模式。
串行：按 order_index 顺序逐个等待任务完成，再启动下一个。
并行：同时启动所有任务（受 max_concurrent 限制），轮询等待全部完成。
"""
from __future__ import annotations

import logging
import time
import threading
from django.db import close_old_connections
from django.utils import timezone

from test_manager.models import (
    PerformanceBatchTask,
    PerformanceBatchItem,
    PerformanceTestTask,
)

logger = logging.getLogger(__name__)

# 轮询间隔（秒）
POLL_INTERVAL = 5
# 每个任务最长等待时间（秒），防止无限等待
MAX_WAIT_PER_TASK = 3600


def start_performance_batch(batch_id: int) -> None:
    """
    启动批量性能测试（在 transaction.on_commit 回调中调用，运行于主进程线程）。
    在后台线程中执行，不阻塞主 Web 请求。
    """
    t = threading.Thread(target=_run_batch, args=(batch_id,), daemon=True)
    t.start()


def _run_batch(batch_id: int) -> None:
    """实际执行批量任务的函数，在后台线程中运行。"""
    close_old_connections()
    try:
        batch = PerformanceBatchTask.objects.select_related("project").get(pk=batch_id)
    except PerformanceBatchTask.DoesNotExist:
        logger.error("批量任务不存在: batch_id=%s", batch_id)
        return

    # 标记为运行中
    batch.status = PerformanceBatchTask.STATUS_RUNNING
    batch.started_at = timezone.now()
    batch.save(update_fields=["status", "started_at"])

    items = list(
        PerformanceBatchItem.objects.filter(batch=batch)
        .select_related("performance_task")
        .order_by("order_index")
    )

    if not items:
        batch.status = PerformanceBatchTask.STATUS_COMPLETED
        batch.finished_at = timezone.now()
        batch.save(update_fields=["status", "finished_at"])
        return

    try:
        if batch.execute_mode == PerformanceBatchTask.EXECUTE_MODE_PARALLEL:
            _run_parallel(batch, items)
        else:
            _run_serial(batch, items)
    except Exception as exc:
        logger.exception("批量任务执行异常: batch_id=%s err=%s", batch_id, exc)
        close_old_connections()
        batch.refresh_from_db()
        if batch.status == PerformanceBatchTask.STATUS_RUNNING:
            batch.status = PerformanceBatchTask.STATUS_FAILED
            batch.finished_at = timezone.now()
            batch.save(update_fields=["status", "finished_at"])


# ---------------------------------------------------------------------------
# 串行执行
# ---------------------------------------------------------------------------

def _run_serial(batch: PerformanceBatchTask, items: list) -> None:
    """逐个等待任务完成，再执行下一个。"""
    success_count = 0
    failed_count = 0

    for item in items:
        # 重新获取最新 batch 状态，如果被外部停止则中断
        close_old_connections()
        batch.refresh_from_db()
        if batch.status not in (
            PerformanceBatchTask.STATUS_RUNNING,
            PerformanceBatchTask.STATUS_PARTIAL_SUCCESS,
        ):
            logger.info("批量任务已被停止，中断串行执行: batch_id=%s", batch.pk)
            break

        perf_task = item.performance_task
        _reset_task_if_needed(perf_task)

        # 标记 item 为运行中
        item.status = PerformanceBatchItem.STATUS_RUNNING
        item.started_at = timezone.now()
        item.save(update_fields=["status", "started_at"])

        # 异步启动单个任务
        try:
            from test_manager.utils.performance_schedule import schedule_performance_test
            schedule_performance_test(perf_task.id)
        except Exception as exc:
            item.status = PerformanceBatchItem.STATUS_FAILED
            item.error_message = f"启动失败: {exc}"
            item.finished_at = timezone.now()
            item.save(update_fields=["status", "error_message", "finished_at"])
            failed_count += 1
            _sync_batch_stats(batch, success_count, failed_count, 0)
            continue

        # 轮询等待该任务完成
        _wait_for_task(perf_task)
        close_old_connections()
        perf_task.refresh_from_db()

        if perf_task.status == PerformanceTestTask.STATUS_COMPLETED:
            item.status = PerformanceBatchItem.STATUS_SUCCESS
            item.result_summary = _extract_result_summary(perf_task)
            success_count += 1
        else:
            item.status = PerformanceBatchItem.STATUS_FAILED
            item.error_message = f"任务结束状态: {perf_task.status}"
            failed_count += 1

        item.finished_at = timezone.now()
        item.save(update_fields=["status", "result_summary", "error_message", "finished_at"])
        _sync_batch_stats(batch, success_count, failed_count, 0)

    _finalize_batch(batch, success_count, failed_count)


# ---------------------------------------------------------------------------
# 并行执行
# ---------------------------------------------------------------------------

def _run_parallel(batch: PerformanceBatchTask, items: list) -> None:
    """受 max_concurrent 控制，并发启动所有任务，然后等待全部完成。"""
    max_concurrent = max(1, batch.max_concurrent or 5)
    semaphore = threading.Semaphore(max_concurrent)
    lock = threading.Lock()
    counters = {"success": 0, "failed": 0}

    def _start_one(item) -> None:
        with semaphore:
            close_old_connections()
            perf_task = item.performance_task
            _reset_task_if_needed(perf_task)

            item.status = PerformanceBatchItem.STATUS_RUNNING
            item.started_at = timezone.now()
            item.save(update_fields=["status", "started_at"])

            try:
                from test_manager.utils.performance_schedule import schedule_performance_test
                schedule_performance_test(perf_task.id)
            except Exception as exc:
                item.status = PerformanceBatchItem.STATUS_FAILED
                item.error_message = f"启动失败: {exc}"
                item.finished_at = timezone.now()
                item.save(update_fields=["status", "error_message", "finished_at"])
                with lock:
                    counters["failed"] += 1
                _sync_batch_stats(batch, counters["success"], counters["failed"], 0)
                return

            _wait_for_task(perf_task)
            close_old_connections()
            perf_task.refresh_from_db()

            if perf_task.status == PerformanceTestTask.STATUS_COMPLETED:
                item.status = PerformanceBatchItem.STATUS_SUCCESS
                item.result_summary = _extract_result_summary(perf_task)
                with lock:
                    counters["success"] += 1
            else:
                item.status = PerformanceBatchItem.STATUS_FAILED
                item.error_message = f"任务结束状态: {perf_task.status}"
                with lock:
                    counters["failed"] += 1

            item.finished_at = timezone.now()
            item.save(update_fields=["status", "result_summary", "error_message", "finished_at"])
            _sync_batch_stats(batch, counters["success"], counters["failed"], 0)

    threads = [threading.Thread(target=_start_one, args=(it,), daemon=True) for it in items]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    _finalize_batch(batch, counters["success"], counters["failed"])


# ---------------------------------------------------------------------------
# 辅助工具
# ---------------------------------------------------------------------------

def _reset_task_if_needed(perf_task: PerformanceTestTask) -> None:
    """如果任务之前跑过，清空旧结果并重置为草稿状态。"""
    if perf_task.status in (
        PerformanceTestTask.STATUS_COMPLETED,
        PerformanceTestTask.STATUS_FAILED,
        PerformanceTestTask.STATUS_STOPPED,
    ):
        from test_manager.models import PerformanceTestResult
        PerformanceTestResult.objects.filter(task=perf_task).delete()
        perf_task.status = PerformanceTestTask.STATUS_DRAFT
        perf_task.executed_at = None
        perf_task.finished_at = None
        perf_task.runner_pid = None
        perf_task.celery_task_id = None
        perf_task.save(update_fields=[
            "status", "executed_at", "finished_at", "runner_pid", "celery_task_id"
        ])


def _wait_for_task(perf_task: PerformanceTestTask) -> bool:
    """
    轮询等待单个 PerformanceTestTask 到达终态。
    返回 True 表示在超时前到达终态。
    """
    terminal = {
        PerformanceTestTask.STATUS_COMPLETED,
        PerformanceTestTask.STATUS_FAILED,
        PerformanceTestTask.STATUS_STOPPED,
    }
    deadline = time.monotonic() + MAX_WAIT_PER_TASK
    # 先等一小段时间，让调度器把任务状态从 draft 改为 running
    time.sleep(3)

    while time.monotonic() < deadline:
        close_old_connections()
        perf_task.refresh_from_db()
        if perf_task.status in terminal:
            return True
        time.sleep(POLL_INTERVAL)

    logger.warning("等待任务超时: task_id=%s", perf_task.id)
    return False


def _extract_result_summary(perf_task: PerformanceTestTask) -> dict:
    """从任务结果数据中提取摘要指标（供 result_summary 字段存储）。"""
    try:
        from test_manager.utils.performance_report import build_performance_report_dict
        report = build_performance_report_dict(perf_task)
        if report:
            return {
                "max_rps": report.get("max_qps", 0),
                "avg_response_time_50_ms": report.get("avg_response_time_50_ms", 0),
                "avg_response_time_90_ms": report.get("avg_response_time_90_ms", 0),
                "avg_p95_ms": report.get("avg_p95_ms", 0),
                "avg_p99_ms": report.get("avg_p99_ms", 0),
                "avg_failure_rate_percent": report.get("avg_failure_rate_percent", 0),
                "max_active_users": report.get("max_active_users", 0),
            }
    except Exception as exc:
        logger.warning("提取任务摘要失败: task_id=%s err=%s", perf_task.id, exc)
    return {}


def _sync_batch_stats(
    batch: PerformanceBatchTask,
    success: int,
    failed: int,
    running: int,
) -> None:
    """将当前统计写回 batch 记录。"""
    close_old_connections()
    PerformanceBatchTask.objects.filter(pk=batch.pk).update(
        completed_tasks=success + failed,
        successful_tasks=success,
        failed_tasks=failed,
        running_tasks=running,
    )


def _finalize_batch(
    batch: PerformanceBatchTask,
    success_count: int,
    failed_count: int,
) -> None:
    """确定最终状态并写回。"""
    close_old_connections()
    batch.refresh_from_db()

    # 如果已被外部停止，不再覆盖
    if batch.status not in (
        PerformanceBatchTask.STATUS_RUNNING,
        PerformanceBatchTask.STATUS_PARTIAL_SUCCESS,
    ):
        return

    total = success_count + failed_count
    if failed_count == 0 and total > 0:
        final_status = PerformanceBatchTask.STATUS_COMPLETED
    elif success_count > 0 and failed_count > 0:
        final_status = PerformanceBatchTask.STATUS_PARTIAL_SUCCESS
    else:
        final_status = PerformanceBatchTask.STATUS_FAILED

    batch.status = final_status
    batch.completed_tasks = total
    batch.successful_tasks = success_count
    batch.failed_tasks = failed_count
    batch.running_tasks = 0
    batch.finished_at = timezone.now()
    batch.save(update_fields=[
        "status", "completed_tasks", "successful_tasks",
        "failed_tasks", "running_tasks", "finished_at",
    ])
    logger.info(
        "批量任务完成: batch_id=%s status=%s success=%s failed=%s",
        batch.pk, final_status, success_count, failed_count,
    )
