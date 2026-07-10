"""
性能测试 Locust 执行模块（阶段2 单机增强）

- 基于 DynamicApiUser + gevent。Django 的 default 连接在 thread_critical 下按 OS 线程隔离，
  但同一进程内 gevent 各 greenlet 的 _thread.get_ident() 与创建连接时不一致，易触发
  DatabaseWrapper 校验错误；inc_thread_sharing 在 Locust/Celery 组合下仍不可靠。
- 指标落库：采集 greenlet 只 append 快照到 list；Locust 结束后再在主线程同步路径 bulk_create。
  （压测阶段禁止 ORM：gevent patch 后 get_ident 在 greenlet/OS 线程间与 Django DatabaseWrapper
  不一致，任意异步路径写库都会触发 validate_thread_sharing。）
- 须在首次 ORM 前加载 Locust/gevent；重置连接请用 safe_reset_django_connections()（不可仅用
  connections.close_all()：陈旧 wrapper 上的 close() 也会触发 validate_thread_sharing 失败）。
- 目标 RPS：任务表 target_rps 有值时，每次请求后按「当前活跃用户数 / target_rps − 本次耗时」补 gevent.sleep（再叠加 think_time）。
- 阶段3 分布式：可在此模块替换为 Master/Worker 启动或远程 runner，与单机 Environment 创建解耦。

依赖：locust==2.15.1
"""
import json
import logging
import time
import warnings
from urllib.parse import urlparse

warnings.filterwarnings("ignore", message="Monkey-patching ssl")

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "EasyTesting.settings")
try:
    django.setup()
except Exception:
    pass

import requests
from django.conf import settings as django_settings
from django.db import close_old_connections, connections
from django.utils import timezone

from test_manager.utils.performance_assertions import run_assertions
from test_manager.utils.performance_config import (
    CSV_STRATEGY_PER_ITERATION,
    CSV_STRATEGY_PER_USER,
    PerformanceConfigError,
    validate_extra_config_for_task,
)
from test_manager.utils.performance_csv import CsvRowProvider, load_csv_rows, replace_placeholders_obj

logger = logging.getLogger(__name__)


def safe_reset_django_connections() -> None:
    """
    gevent patch 前后 _thread.get_ident() 可能从 OS 线程 id 变为 greenlet id；此时
    connections.close_all() 会因 validate_thread_sharing 失败（甚至 except 吞掉后仍留下陈旧
    wrapper），后续 ORM 继续复用坏连接。

    对每个已初始化的连接：先 inc_thread_sharing 再 close，再 dec；最后 del 掉 thread-local
    中的别名，强制下次访问新建 DatabaseWrapper（与当前 identity 一致）。
    """
    for alias in list(connections):
        if not hasattr(connections._connections, alias):
            continue
        conn = getattr(connections._connections, alias)
        try:
            conn.inc_thread_sharing()
            try:
                conn.close()
            finally:
                try:
                    conn.dec_thread_sharing()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            del connections[alias]
        except Exception:
            try:
                delattr(connections._connections, alias)
            except Exception:
                pass
    close_old_connections()


def _json_body_utf8_bytes(obj):
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


def _get_locust_imports():
    import gevent
    from gevent.lock import RLock

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        from locust import HttpUser, LoadTestShape, task
        from locust.env import Environment

    return gevent, RLock, HttpUser, LoadTestShape, task, Environment


def _build_full_url(base_url: str, interface_url: str, request_params: dict) -> str:
    from urllib.parse import urlencode

    base_url = (base_url or "").strip().rstrip("/")
    interface_url = (interface_url or "").strip()

    parsed = urlparse(interface_url)
    if parsed.scheme and parsed.netloc:
        full_base = f"{parsed.scheme}://{parsed.netloc}"
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
    else:
        full_base = base_url
        path = interface_url if interface_url.startswith("/") else f"/{interface_url}"

    # 兼容 list 格式 request_params
    if isinstance(request_params, list):
        params_dict = {}
        for item in request_params:
            if isinstance(item, dict) and item.get("key"):
                params_dict[item["key"]] = item.get("value", "")
        request_params = params_dict
    if request_params and isinstance(request_params, dict):
        params_str = urlencode({k: v for k, v in request_params.items() if v is not None})
        if params_str:
            path = f"{path}{'&' if '?' in path else '?'}{params_str}"

    if not path.startswith("/"):
        path = f"/{path}"
    return f"{full_base.rstrip('/')}{path}"


def _normalize_headers(raw_headers) -> dict:
    if not raw_headers:
        return {}
    if isinstance(raw_headers, dict):
        result = {}
        for k, v in raw_headers.items():
            k = str(k).strip()
            if not k:
                continue
            if isinstance(v, dict) and "value" in v:
                v = v.get("value")
            result[k] = str(v) if v is not None else ""
        return result
    if isinstance(raw_headers, list):
        result = {}
        for item in raw_headers:
            if isinstance(item, dict):
                k = item.get("key") or item.get("name")
                v = item.get("value")
                if k:
                    result[str(k)] = str(v) if v is not None else ""
        return result
    return {}


def _sanitize_headers_for_http(headers: dict) -> dict:
    result = {}
    for k, v in headers.items():
        k_str = str(k) if k else ""
        v_str = str(v) if v is not None else ""
        k_safe = k_str.encode("latin-1", "replace").decode("latin-1")
        v_safe = v_str.encode("latin-1", "replace").decode("latin-1")
        result[k_safe] = v_safe
    return result


class ErrorClassificationCounters:
    """Locust 多协程下错误分类计数（gevent 兼容）。"""

    KEYS = ("http_status_error", "timeout", "connection_error", "assertion_failure")

    def __init__(self, lock):
        self._lock = lock
        self._data = {k: 0 for k in self.KEYS}

    def inc(self, key: str):
        if key not in self._data:
            key = "http_status_error"
        with self._lock:
            self._data[key] += 1

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self._data)


def _parse_host_path(full_url: str, fallback_base: str) -> tuple[str, str]:
    parsed = urlparse(full_url)
    if parsed.scheme and parsed.netloc:
        host = f"{parsed.scheme}://{parsed.netloc}"
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
    else:
        host = (fallback_base or "").strip().rstrip("/")
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        if not path.startswith("/"):
            path = f"/{path}"
    return host, path


def run_locust_test(task_id: int) -> bool:
    from test_manager.models import PerformanceTestTask, PerformanceTestResult

    # 必须先加载 gevent/Locust，再建立 DB 连接；否则先连库后 patch 会导致压测结束后 ORM 身份不一致。
    gevent, RLock, HttpUser, LoadTestShape, task_decorator, Environment = _get_locust_imports()

    safe_reset_django_connections()

    try:
        task = PerformanceTestTask.objects.select_related("project", "environment", "interface").get(
            id=task_id
        )
        if task.status != PerformanceTestTask.STATUS_DRAFT:
            logger.warning(f"任务 {task_id} 状态非草稿，当前: {task.status}")
            return False

        try:
            cfg_summary = validate_extra_config_for_task(task.extra_config, task.run_time)
        except PerformanceConfigError as e:
            logger.error(f"任务 {task_id} 配置非法: {e}")
            safe_reset_django_connections()
            _mark_task_failed(task_id)
            return False
        except Exception as e:
            logger.exception(f"校验配置失败: {e}")
            safe_reset_django_connections()
            _mark_task_failed(task_id)
            return False

        task.status = PerformanceTestTask.STATUS_RUNNING
        task.executed_at = timezone.now()
        _upd = ["status", "executed_at"]
        _mode = str(getattr(django_settings, "PERFORMANCE_TEST_EXECUTOR", "process")).strip().lower() or "process"
        if _mode == "process":
            task.runner_pid = os.getpid()
            _upd.append("runner_pid")
        task.save(update_fields=_upd)

    except PerformanceTestTask.DoesNotExist:
        logger.error(f"性能测试任务不存在: {task_id}")
        return False
    except Exception as e:
        logger.exception(f"查询/更新任务失败: {e}")
        safe_reset_django_connections()
        _mark_task_failed(task_id)
        return False

    try:
        interface = task.interface
        request_method = (interface.method or "GET").upper()
        request_url = interface.url or ""
        request_headers_template = _normalize_headers(interface.request_headers)
        request_params_template = interface.request_params or {}
        request_body_template = interface.request_body or {}
        request_body_format = getattr(interface, "request_body_format", "json") or "json"

        env_obj = task.environment
        base_url = (env_obj.base_url or "").strip().rstrip("/")

        extra_config = task.extra_config or {}
        timeout = int(extra_config.get("timeout", 30))

        assertions = cfg_summary["assertions"]
        stages = cfg_summary["stages"]
        think_time_ms = cfg_summary["think_time_ms"]
        csv_strategy = cfg_summary["csv_read_strategy"]

        csv_provider: CsvRowProvider | None = None
        if task.csv_file:
            path = task.csv_file.path
            rows = load_csv_rows(path)
            csv_provider = CsvRowProvider(rows, csv_strategy)

        counter_lock = RLock()
        err_counters = ErrorClassificationCounters(counter_lock)

        method = request_method
        timeout_sec = timeout

        _initial_full = _build_full_url(base_url, request_url, request_params_template)
        initial_host, _ = _parse_host_path(_initial_full, base_url)
        if not str(initial_host).startswith("http"):
            initial_host = f"http://{initial_host}" if initial_host else "http://127.0.0.1"

        target_rps_val = getattr(task, "target_rps", None)
        if target_rps_val is not None:
            try:
                target_rps_val = float(target_rps_val)
                if target_rps_val <= 0:
                    target_rps_val = None
            except (TypeError, ValueError):
                target_rps_val = None
        base_users_for_rps = max(1, int(task.total_users or 1))

        def make_stage_shape(stage_list):
            class StageShape(LoadTestShape):
                def tick(self):
                    run_time = self.get_run_time()
                    for st in stage_list:
                        dur = st["duration_sec"]
                        if run_time < dur:
                            return st["users"], st["spawn_rate"]
                        run_time -= dur
                    return None

            return StageShape

        def build_user_class():
            class DynamicApiUser(HttpUser):
                host = initial_host

                connection_timeout = timeout_sec
                network_timeout = timeout_sec

                def on_start(self):
                    self._csv_fixed_idx = None
                    if csv_provider and csv_strategy == CSV_STRATEGY_PER_USER:
                        self._csv_fixed_idx = csv_provider.assign_user_index()

                @task_decorator
                def _call_api(self):
                    row: dict = {}
                    if csv_provider:
                        if csv_strategy == CSV_STRATEGY_PER_USER:
                            assert self._csv_fixed_idx is not None
                            row = csv_provider.get_row_for_user_index(self._csv_fixed_idx)
                        else:
                            row = csv_provider.get_row_for_iteration()

                    params = replace_placeholders_obj(request_params_template, row)
                    headers = replace_placeholders_obj(request_headers_template, row)
                    body = replace_placeholders_obj(request_body_template, row)

                    full_url = _build_full_url(base_url, request_url, params)
                    host_part, path_part = _parse_host_path(full_url, base_url)
                    if host_part:
                        self.host = host_part
                    headers_h = _sanitize_headers_for_http(headers)

                    def handle_response(resp):
                        sc = resp.status_code
                        if sc is None or sc >= 400:
                            err_counters.inc("http_status_error")
                            resp.failure(f"HTTP {sc}")
                            return
                        if not assertions:
                            return
                        try:
                            text = resp.text or ""
                            data = json.loads(text) if text else None
                        except json.JSONDecodeError:
                            err_counters.inc("assertion_failure")
                            resp.failure("响应非 JSON，无法断言")
                            return
                        ok, _msg = run_assertions(data, assertions)
                        if not ok:
                            err_counters.inc("assertion_failure")
                            resp.failure("business assertion failed")

                    t0 = time.perf_counter()
                    try:
                        if method in ("GET", "DELETE", "HEAD"):
                            if request_body_format == "json" and body:
                                h = headers_h.copy()
                                if "Content-Type" not in h:
                                    h["Content-Type"] = "application/json; charset=utf-8"
                                with self.client.request(
                                    method,
                                    path_part,
                                    data=_json_body_utf8_bytes(body),
                                    headers=h,
                                    catch_response=True,
                                    name="/api",
                                ) as response:
                                    handle_response(response)
                            else:
                                with self.client.request(
                                    method, path_part, headers=headers_h, catch_response=True, name="/api"
                                ) as response:
                                    handle_response(response)
                        else:
                            if request_body_format == "form-data":
                                with self.client.request(
                                    method,
                                    path_part,
                                    data=body if isinstance(body, dict) else {},
                                    headers=headers_h,
                                    catch_response=True,
                                    name="/api",
                                ) as response:
                                    handle_response(response)
                            else:
                                h = headers_h.copy()
                                if "Content-Type" not in h:
                                    h["Content-Type"] = "application/json; charset=utf-8"
                                payload = body if body else {}
                                with self.client.request(
                                    method,
                                    path_part,
                                    data=_json_body_utf8_bytes(payload),
                                    headers=h,
                                    catch_response=True,
                                    name="/api",
                                ) as response:
                                    handle_response(response)
                    except requests.exceptions.Timeout:
                        err_counters.inc("timeout")
                    except (requests.exceptions.ConnectionError, OSError):
                        err_counters.inc("connection_error")

                    elapsed = time.perf_counter() - t0
                    if target_rps_val is not None:
                        try:
                            u = int(
                                getattr(getattr(self.environment, "runner", None), "user_count", 0) or 0
                            )
                        except Exception:
                            u = 0
                        if u < 1:
                            u = base_users_for_rps
                        interval = float(u) / float(target_rps_val)
                        gevent.sleep(max(0.0, interval - elapsed))

                    if think_time_ms > 0:
                        gevent.sleep(think_time_ms / 1000.0)

            return DynamicApiUser

        DynamicApiUser = build_user_class()
        total_users = task.total_users
        spawn_rate = task.spawn_rate
        run_time_sec = task.run_time

        use_shape = bool(stages)
        if use_shape:
            ShapeCls = make_stage_shape(stages)
            env = Environment(user_classes=[DynamicApiUser], shape_class=ShapeCls)
        else:
            env = Environment(user_classes=[DynamicApiUser])

        runner = env.create_local_runner()

        _task_id = task_id
        _runner = runner
        _start_time = time.time()
        _run_time_sec = run_time_sec
        _env = env
        _err = err_counters

        metrics_buffer: list[dict] = []

        def _collect_and_save_metrics():
            """仅在 gevent greenlet 中采集统计并追加 dict，不写 ORM。"""
            for _ in range(_run_time_sec + 5):
                gevent.sleep(1)
                if getattr(_runner, "state", "") in ("stopped", "cleanup", "stopping"):
                    break
                try:
                    stats = _env.stats
                    total = stats.total
                    user_count = getattr(_runner, "user_count", 0) or 0

                    num_requests = total.num_requests
                    num_failures = total.num_failures
                    elapsed = time.time() - _start_time
                    rps = (num_requests / elapsed) if elapsed > 0 else 0.0
                    failure_rate = (num_failures / num_requests * 100) if num_requests > 0 else 0.0

                    rt_50 = rt_90 = rt_95 = rt_99 = 0.0
                    max_rt = 0.0
                    if num_requests > 0:
                        rt_50 = float(total.get_response_time_percentile(0.50))
                        rt_90 = float(total.get_response_time_percentile(0.90))
                        rt_95 = float(total.get_response_time_percentile(0.95))
                        rt_99 = float(total.get_response_time_percentile(0.99))
                        max_rt = float(total.max_response_time or 0)

                    snap = _err.snapshot()

                    metrics_buffer.append(
                        {
                            "task_id": _task_id,
                            "timestamp": timezone.now(),
                            "active_users": user_count,
                            "requests_per_second": round(rps, 2),
                            "response_time_50": round(rt_50, 2),
                            "response_time_90": round(rt_90, 2),
                            "failure_rate": round(failure_rate, 2),
                            "p95": round(rt_95, 2),
                            "p99": round(rt_99, 2),
                            "max_response_time": round(max_rt, 2),
                            "error_classification": snap,
                        }
                    )
                except Exception as ex:
                    logger.warning(f"采集指标聚合失败: {ex}")

        def _join_metrics_greenlet(gl, timeout_sec: float) -> None:
            if gl is None:
                return
            try:
                gl.join(timeout=timeout_sec)
            except Exception:
                pass
            if not getattr(gl, "dead", True):
                try:
                    gl.kill()
                except Exception:
                    pass

        metrics_gl = None
        try:
            metrics_gl = gevent.spawn(_collect_and_save_metrics)

            if use_shape:
                runner.start_shape()
            else:
                runner.start(total_users, spawn_rate=spawn_rate)
                gevent.spawn_later(run_time_sec, runner.quit)

            runner.greenlet.join()
        finally:
            _join_metrics_greenlet(metrics_gl, timeout_sec=float(max(_run_time_sec + 30, 120)))

        safe_reset_django_connections()
        if metrics_buffer:
            close_old_connections()
            try:
                PerformanceTestResult.objects.bulk_create(
                    [PerformanceTestResult(**row) for row in metrics_buffer]
                )
            except Exception as ex:
                logger.warning("采集指标批量写入失败: %s", ex)
            finally:
                close_old_connections()
        safe_reset_django_connections()
        task.refresh_from_db()
        if task.status == PerformanceTestTask.STATUS_STOPPED:
            logger.info("性能测试任务 %s 已被手动停止，跳过完成态写入", task_id)
            return True
        task.status = PerformanceTestTask.STATUS_COMPLETED
        task.finished_at = timezone.now()
        task.runner_pid = None
        task.celery_task_id = None
        task.save(update_fields=["status", "finished_at", "runner_pid", "celery_task_id"])
        logger.info(f"性能测试任务 {task_id} 执行完成")
        return True

    except Exception as e:
        logger.exception(f"性能测试任务 {task_id} 执行异常: {e}")
        safe_reset_django_connections()
        _mark_task_failed(task_id)
        return False


def _mark_task_failed(task_id: int) -> None:
    try:
        from test_manager.models import PerformanceTestTask

        PerformanceTestTask.objects.filter(id=task_id).exclude(
            status=PerformanceTestTask.STATUS_STOPPED
        ).update(
            status=PerformanceTestTask.STATUS_FAILED,
            finished_at=timezone.now(),
            runner_pid=None,
            celery_task_id=None,
        )
    except Exception as ex:
        logger.exception(f"更新任务失败状态异常: {ex}")
