"""
场景执行报告内容构建。

场景报告 JSON 顶层结构约定（与 TestSceneExecution.node_results 对齐后归一化）::

    {
        "scene": {"id": int, "name": str, "description": str},
        "environment": {"id": int, "name": str, "project_id": int},
        "execution": {
            "id": int, "status": str,
            "created_at": str, "finished_at": str|null,
            "duration": float
        },
        "nodes": [
            {
                "node_id": str, "name": str, "status": str,
                "response": str, "error": str
            }
        ]
    }

空 node_results、缺失字段时以空列表/空字符串兼容。
project_id 强制取自 execution.environment.project_id，并校验 Project 存在。
"""

from __future__ import annotations

import json
from typing import Any

from django.template.loader import render_to_string

from test_manager.models import Project, TestReport, TestSceneExecution, TestRun

class SceneExecutionReportValidationError(ValueError):
    """场景执行报告校验失败（环境/项目缺失或非法）。"""


def _ensure_project_for_execution(execution: TestSceneExecution) -> int:
    """
    业务项目 ID 必须来自 Environment.project_id（规范口径）。
    无环境、无 project_id 或 Project 不存在时抛出明确异常，便于排查环境与项目绑定问题。
    """
    env = execution.environment
    if env is None:
        raise SceneExecutionReportValidationError(
            "无法生成场景执行报告：执行记录未关联运行环境（Environment），无法确定所属项目。"
        )
    pid = getattr(env, "project_id", None)
    if not pid:
        raise SceneExecutionReportValidationError(
            "无法生成场景执行报告：环境未绑定业务项目（Environment.project_id 为空）。"
        )
    if not Project.objects.filter(pk=pid).exists():
        raise SceneExecutionReportValidationError(
            f"无法生成场景执行报告：环境关联的项目 ID={pid} 在系统中不存在或已删除，请检查环境配置。"
        )
    return int(pid)


def _normalize_node_item(raw: dict[str, Any] | None) -> dict[str, str]:
    """将 node_results 单条映射为报告 JSON 的 nodes[] 元素（字段名与规范对齐）。"""
    if not raw:
        return {"node_id": "", "name": "", "status": "", "response": "", "error": ""}
    nid = raw.get("node_id")
    name = raw.get("node_name") or raw.get("name") or ""
    status = raw.get("status") or ""
    err = raw.get("reason") or raw.get("error_message") or raw.get("error") or ""
    resp = raw.get("response")
    response_str = ""
    if isinstance(resp, dict):
        body = resp.get("body")
        if body is not None:
            try:
                response_str = json.dumps(body, ensure_ascii=False)
            except (TypeError, ValueError):
                response_str = str(body)
        else:
            try:
                response_str = json.dumps(resp, ensure_ascii=False)
            except (TypeError, ValueError):
                response_str = str(resp)
    elif resp is not None:
        try:
            response_str = json.dumps(resp, ensure_ascii=False) if not isinstance(resp, str) else resp
        except (TypeError, ValueError):
            response_str = str(resp)
    return {
        "node_id": str(nid) if nid is not None else "",
        "name": str(name),
        "status": str(status),
        "response": response_str,
        "error": str(err) if err is not None else "",
    }


def _pretty_for_pre(obj: Any) -> str:
    """与测试运行报告一致：可 JSON 格式化的内容缩进输出，否则转字符串。"""
    if obj is None or obj == "":
        return "无数据"
    if isinstance(obj, str):
        return obj
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return str(obj)


def build_node_details_for_scene_html(raw_nodes: list[Any]) -> list[dict[str, Any]]:
    """
    解析 node_results 原始结构，生成与「测试运行」报告类似的字段：
    节点标题 + 状态行 + 请求方法/URL + 可折叠的请求头/参数/体/响应头/体/断言等。
    """
    out: list[dict[str, Any]] = []
    if not isinstance(raw_nodes, list):
        return out
    for raw in raw_nodes:
        if not isinstance(raw, dict):
            raw = {}
        name = raw.get("node_name") or raw.get("name") or "（未命名节点）"
        status_raw = raw.get("status") or ""
        status_lower = str(status_raw).lower() or "unknown"

        req = raw.get("request") if isinstance(raw.get("request"), dict) else {}
        resp = raw.get("response") if isinstance(raw.get("response"), dict) else {}

        method = req.get("method") or ""
        if hasattr(method, "upper"):
            method = str(method).upper()
        url = (req.get("url") or req.get("url_path") or "").strip() or "—"

        headers = req.get("headers")
        # params 已合并到 URL 中，不再单独读取
        body = req.get("body")

        status_code = resp.get("status_code")
        resp_headers = resp.get("headers")
        resp_body = resp.get("body")
        duration_ms = resp.get("duration_ms")

        response_body_str = _pretty_for_pre(resp_body)

        err = raw.get("reason") or raw.get("error_message") or raw.get("error") or ""
        assert_results = raw.get("assert_results")
        script_logs = raw.get("script_logs")
        pre_in = raw.get("pre_request_script_input")

        if assert_results in (None, [], {}):
            assert_pre = "无数据"
        else:
            assert_pre = _pretty_for_pre(assert_results)

        detail = {
            "name": name,
            "status": status_raw,
            "status_lower": status_lower,
            "node_id": raw.get("node_id"),
            "node_key": raw.get("node_key") or "",
            "request_method": method or "—",
            "request_url": url,    # params 已合并到 URL 中
            "request_headers_pre": _pretty_for_pre(headers),
            # request_params_pre 已移除，params 已在 URL 中展示
            "request_body_pre": _pretty_for_pre(body) if body else "无请求体",
            "response_status_code": status_code if status_code is not None else "—",
            "response_time_ms": duration_ms if duration_ms is not None else "—",
            "response_headers_pre": _pretty_for_pre(resp_headers),
            "response_body_pre": response_body_str,
            "assert_results_pre": assert_pre,
            "error_message": err,
            "script_logs_pre": _pretty_for_pre(script_logs) if script_logs else None,
            "pre_request_script_input_pre": _pretty_for_pre(pre_in) if pre_in else None,
        }
        out.append(detail)
    return out


def build_scene_execution_report_content(execution: TestSceneExecution) -> dict[str, Any]:
    """
    构建场景执行报告正文（独立于视图，便于复用与单测）。

    兼容执行中 / 成功 / 失败等状态；未完成时 finished_at、duration 等按实际字段输出。

    Returns:
        {"html": str, "json": dict} — json 为结构化数据；html 为 Django 模板渲染结果。
    """
    project_id = _ensure_project_for_execution(execution)

    scene = execution.scene
    env = execution.environment
    assert env is not None

    raw_nodes = execution.node_results or []
    if not isinstance(raw_nodes, list):
        raw_nodes = []

    normalized_nodes = []
    for item in raw_nodes:
        if isinstance(item, dict):
            normalized_nodes.append(_normalize_node_item(item))
        else:
            normalized_nodes.append(_normalize_node_item(None))

    duration_sec = (execution.duration_ms or 0) / 1000.0
    created_at = execution.started_at
    finished_at = execution.finished_at
    payload = {
        "scene": {
            "id": scene.id if scene else 0,
            "name": getattr(scene, "name", "") or "",
            "description": getattr(scene, "description", "") or "",
        },
        "environment": {
            "id": env.id,
            "name": env.name,
            "project_id": project_id,
        },
        "execution": {
            "id": execution.id,
            "status": execution.status,
            "created_at": created_at.isoformat() if created_at else "",
            "finished_at": finished_at.isoformat() if finished_at else None,
            "duration": float(duration_sec),
        },
        "nodes": normalized_nodes,
    }

    project_name = env.project.name if getattr(env, "project", None) else ""

    html = render_to_string(
        "report/scene_execution_report.html",
        {
            "execution": execution,
            "scene": scene,
            "environment": env,
            "project_id": project_id,
            "project_name": project_name,
            "duration_sec": duration_sec,
            "run_mode_display": execution.get_run_mode_display(),
            "node_details": build_node_details_for_scene_html(raw_nodes),
            "json_payload": payload,
        },
    )
    return {"html": html, "json": payload}


def save_scene_execution_test_report(
    execution: TestSceneExecution,
    user,
    *,
    name: str,
    description: str | None,
    report_format: str,
    is_public: bool,
) -> TestReport:
    """
    持久化场景执行报告（Web 与异步导出共用）。
    先 build_scene_execution_report_content，再写入 TestReport；project 取自 Environment.project。
    """
    built = build_scene_execution_report_content(execution)
    project = execution.environment.project
    report = TestReport(
        name=name,
        description=description or "",
        project=project,
        report_type="scene_execution",
        report_format=report_format,
        scene_execution=execution,
        is_public=is_public,
        created_by=user,
    )
    if report_format == "json":
        report.content = json.dumps(built["json"], ensure_ascii=False, indent=2)
    else:
        report.content = built["html"]
    report.save()
    return report


def save_test_run_test_report(
    test_run: TestRun,
    user,
    *,
    name: str,
    description: str | None,
    report_format: str,
    is_public: bool,
) -> TestReport:
    """
    持久化测试运行报告。
    从 test_run.test_results.all() 遍历生成 HTML 或 JSON 内容，创建并返回 TestReport。
    """
    if report_format == "json":
        content_data: dict[str, Any] = {
            "id": str(test_run.id),
            "name": test_run.name,
            "project": {
                "id": str(test_run.project.id),
                "name": test_run.project.name,
            },
            "environment": {
                "id": str(test_run.environment.id),
                "name": test_run.environment.name,
                "base_url": test_run.environment.base_url,
            },
            "status": test_run.status,
            "start_time": test_run.start_time.isoformat() if test_run.start_time else None,
            "end_time": test_run.end_time.isoformat() if test_run.end_time else None,
            "duration": test_run.duration,
            "results": [],
        }

        if test_run.test_suite:
            content_data["test_suite"] = {
                "id": str(test_run.test_suite.id),
                "name": test_run.test_suite.name,
            }

        for result in test_run.test_results.all():
            result_data: dict[str, Any] = {
                "id": str(result.id),
                "status": result.status,
                "response_status_code": result.response_status_code,
                "response_time": result.response_time,
                "test_case": {
                    "id": str(result.test_case.id),
                    "name": result.test_case.name,
                    "request_method": result.test_case.request_method,
                    "request_url": result.test_case.request_url,
                },
            }
            if result.response_headers:
                result_data["response_headers"] = result.response_headers
            if result.response_body:
                result_data["response_body"] = result.response_body
            if result.request_headers:
                result_data["request_headers"] = result.request_headers
            if result.request_body:
                result_data["request_body"] = result.request_body
            if result.error_message:
                result_data["error_message"] = result.error_message
            content_data["results"].append(result_data)

        content = json.dumps(content_data, ensure_ascii=False, indent=2)
    else:
        # 生成 HTML 格式报告（与旧 Django 视图相同的 collapsible 结构）
        html_parts: list[str] = [
            f"""<div class="test-report">
                <h1>{test_run.name} - 测试运行报告</h1>
                <div class="report-meta">
                    <p><strong>项目:</strong> {test_run.project.name}</p>
                    <p><strong>环境:</strong> {test_run.environment.name}</p>
                    <p><strong>状态:</strong> <span class="status-{test_run.status.lower()}">{test_run.status}</span></p>
                    <p><strong>开始时间:</strong> {test_run.start_time}</p>
                    <p><strong>结束时间:</strong> {test_run.end_time}</p>
                    <p><strong>持续时间:</strong> {test_run.duration} 秒</p>"""
        ]

        if test_run.test_suite:
            html_parts.append(
                f"""<p><strong>测试套件:</strong> {test_run.test_suite.name}</p>"""
            )

        html_parts.append("""</div><h2>测试结果</h2>""")

        for result in test_run.test_results.all():
            req_headers_str = _pretty_for_pre(result.request_headers) if result.request_headers else "无数据"
            req_body_str = str(result.request_body) if result.request_body else "无数据"
            resp_headers_str = _pretty_for_pre(result.response_headers) if result.response_headers else "无数据"
            resp_body_str = _pretty_for_pre(result.response_body) if result.response_body else "无数据"
            error_section = (
                f'<div class="error-message"><h4>错误信息</h4><pre>{result.error_message}</pre></div>'
                if result.error_message else ""
            )

            html_parts.append(f"""
                <div class="test-result">
                    <h3>{result.test_case.name}</h3>
                    <p><strong>状态:</strong> <span class="status-{result.status.lower()}">{result.status}</span></p>
                    <p><strong>请求方法:</strong> {result.test_case.request_method}</p>
                    <p><strong>请求URL:</strong> {result.test_case.request_url}</p>
                    <p><strong>响应状态码:</strong> {result.response_status_code}</p>
                    <p><strong>响应时间:</strong> {result.response_time} 毫秒</p>

                    <div class="collapsible">
                        <h4>请求头</h4>
                        <pre>{req_headers_str}</pre>
                    </div>
                    <div class="collapsible">
                        <h4>请求体</h4>
                        <pre>{req_body_str}</pre>
                    </div>
                    <div class="collapsible">
                        <h4>响应头</h4>
                        <pre>{resp_headers_str}</pre>
                    </div>
                    <div class="collapsible">
                        <h4>响应体</h4>
                        <pre>{resp_body_str}</pre>
                    </div>
                    {error_section}
                </div>""")

        html_parts.append("""
            </div>
            <style>
                .test-report { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
                .report-meta { background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                .test-result { background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin-bottom: 15px; border-left: 5px solid #ddd; }
                .collapsible { margin-top: 10px; }
                .collapsible h4 { cursor: pointer; background-color: #eee; padding: 8px; border-radius: 3px; }
                .collapsible pre { background-color: #f5f5f5; padding: 10px; border-radius: 3px; overflow-x: auto; white-space: pre-wrap; }
                .status-pass, .status-success, .status-completed { color: green; font-weight: bold; }
                .status-fail, .status-failure, .status-error, .status-failed { color: red; font-weight: bold; }
                .error-message { background-color: #ffeeee; padding: 10px; border-radius: 3px; margin-top: 10px; }
                .error-message h4 { color: red; }
            </style>
            <script>
                document.addEventListener('DOMContentLoaded', function() {{
                    document.querySelectorAll('.collapsible h4').forEach(function(h4) {{
                        h4.addEventListener('click', function() {{
                            var pre = this.nextElementSibling;
                            pre.style.display = pre.style.display === 'none' ? 'block' : 'none';
                        }});
                        h4.nextElementSibling.style.display = 'none';
                    }});
                }});
            </script>""")

        content = "\n".join(html_parts)

    report = TestReport(
        name=name,
        description=description or "",
        project=test_run.project,
        report_type="test_run",
        report_format=report_format,
        test_run=test_run,
        is_public=is_public,
        created_by=user,
    )
    report.content = content
    report.save()
    return report
