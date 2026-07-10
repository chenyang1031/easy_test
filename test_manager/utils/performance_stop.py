"""
性能压测任务手动停止（单机 Locust / Celery）

- process 模式：通过启动时记录的子进程 PID 终止 Locust 子进程。
- celery 模式：revoke 并 terminate 异步任务。
- 无 PID / 无 Celery id：视为执行器已丢失，仅将 DB 置为已停止（兼容「僵尸执行中」）。
- 目标进程已退出：视为停止成功，更新 DB。
"""
from __future__ import annotations

import errno
import logging
import os
import signal
import subprocess
import sys
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

logger = logging.getLogger(__name__)


def _stderr_means_process_already_gone(text: str) -> bool:
    """
    taskkill / 系统返回：目标进程已不存在时视为停止成功（幂等）。
    英文 not found；简体中文常见「没有找到进程」或「找不到进程」，二者措辞不同需都识别。
    """
    if not text:
        return False
    t = text.strip()
    low = t.lower()
    if "not found" in low or "not running" in low:
        return True
    # 中文 Windows taskkill：错误: 没有找到进程 "12345"。
    if "没有找到进程" in t or "找不到进程" in t or "找不到" in t:
        return True
    if "进程" in t and ("不存在" in t or "无法终止" in t):
        return True
    return False


def _oserror_means_process_already_gone(exc: OSError) -> bool:
    """Unix 上常见 ESRCH；Windows 上 os.kill 对已退出进程可能抛 OSError。"""
    if exc.errno == errno.ESRCH:
        return True
    # Windows: 部分版本/场景下 WinError 与「进程已结束」相关
    winerr = getattr(exc, "winerror", None)
    if winerr is not None and sys.platform == "win32":
        # 87 INVALID_PARAMETER 等有时在 PID 无效时出现；与「已退出」难以区分，交给 taskkill 二次判断
        if winerr == 87:
            return False
    return False


def _terminate_pid(pid: int) -> tuple[bool, str | None]:
    """
    终止本地 OS 进程。已退出返回 (True, None)；不可恢复错误返回 (False, message)。
    """
    if pid <= 0:
        return True, None
    try:
        os.kill(pid, signal.SIGTERM)
        return True, None
    except ProcessLookupError:
        return True, None
    except OSError as e:
        if _oserror_means_process_already_gone(e):
            return True, None
        if sys.platform == "win32":
            try:
                r = subprocess.run(
                    ["taskkill", "/PID", str(pid), "/F", "/T"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                if r.returncode == 0:
                    return True, None
                err = (r.stderr or r.stdout or "").strip() or f"taskkill exit {r.returncode}"
                if _stderr_means_process_already_gone(err):
                    return True, None
                return False, err
            except Exception as ex:
                logger.warning("taskkill 失败 pid=%s: %s", pid, ex)
                return False, str(ex)
        return False, str(e)


def _revoke_celery_task(async_result_id: str | None) -> tuple[bool, str | None]:
    if not async_result_id:
        return True, None
    try:
        from EasyTesting.celery import app

        app.control.revoke(async_result_id, terminate=True)
        return True, None
    except Exception as e:
        logger.warning("Celery revoke 失败 task_id=%s: %s", async_result_id, e)
        return False, str(e)


def stop_performance_task(
    *,
    task,
    user: AbstractUser | None,
    reason: str = "",
) -> dict:
    """
    停止执行中的性能测试任务。

    Returns:
        {"ok": True, "message": str, "already_stopped": bool}
    Raises:
        ValidationError: 当前状态不可停止，或终止执行器失败
    """
    from rest_framework.exceptions import ValidationError

    from test_manager.models import PerformanceTestTask

    reason = (reason or "").strip() or "用户手动停止"

    with transaction.atomic():
        t = (
            PerformanceTestTask.objects.select_for_update()
            .select_related("project", "stopped_by")
            .get(pk=task.pk)
        )

        if t.status == PerformanceTestTask.STATUS_STOPPED:
            return {
                "ok": True,
                "message": "任务已处于已停止状态",
                "already_stopped": True,
                "task": t,
            }

        if t.status != PerformanceTestTask.STATUS_RUNNING:
            raise ValidationError(
                {"detail": "仅执行中的任务可以停止；当前状态不可停止"}
            )

        pid = t.runner_pid
        celery_id = (t.celery_task_id or "").strip() or None

        if celery_id:
            ok_c, err_c = _revoke_celery_task(celery_id)
            if not ok_c:
                raise ValidationError({"detail": f"停止失败：{err_c}"})
        elif pid:
            ok_p, err_p = _terminate_pid(int(pid))
            if not ok_p:
                raise ValidationError({"detail": f"停止失败：{err_p}"})
        else:
            logger.info(
                "性能任务 %s 无 runner_pid/celery_task_id，仅将状态更新为已停止",
                t.id,
            )

        now = timezone.now()
        t.status = PerformanceTestTask.STATUS_STOPPED
        t.stopped_at = now
        t.stopped_by = user if user and getattr(user, "pk", None) else None
        t.stop_reason = reason[:500]
        t.runner_pid = None
        t.celery_task_id = None
        t.finished_at = now
        t.save(
            update_fields=[
                "status",
                "stopped_at",
                "stopped_by",
                "stop_reason",
                "runner_pid",
                "celery_task_id",
                "finished_at",
            ]
        )

        return {
            "ok": True,
            "message": "性能测试任务已停止",
            "already_stopped": False,
            "task": t,
        }
