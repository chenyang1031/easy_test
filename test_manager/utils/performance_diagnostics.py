"""
性能压测任务「卡在执行中 / 控制台无数据」排查辅助。

基于任务状态、executed_at、采样结果时间分布与 settings 中的执行器模式做启发式判断，
不访问 Locust 进程内部，便于运维与前端展示。
"""
from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db.models import Count, Max, Min
from django.utils import timezone

from test_manager.models import PerformanceTestResult, PerformanceTestTask

# 首条采样约在 Locust 启动后 1s 写出，略留余量
WARMUP_NO_RESULTS_SEC = 45
# 超过计划时长仍未结束，怀疑僵尸「执行中」
ZOMBIE_AFTER_RUN_EXTRA_SEC = 90
# 有条目但长时间无新采样
STALE_SAMPLE_GAP_SEC = 120


def build_performance_diagnostics(task: PerformanceTestTask) -> dict[str, Any]:
    now = timezone.now()
    mode = str(getattr(settings, "PERFORMANCE_TEST_EXECUTOR", "process")).strip().lower() or "process"

    agg = PerformanceTestResult.objects.filter(task=task).aggregate(
        c=Count("id"),
        first_ts=Min("timestamp"),
        last_ts=Max("timestamp"),
    )
    results_count = int(agg["c"] or 0)
    first_ts = agg["first_ts"]
    last_ts = agg["last_ts"]

    executed_at = task.executed_at
    sec_since_start: float | None = None
    if executed_at:
        sec_since_start = max(0.0, (now - executed_at).total_seconds())

    sec_since_last_result: float | None = None
    if last_ts:
        sec_since_last_result = max(0.0, (now - last_ts).total_seconds())

    run_sec = int(task.run_time or 0)
    overdue_sec: float | None = None
    if (
        task.status == PerformanceTestTask.STATUS_RUNNING
        and sec_since_start is not None
        and run_sec > 0
    ):
        overdue_sec = sec_since_start - run_sec

    risk_level, hints = _assess_risk(
        task=task,
        results_count=results_count,
        sec_since_start=sec_since_start,
        sec_since_last_result=sec_since_last_result,
        run_sec=run_sec,
        executor_mode=mode,
    )

    celery_worker_ok: bool | None = None
    if mode == "celery":
        try:
            from test_manager.utils.performance_schedule import check_celery_workers

            ok, _hint = check_celery_workers()
            celery_worker_ok = ok
        except Exception:
            celery_worker_ok = False

    hint_list = list(hints)
    if mode == "celery" and celery_worker_ok is False:
        hint_list.insert(
            0,
            "当前 Celery inspect 未探测到 Worker：若压测通过队列投递，可能从未执行；请启动 Worker 或将 PERFORMANCE_TEST_EXECUTOR 设为 process。",
        )

    return {
        "task_id": task.id,
        "status": task.status,
        "executor_mode": mode,
        "run_time_sec": run_sec,
        "executed_at": executed_at.isoformat() if executed_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
        "server_now": now.isoformat(),
        "results_count": results_count,
        "first_result_at": first_ts.isoformat() if first_ts else None,
        "last_result_at": last_ts.isoformat() if last_ts else None,
        "seconds_since_executed": round(sec_since_start, 1) if sec_since_start is not None else None,
        "seconds_since_last_result": round(sec_since_last_result, 1)
        if sec_since_last_result is not None
        else None,
        "expected_finish_after_start_sec": run_sec,
        "seconds_over_expected_finish": round(overdue_sec, 1) if overdue_sec is not None else None,
        "risk_level": risk_level,
        "hints": hint_list,
        "celery_worker_ok": celery_worker_ok,
    }


def _assess_risk(
    *,
    task: PerformanceTestTask,
    results_count: int,
    sec_since_start: float | None,
    sec_since_last_result: float | None,
    run_sec: int,
    executor_mode: str,
) -> tuple[str, list[str]]:
    hints: list[str] = []
    st = task.status

    if st != PerformanceTestTask.STATUS_RUNNING:
        return "idle", [
            "当前任务不在执行中；若曾卡在执行中，请结合下方历史时间与服务器日志分析。"
        ]

    # 执行中但从未写入 executed_at（异常数据）
    if sec_since_start is None:
        return "unknown", [
            "状态为「执行中」但缺少 executed_at，数据可能不一致，请检查数据库或是否被手工改状态。",
            "可查看 Django / Celery / 自定义日志中该 task_id 的报错。",
        ]

    # 僵尸：超过计划时长仍未结束
    if run_sec > 0 and sec_since_start > run_sec + ZOMBIE_AFTER_RUN_EXTRA_SEC:
        hints.append(
            f"已运行约 {int(sec_since_start)} 秒，超过计划时长 {run_sec} 秒逾 {ZOMBIE_AFTER_RUN_EXTRA_SEC} 秒，"
            "任务状态可能未正确更新（进程崩溃、Locust 未正常退出等）。"
        )
        hints.append(
            "建议：在服务器上搜索日志关键字「性能测试任务」或 task_id=%s，确认 run_locust_test 是否异常退出。"
            % task.id
        )
        return "zombie_running", hints

    # 一直没有任何采样
    if results_count == 0:
        if sec_since_start <= WARMUP_NO_RESULTS_SEC:
            return "warming_up", [
                f"启动后 {int(sec_since_start)} 秒内尚无采样属常见情况：首条结果约在启动后 1～2 秒写入。",
                "若超过约 %d 秒仍无数据，请查看下方「可能原因」。" % WARMUP_NO_RESULTS_SEC,
            ]
        hints.extend(
            [
                "已执行超过 %d 秒仍无任何 PerformanceTestResult 记录，说明 Locust 侧可能未写入数据库或进程未真正跑起来。"
                % WARMUP_NO_RESULTS_SEC,
                "请逐项确认：",
            ]
        )
        if executor_mode == "celery":
            hints.append(
                "• 当前为 Celery 模式：Worker 是否已启动且与 Web 共用同一 Redis？启动压测时是否曾提示 Worker 不可用？"
            )
        else:
            hints.append(
                "• 当前为 process 模式：压测在独立子进程中运行，若子进程启动即崩溃，可能无采样；请查看 Django 进程标准输出与日志。"
            )
        hints.append(
            "• 环境 base_url / 接口 URL 是否可达？若目标不可达，可能长时间卡在连接阶段（仍应有少量请求统计，视 Locust 版本而定）。"
        )
        hints.append(
            "• 查看日志模块 test_manager.utils.performance_locust 是否有「采集指标写入失败」或异常栈。"
        )
        return "no_samples", hints

    # 有历史采样，但长时间无新数据（且未触发上方的僵尸判定）
    if sec_since_last_result is not None and sec_since_last_result > STALE_SAMPLE_GAP_SEC:
        hints.append(
            "最近一次采样已超过约 %d 秒，可能 Locust 已卡住、目标不可达或进程被挂起。"
            % int(sec_since_last_result)
        )
        hints.append("建议检查目标接口健康、超时配置（extra_config.timeout）及服务器 CPU/内存。")
        return "sampling_stalled", hints

    # 正常有数据且在预期时间内
    if results_count > 0 and sec_since_last_result is not None and sec_since_last_result <= 30:
        return "healthy", ["采样正常更新中。"]

    return "ok", [
        "任务执行中且已有采样数据；若曲线不刷新，可尝试点击「刷新」或检查浏览器网络请求是否被拦截。"
    ]
