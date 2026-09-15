"""
场景批量执行调度器

批量执行 N 个场景只产生一条 SceneBatchExecution 批次记录，
每个场景的实际执行通过 execute_scene(batch=...) 挂到批次下，
计数与聚合状态逐个回写，供前端轮询展示进度。
"""
from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor

import requests

from django.db import close_old_connections
from django.utils import timezone

from test_manager.env_variables_compat import variables_for_runtime
from test_manager.models import SceneBatchExecution, TestScene, TestSceneExecution
from test_manager.api.scene_engine import _render_text_with_variables, execute_scene

logger = logging.getLogger(__name__)

# 并发模式下的最大并发场景数
MAX_PARALLEL_SCENES = 5

# 批次终态集合（用于中断判断）
_TERMINAL_BATCH_STATUS = {
    SceneBatchExecution.STATUS_SUCCESS,
    SceneBatchExecution.STATUS_FAILED,
    SceneBatchExecution.STATUS_PARTIAL_SUCCESS,
    SceneBatchExecution.STATUS_STOPPED,
}


def start_scene_batch(batch_id: int, scene_ids: list) -> None:
    """在后台线程中执行批次，不阻塞 Web 请求。"""
    t = threading.Thread(target=_run_batch, args=(batch_id, list(scene_ids)), daemon=True)
    t.start()


def _probe_environment_token(env):
    """
    批量执行前的 Token 探活：环境配置了 probe_url 时发一次轻量 GET。
    返回 401/403 判定 Token 失效，返回给用户的失败说明；其他异常只记日志，不阻断批次。
    """
    probe_url = (getattr(env, "probe_url", "") or "").strip() if env else ""
    if not probe_url:
        return None
    if not probe_url.lower().startswith(("http://", "https://")):
        base = (env.base_url or "").rstrip("/")
        probe_url = f"{base}/{probe_url.lstrip('/')}"
    if not probe_url.lower().startswith(("http://", "https://")):
        logger.warning("批次探活 URL 无法拼接 base_url，跳过探活: %s", probe_url)
        return None

    # 请求头取环境预设（含 token），值中的 {{var}} 按环境变量渲染
    env_variables = variables_for_runtime(env.variables or {})
    headers = {}
    for item in env.request_headers or []:
        try:
            key = str(item.get("key") or "").strip()
            raw_val = item.get("value")
            if isinstance(raw_val, dict):
                raw_val = raw_val.get("value")
            if key and raw_val not in (None, ""):
                headers[key] = str(_render_text_with_variables(raw_val, dict(env_variables)))
        except Exception:
            continue

    try:
        resp = requests.get(probe_url, headers=headers, timeout=10, allow_redirects=False)
    except Exception as exc:
        logger.warning("批次探活请求失败（不阻断批次）: %s err=%s", probe_url, exc)
        return None
    if resp.status_code in (401, 403):
        return (
            f"环境 Token 探活未通过：GET {probe_url} 返回 {resp.status_code}，已跳过整批执行；"
            f"请刷新环境 Token 后重新发起批量执行"
        )
    logger.info("批次探活通过: %s -> %s", probe_url, resp.status_code)
    return None


def _run_batch(batch_id: int, scene_ids: list) -> None:
    close_old_connections()
    try:
        batch = SceneBatchExecution.objects.select_related("environment", "created_by").get(pk=batch_id)
    except SceneBatchExecution.DoesNotExist:
        logger.error("场景批量执行批次不存在: batch_id=%s", batch_id)
        return

    counters = {"success": 0, "failed": 0, "partial": 0}
    lock = threading.Lock()
    env = batch.environment

    # Token 探活：避免 Token 过期时整批场景逐个失败（失败诊断实战中的头号原因）
    skip_reason = _probe_environment_token(env)
    if skip_reason:
        logger.warning("批次 %s 未开始即结束（Token 探活未通过）: %s", batch_id, skip_reason)
        batch.status = SceneBatchExecution.STATUS_FAILED
        batch.error_message = skip_reason
        batch.finished_at = timezone.now()
        batch.save(update_fields=["status", "error_message", "finished_at", "updated_at"])
        return

    def _run_one(scene_id: int) -> None:
        close_old_connections()
        with lock:
            # 每个场景启动前检查批次是否被停止
            batch.refresh_from_db(fields=["status", "cancel_requested"])
            if batch.cancel_requested or batch.status in _TERMINAL_BATCH_STATUS:
                return

        try:
            scene = TestScene.objects.get(pk=scene_id, is_deleted=False)
        except TestScene.DoesNotExist:
            _record_child_result(batch, counters, lock, None, "场景不存在或已删除")
            return

        # 与单次执行入口保持一致：以场景自身配置为底，环境参数覆盖
        scene_runtime = dict(scene.runtime_config or {})
        if env:
            scene_runtime["environment_id"] = env.id
            scene_runtime["base_url"] = env.base_url or ""

        try:
            execution = execute_scene(
                scene=scene,
                operator=batch.created_by,
                run_mode=TestSceneExecution.RUN_MODE_ALL,
                runtime_config_override=scene_runtime,
                batch=batch,
            )
            _record_child_result(batch, counters, lock, execution, None)
        except Exception as exc:
            logger.exception("批量执行场景异常: batch_id=%s scene_id=%s err=%s", batch_id, scene_id, exc)
            _record_child_result(batch, counters, lock, None, str(exc))

    try:
        if batch.execute_mode == SceneBatchExecution.EXECUTE_MODE_PARALLEL:
            with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL_SCENES, max(1, len(scene_ids)))) as pool:
                list(pool.map(_run_one, scene_ids))
        else:
            for sid in scene_ids:
                _run_one(sid)
    except Exception as exc:
        logger.exception("场景批量执行线程异常: batch_id=%s err=%s", batch_id, exc)

    _finalize_batch(batch, counters["success"], counters["failed"], counters["partial"])


def _record_child_result(batch, counters, lock, execution, error_message):
    """单个场景执行结束，回写批次计数。execution 为 None 表示未产生执行记录（启动失败）。"""
    status = execution.status if execution is not None else TestSceneExecution.STATUS_FAILED
    if error_message and execution is None:
        # 未产生执行记录的启动失败，附加到批次错误信息便于排查
        batch.error_message = (batch.error_message + "\n" if batch.error_message else "") + error_message
    with lock:
        if status == TestSceneExecution.STATUS_SUCCESS:
            counters["success"] += 1
        elif status == TestSceneExecution.STATUS_PARTIAL_SUCCESS:
            counters["partial"] += 1
        else:
            counters["failed"] += 1
        _sync_batch_stats(batch.pk, counters, batch.error_message)


def _sync_batch_stats(batch_id: int, counters: dict, error_message=None) -> None:
    close_old_connections()
    fields = {
        "completed_scenes": counters["success"] + counters["failed"] + counters["partial"],
        "success_scenes": counters["success"],
        "failed_scenes": counters["failed"],
        "partial_scenes": counters["partial"],
    }
    if error_message is not None:
        fields["error_message"] = error_message
    SceneBatchExecution.objects.filter(pk=batch_id).update(**fields)


def _finalize_batch(batch, success: int, failed: int, partial: int) -> None:
    """确定批次最终聚合状态并写回。"""
    close_old_connections()
    batch.refresh_from_db()
    if batch.status in _TERMINAL_BATCH_STATUS:
        return

    if batch.cancel_requested:
        final_status = SceneBatchExecution.STATUS_STOPPED
    elif failed == 0 and partial == 0 and success > 0:
        final_status = SceneBatchExecution.STATUS_SUCCESS
    elif success > 0 or partial > 0:
        final_status = SceneBatchExecution.STATUS_PARTIAL_SUCCESS
    else:
        final_status = SceneBatchExecution.STATUS_FAILED

    batch.status = final_status
    batch.completed_scenes = success + failed + partial
    batch.success_scenes = success
    batch.failed_scenes = failed
    batch.partial_scenes = partial
    batch.finished_at = timezone.now()
    batch.save(update_fields=[
        "status", "completed_scenes", "success_scenes",
        "failed_scenes", "partial_scenes", "finished_at", "updated_at",
    ])
    logger.info(
        "场景批量执行完成: batch_id=%s status=%s success=%s partial=%s failed=%s",
        batch.pk, final_status, success, partial, failed,
    )
