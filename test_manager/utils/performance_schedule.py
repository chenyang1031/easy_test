"""
性能压测任务调度：支持 Celery 队列或本机独立进程。

默认使用独立进程（process），无需启动 Celery Worker，适合本地开发。
生产环境若已部署 Celery，可在 settings 或环境变量中设置 PERFORMANCE_TEST_EXECUTOR=celery。
"""
from __future__ import annotations

import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# inspect 超时（秒），避免 Broker 不可达时长时间阻塞
CELERY_INSPECT_TIMEOUT = 1.0


def check_celery_workers() -> tuple[bool, str | None]:
    """
    检测是否有 Celery Worker 响应 inspect.ping（需 Broker 可达）。

    返回 (是否有可用 Worker, 异常时的用户提示文案)。
    无 Worker 时第二个元素为简短说明，供前端或 API 展示。
    """
    try:
        from EasyTesting.celery import app
    except Exception as e:
        logger.warning("加载 Celery 应用失败: %s", e)
        return False, "无法加载 Celery 应用，请检查项目配置。"

    try:
        insp = app.control.inspect(timeout=CELERY_INSPECT_TIMEOUT)
        if insp is None:
            return (
                False,
                "无法连接 Celery Broker（通常为 Redis 未启动或地址错误）。请检查 Redis 与 CELERY_BROKER_URL。",
            )
        ping = insp.ping()
        if ping:
            return True, None
        return (
            False,
            "未检测到可用的 Celery Worker：任务已入队但可能不会被消费。请启动 Worker（如 celery -A EasyTesting worker），"
            "或将环境变量 PERFORMANCE_TEST_EXECUTOR 设为 process 使用本机子进程执行。",
        )
    except Exception as e:
        logger.warning("Celery inspect 失败: %s", e)
        return (
            False,
            f"检测 Worker 时出错：{e}。若使用 Celery 模式，请确认 Redis 已启动且 Worker 与 Web 使用同一 Broker。",
        )


def _run_locust_in_process(task_id: int) -> None:
    """子进程入口：完整 Django 初始化后执行与 Celery 任务相同的逻辑。"""
    import os

    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "EasyTesting.settings")
    django.setup()
    from test_manager.utils.performance_locust import safe_reset_django_connections

    safe_reset_django_connections()
    try:
        from test_manager.tasks import run_performance_test

        run_performance_test.apply(args=[task_id])
    finally:
        safe_reset_django_connections()


def schedule_performance_test(task_id: int) -> None:
    """
    异步启动压测：按 PERFORMANCE_TEST_EXECUTOR 选择 Celery 或本机子进程。
    """
    mode = getattr(settings, "PERFORMANCE_TEST_EXECUTOR", "process")
    mode = str(mode).strip().lower() or "process"

    if mode == "celery":
        from test_manager.models import PerformanceTestTask
        from test_manager.tasks import run_performance_test

        async_result = run_performance_test.delay(task_id)
        PerformanceTestTask.objects.filter(id=task_id).update(celery_task_id=async_result.id)
        logger.info("性能压测已投递 Celery: task_id=%s async_id=%s", task_id, async_result.id)
        return

    if mode == "process":
        from multiprocessing import Process

        p = Process(target=_run_locust_in_process, args=(task_id,), daemon=True)
        p.start()
        logger.info("性能压测已启动独立进程: task_id=%s pid=%s", task_id, p.pid)
        return

    raise ValueError(
        f"未知 PERFORMANCE_TEST_EXECUTOR={mode!r}，支持: celery, process"
    )
