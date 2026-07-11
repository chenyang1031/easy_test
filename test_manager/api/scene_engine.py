import copy
import json
import logging
import re
import time
import base64
import uuid
import hashlib
from datetime import datetime
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urlparse, urlsplit, urlunsplit

from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)

from test_manager.env_variables_compat import variables_for_runtime
from test_manager.httprunner_executor import ASSERT_MAP, execute_test_case, get_debugtalk_functions
from test_manager.models import Environment, TestSceneExecution, TestSceneNode, SceneDownloadedFile


VAR_PATTERN = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")


class VariableResolveError(Exception):
    """变量解析失败异常。"""


def _render_with_field_context(field_name, value, variable_pool):
    """包装 render_with_variables，在 VariableResolveError 中附带字段上下文。"""
    try:
        return render_with_variables(value, variable_pool)
    except VariableResolveError as exc:
        raise VariableResolveError(f"「{field_name}」中变量解析失败: {exc}")


def _sanitize_for_json(obj):
    """递归移除不可 JSON 序列化的值（如 function），避免保存/返回时报错。"""
    if callable(obj):
        return None
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if callable(v):
                continue
            out[k] = _sanitize_for_json(v)
        return out
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj if not callable(v)]
    return obj


def _extract_filename_from_headers(response_headers, request_url, default="downloaded_file"):
    """从响应头 Content-Disposition 或 URL 中提取文件名。"""
    cd = (response_headers or {}).get("Content-Disposition", "")
    if cd:
        # filename*=UTF-8''%E4%B8%AD%E6%96%87.txt  (RFC 5987)
        # filename="export.zip"
        # RFC 5987 优先
        m = re.search(r"filename\*=(?:UTF-8|utf-8)''([^;\s]+)", cd)
        if m:
            from urllib.parse import unquote
            name = unquote(m.group(1))
            if name:
                return name
        # 普通 filename
        m = re.search(r'filename="([^"]*)"', cd)
        if not m:
            m = re.search(r"filename=([^;\s]+)", cd)
        if m:
            name = m.group(1).strip('"').strip()
            if name:
                return name
    # 从 URL 最后一段提取
    if request_url:
        path = request_url.rstrip("/")
        seg = path.rsplit("/", 1)[-1]
        if seg and "." in seg:
            return seg
    return default


@dataclass
class ProxyEnvironment:
    """复用 execute_test_case 所需的最小环境对象。"""

    base_url: str
    variables: dict
    name: str = "SceneRuntime"
    id: int = 0


@dataclass
class ProxyCase:
    """复用 execute_test_case 所需的最小用例对象。"""

    id: int
    name: str
    request_method: str
    request_url: str
    request_headers: dict
    request_body: object
    request_body_format: str
    expected_status_code: int
    validation_rules: list
    extract_params: list
    timeout: int
    upload_file: object = None
    upload_field_name: str = ""


def _resolve_value(expr, variable_pool):
    """
    解析变量表达式，支持：
    - func()：调用 debugtalk 函数，返回执行结果
    - var.path：按路径从变量池取值
    """
    expr = str(expr or "").strip()
    if not expr:
        raise VariableResolveError("变量表达式为空")

    # 支持 {{func()}} 语法：调用 debugtalk 函数
    if expr.endswith("()"):
        func_name = expr[:-2].strip()
        if func_name and func_name in variable_pool:
            fn = variable_pool[func_name]
            if callable(fn):
                try:
                    val = fn()
                    return val if val is not None else ""
                except Exception as e:
                    raise VariableResolveError(f"函数 {func_name}() 执行失败: {e}")
        raise VariableResolveError(f"函数不存在或不可调用: {expr}")

    # 按路径解析
    return _resolve_from_pool(expr, variable_pool)


def _resolve_from_pool(path_text, variable_pool):
    segments = [item for item in str(path_text).strip().split(".") if item]
    if not segments:
        raise VariableResolveError("变量表达式为空")

    current = variable_pool
    for segment in segments:
        # 支持方括号下标语法：data[0] 或 data[0][1] 或 [0]
        if "[" in segment:
            parts = re.split(r"[\[\]]+", segment)
            parts = [p for p in parts if p]
            for p in parts:
                if isinstance(current, dict) and p in current:
                    current = current[p]
                elif isinstance(current, list) and p.isdigit():
                    idx = int(p)
                    if idx < 0 or idx >= len(current):
                        raise VariableResolveError(f"数组下标越界: {p}")
                    current = current[idx]
                else:
                    raise VariableResolveError(f"变量路径不存在: {path_text}")
            continue

        if isinstance(current, dict) and segment in current:
            current = current[segment]
            continue

        if isinstance(current, list) and segment.isdigit():
            idx = int(segment)
            if idx < 0 or idx >= len(current):
                raise VariableResolveError(f"数组下标越界: {segment}")
            current = current[idx]
            continue

        raise VariableResolveError(f"变量路径不存在: {path_text}")
    return current


def _render_text_with_variables(text, variable_pool):
    """
    解析字符串中的 {{var.path}} 与 {{func()}} 表达式。
    - 整段只有一个模板时，保留原始类型（可能是 dict/list/int）
    - 否则按字符串替换，便于拼 URL/Header 等文本场景
    - 支持 {{func()}} 调用 debugtalk 函数
    """
    text = str(text)
    full_match = VAR_PATTERN.fullmatch(text.strip())
    if full_match:
        return _resolve_value(full_match.group(1), variable_pool)

    def replace_func(match):
        value = _resolve_value(match.group(1), variable_pool)
        if value is None:
            return ""
        return str(value)

    return VAR_PATTERN.sub(replace_func, text)


def _flatten_kv_for_request(payload, exclude_file=False):
    """
    将 API 资产格式 { key: { value: "x", required, type, ... } } 转为请求所需格式。
    - 普通类型：{ key: "value" }
    - file 类型：保留 { type: "File", file_path, file_name } 供执行器处理（exclude_file=True 时排除，用于 URL 参数）
    """
    if not payload or not isinstance(payload, dict):
        return {}
    result = {}
    for key, val in payload.items():
        key = str(key).strip()
        if not key:
            continue
        if isinstance(val, dict):
            if val.get("type") == "File" and ("file_path" in val or "file_url" in val):
                if not exclude_file:
                    result[key] = val
            elif "value" in val:
                result[key] = val["value"]
            else:
                result[key] = val
        else:
            result[key] = val
    return result


def _list_params_to_dict(params_list):
    """将结构化数组 [{key, type, value, required, default, desc, validation}] 转为 {key: {value, type, ...}} 格式，
    保留元数据供 _flatten_kv_for_request 使用（与节点存储的 flat dict {key: value} 不同）。"""
    if not isinstance(params_list, list):
        return {}
    result = {}
    for item in params_list:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key", "")).strip()
        if not key:
            continue
        entry = {"value": item.get("value", "")}
        for field in ("type", "required", "default", "desc", "validation"):
            if field in item:
                entry[field] = item[field]
        result[key] = entry
    return result


def _effective_request_params_for_node(node):
    """
    合并 API 资产上的默认 request_params 与场景节点上的覆盖（节点键优先）。
    仅使用 node.request_params 时，若节点未同步/未填写而资产上有 Query 等参数，
    前置脚本中的 pm.request.params 会一直是 {}，与真实请求不一致。
    """
    if not node or not getattr(node, "api_asset", None):
        return {}
    asset_p = getattr(node.api_asset, "request_params", None) or {}
    node_p = getattr(node, "request_params", None) or {}
    # 兼容 ApiAsset 的 list 格式 request_params
    if isinstance(asset_p, list):
        asset_p = _list_params_to_dict(asset_p)
    if not isinstance(asset_p, dict):
        asset_p = {}
    if not isinstance(node_p, dict):
        node_p = {}
    merged = dict(asset_p)
    merged.update(node_p)
    return merged


def _has_file_in_payload(payload):
    """检测 payload 中是否存在 file 类型参数。"""
    if not payload or not isinstance(payload, dict):
        return False
    for val in payload.values():
        if isinstance(val, dict) and val.get("type") == "File" and ("file_path" in val or "file_url" in val):
            return True
    return False


def _unwrap_raw_body(body):
    """若 body 为 {"_raw": "xxx"} 格式（HAR/goreplay 导入或脚本回退），解包为原始字符串。"""
    if isinstance(body, dict) and "_raw" in body and len(body) == 1:
        return body["_raw"]
    if isinstance(body, dict) and "mode" in body:
        mode = body.get("mode", "raw")
        if mode == "raw":
            raw = body.get("raw", "")
            if raw:
                try:
                    return json.loads(raw)
                except (json.JSONDecodeError, ValueError):
                    return raw
            return {}
        if mode == "urlencoded":
            result = {}
            for item in body.get("urlencoded") or []:
                if isinstance(item, dict) and item.get("key") and not item.get("disabled"):
                    result[item["key"]] = item.get("value", "")
            return result
        if mode == "formdata":
            result = {}
            for item in body.get("formdata") or []:
                if isinstance(item, dict) and item.get("key") and not item.get("disabled"):
                    if item.get("type") == "file":
                        result[item["key"]] = {"type": "File", "file_path": item.get("src", "")}
                    else:
                        result[item["key"]] = item.get("value", "")
            return result
    return body


def _handle_file_params(resolved_body, resolved_params_all, resolved_params_url, node_body_type, api_format):
    """
    抽离的文件参数处理逻辑：检测、格式切换、参数拆分合并。
    返回 (body_for_request, params_for_url, effective_format)。
    支持多 file 参数，全部合并到 body。
    """
    has_file = _has_file_in_payload(resolved_body) or _has_file_in_payload(resolved_params_all)
    if has_file:
        effective_format = "form-data"
    else:
        effective_format = node_body_type or api_format

    body_for_request = resolved_body
    if isinstance(body_for_request, str):
        try:
            body_for_request = json.loads(body_for_request)
        except (json.JSONDecodeError, ValueError):
            pass
    body_for_request = body_for_request or {}
    if isinstance(body_for_request, dict):
        body_for_request = dict(body_for_request)

    if effective_format == "form-data" and resolved_params_all:
        for key, val in resolved_params_all.items():
            if isinstance(val, dict) and val.get("type") == "File":
                if not isinstance(body_for_request, dict):
                    body_for_request = {}
                body_for_request[key] = val

    return body_for_request, resolved_params_url, effective_format


def render_with_variables(payload, variable_pool):
    """递归解析请求内容中的变量。"""
    if payload is None:
        return None
    if isinstance(payload, dict):
        return {k: render_with_variables(v, variable_pool) for k, v in payload.items()}
    if isinstance(payload, list):
        return [render_with_variables(item, variable_pool) for item in payload]
    if isinstance(payload, str):
        return _render_text_with_variables(payload, variable_pool)
    return payload


def _normalize_response_body_path(context, path):
    """
    兼容误写的 $.response.body.xxx。

    场景执行里 node_context['response'] 已是 HTTP 解析后的 JSON 体，没有再多一层 body。
    若真实响应里也没有 body 字段，则将 response.body 视为 response 的别名（与部分文档/模板写法对齐）。
    """
    if not path or not isinstance(context, dict):
        return path
    resp = context.get("response")
    if not isinstance(resp, dict) or "body" in resp:
        return path
    if path == "response.body":
        return "response"
    if path.startswith("response.body."):
        return "response." + path[len("response.body.") :]
    return path


def _extract_by_path(context, path):
    path = str(path or "").strip()
    if not path:
        return context
    if path.startswith("$."):
        path = path[2:]
    path = _normalize_response_body_path(context, path)
    return _resolve_from_pool(path, context)


def _normalize_assert_rule(rule):
    if not isinstance(rule, dict):
        return None
    if {"path", "comparator", "expected"} <= set(rule.keys()):
        return {
            "path": rule.get("path"),
            "comparator": str(rule.get("comparator") or "eq").lower(),
            "expected": rule.get("expected"),
        }
    if len(rule) == 1:
        comparator = next(iter(rule.keys()))
        value = rule.get(comparator)
        if isinstance(value, (list, tuple)) and len(value) == 2:
            return {
                "path": value[0],
                "comparator": str(comparator or "eq").lower(),
                "expected": value[1],
            }
    return None


def _assert_response_body(assert_details, actual_body, expected_body, default_on_failed=TestSceneNode.ON_FAILED_STOP):
    """
    对比预期响应体与实际响应体，生成断言细节追加到 assert_details。
    default_on_failed 指定基线比对失败时的策略，默认 stop 兼容老行为。
    """
    if expected_body is None:
        return
    if not isinstance(expected_body, dict):
        # 标量或列表：整体比对
        passed = (actual_body == expected_body)
        assert_details.append(
            {
                "passed": passed,
                "path": "$response.body",
                "comparator": "equals",
                "expected": expected_body,
                "actual": actual_body,
                "reason": "" if passed else f"响应体不匹配，期望 {expected_body}，实际 {actual_body}",
                "on_failed": default_on_failed,
                "source": "expected_response_body",
            }
        )
        return

    # dict 深度递归比对
    for exp_key, exp_val in expected_body.items():
        actual_val = actual_body.get(exp_key) if isinstance(actual_body, dict) else None
        if isinstance(exp_val, dict) and isinstance(actual_val, dict):
            _assert_response_body(assert_details, actual_val, exp_val, default_on_failed)
        elif isinstance(exp_val, list) and isinstance(actual_val, list):
            if len(exp_val) == 0 and len(actual_val) > 0:
                passed = False
            else:
                passed = (actual_val == exp_val)
            assert_details.append(
                {
                    "passed": passed,
                    "path": f"$response.body.{exp_key}",
                    "comparator": "equals",
                    "expected": exp_val,
                    "actual": actual_val,
                    "reason": "" if passed else f"响应体字段 {exp_key} 不匹配",
                    "on_failed": default_on_failed,
                    "source": "expected_response_body",
                }
            )
        else:
            passed = (actual_val == exp_val)
            assert_details.append(
                {
                    "passed": passed,
                    "path": f"$response.body.{exp_key}",
                    "comparator": "equals",
                    "expected": exp_val,
                    "actual": actual_val,
                    "reason": "" if passed else f"响应体字段 {exp_key} 不匹配，期望 {exp_val}，实际 {actual_val}",
                    "on_failed": default_on_failed,
                    "source": "expected_response_body",
                }
            )


def _assert_response_headers(assert_details, actual_headers, expected_headers, default_on_failed=TestSceneNode.ON_FAILED_STOP):
    """
    对比预期响应头与实际响应头，生成断言细节追加到 assert_details。
    忽略大小写匹配 header 名称。
    default_on_failed 指定基线比对失败时的策略，默认 stop 兼容老行为。
    """
    if not expected_headers or not isinstance(expected_headers, dict):
        return
    if not actual_headers or not isinstance(actual_headers, dict):
        for h_name, h_val in expected_headers.items():
            assert_details.append(
                {
                    "passed": False,
                    "path": f"$response.headers.{h_name}",
                    "comparator": "equals",
                    "expected": h_val,
                    "actual": None,
                    "reason": f"响应头 {h_name} 不存在",
                    "on_failed": default_on_failed,
                    "source": "expected_response_headers",
                }
            )
        return
    # 忽略大小写建索引
    actual_lower = {k.lower(): v for k, v in actual_headers.items()}
    for h_name, h_val in expected_headers.items():
        actual_val = actual_lower.get(h_name.lower())
        passed = (actual_val == h_val)
        assert_details.append(
            {
                "passed": passed,
                "path": f"$response.headers.{h_name}",
                "comparator": "equals",
                "expected": h_val,
                "actual": actual_val,
                "reason": "" if passed else f"响应头 {h_name} 不匹配，期望 {h_val}，实际 {actual_val}",
                "on_failed": default_on_failed,
                "source": "expected_response_headers",
            }
        )


def evaluate_assertions(assert_rules, node_context, variable_pool,
                        expected_response_body=None, expected_response_headers=None,
                        default_on_failed=TestSceneNode.ON_FAILED_STOP):
    """
    断言执行引擎：
    - 兼容 {"path","comparator","expected"} 与 {"eq": ["path", value]} 两种格式
    - 支持 expected_response_body / expected_response_headers 作为基线断言
    - 返回详细对比，便于排障和前端可视化展示
    """
    if not isinstance(assert_rules, list):
        assert_rules = []

    details = []
    all_passed = True
    for raw_rule in assert_rules:
        rule = _normalize_assert_rule(raw_rule)
        if not rule:
            details.append(
                {
                    "passed": False,
                    "reason": "断言规则格式非法",
                    "raw_rule": raw_rule,
                }
            )
            all_passed = False
            continue

        if raw_rule.get("enabled", True) is False:
            details.append(
                {
                    "passed": True,
                    "skipped": True,
                    "reason": "断言已禁用",
                    "raw_rule": raw_rule,
                }
            )
            continue

        comparator = rule["comparator"]
        path = rule["path"]
        on_failed = str(raw_rule.get("on_failed") or TestSceneNode.ON_FAILED_STOP).lower()
        try:
            expected = render_with_variables(rule["expected"], variable_pool)
        except VariableResolveError as exc:
            details.append(
                {
                    "passed": False,
                    "path": path,
                    "comparator": comparator,
                    "expected": rule["expected"],
                    "actual": None,
                    "reason": f"断言期望值中变量解析失败: {exc}",
                    "on_failed": on_failed,
                }
            )
            if on_failed != TestSceneNode.ON_FAILED_CONTINUE:
                all_passed = False
            continue
        try:
            actual = _extract_by_path(node_context, path)
        except Exception as exc:
            details.append(
                {
                    "passed": False,
                    "path": path,
                    "comparator": comparator,
                    "expected": expected,
                    "actual": None,
                    "reason": f"读取断言路径失败: {exc}",
                    "on_failed": on_failed,
                }
            )
            if on_failed != TestSceneNode.ON_FAILED_CONTINUE:
                all_passed = False
            continue

        assert_func = ASSERT_MAP.get(comparator)
        if not assert_func:
            details.append(
                {
                    "passed": False,
                    "path": path,
                    "comparator": comparator,
                    "expected": expected,
                    "actual": actual,
                    "reason": f"不支持的比较器: {comparator}",
                    "on_failed": on_failed,
                }
            )
            if on_failed != TestSceneNode.ON_FAILED_CONTINUE:
                all_passed = False
            continue

        try:
            passed = bool(assert_func(actual, expected))
        except Exception as exc:
            passed = False
            reason = f"断言执行异常: {exc}"
        else:
            reason = ""

        details.append(
            {
                "passed": passed,
                "path": path,
                "comparator": comparator,
                "expected": expected,
                "actual": actual,
                "reason": reason,
                "on_failed": on_failed,
            }
        )
        if not passed and on_failed != TestSceneNode.ON_FAILED_CONTINUE:
            all_passed = False

    # 基线断言：expected_response_body（深度递归比对）
    actual_body = node_context.get("response")
    if expected_response_body not in (None, {}):
        _assert_response_body(details, actual_body or {}, expected_response_body, default_on_failed)

    # 基线断言：expected_response_headers（忽略大小写比对）
    actual_headers = node_context.get("headers") or {}
    _assert_response_headers(details, actual_headers, expected_response_headers, default_on_failed)

    # 基线断言失败时：按 default_on_failed 决定是否影响整体结果
    for d in details:
        if d.get("source") in ("expected_response_body", "expected_response_headers"):
            if not d.get("passed") and str(d.get("on_failed", "")).lower() != TestSceneNode.ON_FAILED_CONTINUE:
                all_passed = False

    return all_passed, details


def _node_has_soft_assertion_failure(assert_details):
    """是否存在「失败继续」且未通过的断言（节点仍可能为 passed）。"""
    if not isinstance(assert_details, list):
        return False
    for d in assert_details:
        if d.get("skipped"):
            continue
        if not d.get("passed") and str(d.get("on_failed", "")).lower() == TestSceneNode.ON_FAILED_CONTINUE:
            return True
    return False


def _soft_assertion_failure_count(assert_details):
    """「失败继续」且未通过的断言条数。"""
    if not isinstance(assert_details, list):
        return 0
    n = 0
    for d in assert_details:
        if d.get("skipped"):
            continue
        if not d.get("passed") and str(d.get("on_failed", "")).lower() == TestSceneNode.ON_FAILED_CONTINUE:
            n += 1
    return n


def _normalize_extract_rule(rule):
    if not isinstance(rule, dict):
        return None
    name = str(rule.get("name") or "").strip()
    path = str(rule.get("path") or "").strip()
    if not name or not path:
        return None
    return {"name": name, "path": path}


def apply_extract_rules(extract_rules, node_context, variable_pool):
    """根据提取规则写入变量池。"""
    if not isinstance(extract_rules, list):
        return {}
    extracted = {}
    for raw_rule in extract_rules:
        rule = _normalize_extract_rule(raw_rule)
        if not rule:
            continue
        value = _extract_by_path(node_context, rule["path"])
        variable_pool[rule["name"]] = value
        extracted[rule["name"]] = value
    return extracted


def _split_base_and_path(url_text, scene_base_url):
    url_text = str(url_text or "").strip()
    scene_base_url = str(scene_base_url or "").strip().rstrip("/")
    if not url_text:
        return scene_base_url, ""

    parsed = urlparse(url_text)
    if parsed.scheme and parsed.netloc:
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        return base_url, path

    return scene_base_url, url_text


def _merge_query_params_into_url(request_url, params_for_url):
    """
    将 params_for_url 合并进 URL 的 query，避免资产路径上已带 ?pageNo=1 时再拼接一次导致参数重复。
    同名键以 params_for_url 为准。
    """
    request_url = str(request_url or "").strip()
    params_for_url = params_for_url or {}
    if not params_for_url:
        return request_url
    parts = urlsplit(request_url)
    path = parts.path or "/"
    merged = {}
    if parts.query:
        for k, vlist in parse_qs(parts.query, keep_blank_values=True).items():
            merged[k] = vlist[0] if len(vlist) == 1 else vlist
    for k, v in params_for_url.items():
        merged[k] = v
    query = urlencode(merged, doseq=True)
    return urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))


def _build_proxy_case(node, resolved_headers, resolved_params_url, resolved_params_all, resolved_body, resolved_url):
    """
    构建 ProxyCase 供 execute_test_case 执行。
    文件检测、格式切换、参数拆分合并由 _handle_file_params 处理。
    """
    timeout = int(node.timeout) if node.timeout else 30
    api_format = getattr(node.api_asset, "request_body_format", "json") or "json"
    node_body_type = getattr(node, "body_type", None) or api_format

    body_for_request, params_for_url, effective_format = _handle_file_params(
        resolved_body, resolved_params_all, resolved_params_url, node_body_type, api_format
    )

    request_url = _merge_query_params_into_url(str(resolved_url or ""), params_for_url or {})

    # 智能推断默认期望状态码：用户未显式配置时根据 REST 惯例自动设置
    _raw_status = node.expected_status_code
    if _raw_status:
        final_status_code = int(_raw_status)
    else:
        method = str(node.effective_method or "").upper()
        if method == "DELETE":
            final_status_code = 204
        elif method == "POST":
            final_status_code = 201
        elif method == "PUT":
            final_status_code = 200
        elif method == "PATCH":
            final_status_code = 200
        else:
            final_status_code = 200

    return ProxyCase(
        id=node.id,
        name=node.name,
        request_method=node.effective_method or "GET",
        request_url=request_url,
        request_headers=resolved_headers or {},
        request_body=body_for_request,
        request_body_format=effective_format,
        expected_status_code=final_status_code,
        validation_rules=[],
        extract_params=[],
        timeout=timeout,
    )


def _build_initial_variable_pool(scene, runtime_config_override=None):
    """
    初始化变量池，支持场景变量、运行时变量、环境变量、debugtalk 函数四层合并。
    环境变量注入全局变量池，可通过 {{变量名}} 直接引用，优先级最高。
    debugtalk 函数可通过 {{func()}} 调用。
    """
    variable_pool = {}
    # 先注入 debugtalk 函数（供 {{func()}} 调用）
    variable_pool.update(get_debugtalk_functions())

    # --- 场景变量预渲染 ---
    # 将场景变量中的 {{func()}} 和 {{var}} 预先解析一次，一次执行内所有节点共享同一值。
    # 支持变量间相互引用，使用迭代解析（最多 5 轮）避免定义顺序问题。
    scene_vars = copy.deepcopy(scene.variables or {})
    scene_var_keys = set()
    remaining = dict(scene_vars)
    for _round in range(5):
        if not remaining:
            break
        for key in list(remaining.keys()):
            try:
                variable_pool[key] = render_with_variables(remaining[key], variable_pool)
                scene_var_keys.add(key)
                del remaining[key]
            except VariableResolveError:
                pass  # 依赖的变量尚未就绪，下一轮再试
    # 仍未解析的保留原文（不阻塞执行，当前行为保底）
    for key, raw in remaining.items():
        variable_pool[key] = raw
        scene_var_keys.add(key)
        logger.warning("场景变量预渲染未能解析（将在节点执行时保留原文）: %s = %s", key, raw)
    # 同时注册到 scene 前缀下，支持 {{scene.var}} 和 {{var}} 两种引用方式
    variable_pool["scene"] = {k: variable_pool[k] for k in scene_var_keys}

    # --- 运行时变量预渲染（优先级高于场景变量） ---
    runtime_config = dict(runtime_config_override or scene.runtime_config or {})
    runtime_variables = dict(runtime_config.get("variables") or {})
    remaining_rv = dict(runtime_variables)
    for _round in range(5):
        if not remaining_rv:
            break
        for key in list(remaining_rv.keys()):
            try:
                variable_pool[key] = render_with_variables(remaining_rv[key], variable_pool)
                del remaining_rv[key]
            except VariableResolveError:
                pass
    for key, raw in remaining_rv.items():
        variable_pool[key] = raw

    env_variables = {}
    env_obj = None
    env_id = runtime_config.get("environment_id")
    if env_id:
        env_obj = Environment.objects.filter(id=env_id).first()
        if env_obj:
            scene_project_id = getattr(scene.project, "platform_project_id", None)
            if scene_project_id and env_obj.project_id != scene_project_id:
                raise VariableResolveError("运行环境不属于当前场景绑定的平台项目")
            env_variables = variables_for_runtime(env_obj.variables or {})
    variable_pool["env"] = env_variables
    variable_pool.update(env_variables)
    return variable_pool, env_obj


def _get_effective_env_for_node(node, scene, global_env_obj, effective_runtime_config,
                             preloaded_envs=None):
    """
    按优先级获取节点生效的环境对象（用于前置脚本等）。
    接口专属环境 > 场景环境 > 全局环境。

    preloaded_envs: dict {env_id: env_obj}，由调用方预加载以避免 N+1 查询。
    若未传入则使用 node.environment（Django ORM select_related 预加载结果）。
    """
    platform_project_id = getattr(scene.project, "platform_project_id", None)

    if node.environment_id:
        if preloaded_envs and node.environment_id in preloaded_envs:
            node_env = preloaded_envs[node.environment_id]
        else:
            node_env = getattr(node, "environment", None)
        if node_env and (not platform_project_id or node_env.project_id == platform_project_id):
            return node_env

    scene_env_id = (effective_runtime_config or {}).get("environment_id")
    if scene_env_id:
        if preloaded_envs and scene_env_id in preloaded_envs:
            scene_env = preloaded_envs[scene_env_id]
        else:
            scene_env = Environment.objects.filter(id=scene_env_id).first()
        if scene_env and (not platform_project_id or scene_env.project_id == platform_project_id):
            return scene_env

    return global_env_obj


def _resolve_node_base_url(node, scene, global_env_obj, effective_runtime_config,
                         preloaded_envs=None):
    """
    按优先级解析节点 base_url：接口自定义 > 场景自定义 > 全局环境。
    返回 (base_url, source_label) 用于日志标注。

    preloaded_envs: dict {env_id: env_obj}，由调用方预加载以避免 N+1 查询。
    若未传入则使用 node.environment（Django ORM select_related 预加载结果）。
    """
    platform_project_id = getattr(scene.project, "platform_project_id", None)

    # 1. 接口自定义域名（最高优先级）
    custom_url = str(node.custom_base_url or "").strip()
    if custom_url:
        base = custom_url.rstrip("/")
        if "://" in base:
            parsed = urlparse(custom_url)
            base = f"{parsed.scheme}://{parsed.netloc}"
        return base, "接口自定义域名"

    # 2. 接口专属环境
    if node.environment_id:
        if preloaded_envs and node.environment_id in preloaded_envs:
            node_env = preloaded_envs[node.environment_id]
        else:
            node_env = getattr(node, "environment", None)
        if node_env and node_env.base_url:
            if platform_project_id and node_env.project_id != platform_project_id:
                pass  # 环境不属于项目，降级
            else:
                return node_env.base_url.rstrip("/"), f"接口环境({node_env.name})"

    # 3. 场景专属环境（runtime_config.environment_id）
    scene_env_id = (scene.runtime_config or {}).get("environment_id")
    if scene_env_id:
        if preloaded_envs and scene_env_id in preloaded_envs:
            scene_env = preloaded_envs[scene_env_id]
        else:
            scene_env = Environment.objects.filter(id=scene_env_id).first()
        if scene_env and scene_env.base_url:
            if platform_project_id and scene_env.project_id != platform_project_id:
                pass
            else:
                return scene_env.base_url.rstrip("/"), f"场景环境({scene_env.name})"

    # 4. 全局环境（执行时选择）
    if global_env_obj and global_env_obj.base_url:
        return global_env_obj.base_url.rstrip("/"), f"全局环境({global_env_obj.name})"

    return effective_runtime_config.get("base_url", "").rstrip("/"), "未指定"


def execute_scene(scene, operator, run_mode=TestSceneExecution.RUN_MODE_ALL, target_node=None, runtime_config_override=None):
    """
    场景执行引擎主入口。
    核心流程：
    1) 读取并排序节点
    2) 变量渲染并发起接口调用（复用 execute_test_case）
    3) 执行断言与提取，更新变量池
    4) 按 on_failed 策略决定继续或终止
    5) 保存结构化执行记录（节点请求/响应/断言细节）
    环境优先级：接口自定义 > 场景自定义 > 全局环境
    """
    if run_mode == TestSceneExecution.RUN_MODE_SINGLE and not target_node:
        raise ValueError("单步执行必须指定 target_node")

    nodes_qs = scene.nodes.select_related("api_asset", "environment").filter(is_deleted=False).order_by("sort", "id")
    if run_mode == TestSceneExecution.RUN_MODE_SINGLE:
        nodes = [target_node]
    else:
        nodes = list(nodes_qs)

    # 预加载所有可能用到的 Environment，避免节点循环中 N+1 查询
    # 需要的 env_id：全局环境(runtime_config) + 每个节点的专属环境
    runtime_config = dict(runtime_config_override or scene.runtime_config or {})
    env_ids_needed = set()
    scene_env_id = runtime_config.get("environment_id")
    if scene_env_id:
        env_ids_needed.add(int(scene_env_id))
    for node in nodes:
        if node.environment_id:
            env_ids_needed.add(int(node.environment_id))
    preloaded_envs = {}
    if env_ids_needed:
        for env_obj in Environment.objects.filter(id__in=env_ids_needed):
            preloaded_envs[env_obj.id] = env_obj

    execution = TestSceneExecution.objects.create(
        scene=scene,
        target_node=target_node if run_mode == TestSceneExecution.RUN_MODE_SINGLE else None,
        run_mode=run_mode,
        status=TestSceneExecution.STATUS_RUNNING,
        created_by=operator,
    )

    try:
        return _execute_scene_body(scene, execution, nodes, run_mode, runtime_config_override, preloaded_envs, operator=operator)
    except Exception as exc:
        execution.status = TestSceneExecution.STATUS_FAILED
        execution.error_message = str(exc)
        execution.finished_at = timezone.now()
        execution.save(update_fields=["status", "error_message", "finished_at", "updated_at"])
        raise


def _execute_scene_body(scene, execution, nodes, run_mode, runtime_config_override, preloaded_envs=None, operator=None):
    """场景执行主逻辑，异常时由 execute_scene 捕获并更新 execution 状态。"""
    start_ts = time.time()
    variable_pool, env_obj = _build_initial_variable_pool(scene, runtime_config_override)
    if env_obj:
        execution.environment = env_obj
        execution.save(update_fields=["environment", "updated_at"])
    effective_runtime_config = dict(runtime_config_override or scene.runtime_config or {})
    scene_base_url_fallback = effective_runtime_config.get("base_url", "")
    if env_obj and env_obj.base_url:
        scene_base_url_fallback = env_obj.base_url.rstrip("/")

    node_results = []
    stop_after_failed = False
    for node in nodes:
        if stop_after_failed:
            node_results.append(
                {
                    "node_id": node.id,
                    "node_key": node.node_key,
                    "node_name": node.name,
                    "status": "skipped",
                    "reason": "前置节点失败且策略为stop",
                }
            )
            continue

        if not node.is_enabled:
            node_results.append(
                {
                    "node_id": node.id,
                    "node_key": node.node_key,
                    "node_name": node.name,
                    "status": "skipped",
                    "reason": "节点已禁用",
                    "assert_results": [],
                }
            )
            continue

        if not node.api_asset:
            status = "failed"
            reason = "节点未绑定API资产"
            node_results.append(
                {
                    "node_id": node.id,
                    "node_key": node.node_key,
                    "node_name": node.name,
                    "status": status,
                    "reason": reason,
                    "assert_results": [],
                }
            )
            if node.on_failed == TestSceneNode.ON_FAILED_STOP:
                stop_after_failed = True
            continue

        raw_headers = _flatten_kv_for_request(copy.deepcopy(node.request_headers or {}))
        _merged_params = _effective_request_params_for_node(node)
        raw_params_url = _flatten_kv_for_request(copy.deepcopy(_merged_params), exclude_file=True)
        raw_params_all = _flatten_kv_for_request(copy.deepcopy(_merged_params), exclude_file=False)
        raw_body = copy.deepcopy(node.request_body or {})
        # 处理可能的字符串类型：如果 request_body 是字符串，尝试解析为 JSON
        if isinstance(raw_body, str):
            try:
                raw_body = json.loads(raw_body)
            except (json.JSONDecodeError, ValueError):
                pass  # 保留原始字符串，交由后续处理
        if isinstance(raw_body, dict):
            raw_body = _flatten_kv_for_request(raw_body)
        raw_body = _unwrap_raw_body(raw_body)

        try:
            node_effective_url = node.request_url.strip() if node.request_url else ""
            if not node_effective_url:
                node_effective_url = node.api_asset.url if node.api_asset else ""
            rendered_url = _render_with_field_context("请求URL", node_effective_url, variable_pool)
            rendered_headers = _render_with_field_context("请求头", raw_headers, variable_pool)
            rendered_params_url = _render_with_field_context("请求参数", raw_params_url, variable_pool)
            rendered_params_all = _render_with_field_context("请求参数(含文件)", raw_params_all, variable_pool)
            rendered_body = _render_with_field_context("请求体", raw_body, variable_pool)
        except VariableResolveError as exc:
            node_results.append(
                {
                    "node_id": node.id,
                    "node_key": node.node_key,
                    "node_name": node.name,
                    "status": "failed",
                    "reason": str(exc),
                    "request": {
                        "method": node.effective_method or "",
                        "url": node_effective_url,
                        "headers": raw_headers,
                        "params": raw_params_url,
                        "body": raw_body,
                    },
                    "assert_results": [],
                }
            )
            if node.on_failed == TestSceneNode.ON_FAILED_STOP:
                stop_after_failed = True
            continue
        except Exception as exc:
            node_results.append(
                {
                    "node_id": node.id,
                    "node_key": node.node_key,
                    "node_name": node.name,
                    "status": "failed",
                    "reason": f"请求渲染异常: {exc}",
                    "assert_results": [],
                }
            )
            if node.on_failed == TestSceneNode.ON_FAILED_STOP:
                stop_after_failed = True
            continue

        # 1. 环境前置脚本（可选：API资产、节点前置脚本后续扩展）
        node_base_url, env_source = _resolve_node_base_url(node, scene, env_obj, effective_runtime_config, preloaded_envs)
        script_base_url = node_base_url or scene_base_url_fallback or effective_runtime_config.get("base_url", "")
        full_request_url = ""
        if script_base_url:
            path_part = (rendered_url or "").strip().lstrip("/")
            query_text = urlencode(rendered_params_url or {}, doseq=True)
            full_request_url = f"{script_base_url.rstrip('/')}/{path_part}" if path_part else script_base_url.rstrip("/")
            if query_text:
                full_request_url = f"{full_request_url}?{query_text}"
        content_type = (rendered_headers or {}).get("Content-Type") or (rendered_headers or {}).get("content-type") or "application/json"
        script_logs = []
        pre_request_script_input_snapshot = None

        effective_env = _get_effective_env_for_node(node, scene, env_obj, effective_runtime_config, preloaded_envs)
        if effective_env and getattr(effective_env, "pre_request_script", None):
            try:
                from test_manager.pre_request_script import execute_pre_request_script_via_subprocess, PreRequestScriptError
                script_timeout = getattr(effective_env, "script_timeout", 1000) or 1000
                env_vars_for_script = variables_for_runtime(effective_env.variables or {})
                sanitized = _sanitize_for_json(variable_pool)
                if isinstance(sanitized, dict):
                    for k, v in sanitized.items():
                        if k != "env" and v is not None:
                            env_vars_for_script[k] = v
                safe_headers = _sanitize_for_json(rendered_headers) if isinstance(rendered_headers, dict) else {}
                safe_params = _sanitize_for_json(rendered_params_all) if isinstance(rendered_params_all, dict) else {}
                if isinstance(rendered_body, dict):
                    safe_body = _sanitize_for_json(rendered_body)
                elif isinstance(rendered_body, str):
                    safe_body = rendered_body
                else:
                    safe_body = {}
                pre_request_script_input_snapshot = {
                    "request_url": full_request_url,
                    "request_method": str(node.effective_method or "GET").upper(),
                    "content_type": content_type,
                    "request_headers": copy.deepcopy(safe_headers) if isinstance(safe_headers, dict) else safe_headers,
                    "request_params": copy.deepcopy(safe_params) if isinstance(safe_params, dict) else safe_params,
                    "request_body": copy.deepcopy(safe_body) if isinstance(safe_body, (dict, list)) else safe_body,
                }
                new_env, new_headers, new_params, new_body, new_vars, script_logs = execute_pre_request_script_via_subprocess(
                    script=effective_env.pre_request_script,
                    env_vars=env_vars_for_script,
                    request_headers=safe_headers,
                    request_params=safe_params,
                    request_body=safe_body,
                    variables={},
                    request_url=full_request_url,
                    request_method=node.effective_method or "GET",
                    content_type=content_type,
                    timeout_ms=script_timeout,
                )
                variable_pool.update(new_env)
                variable_pool.update(new_vars)
                rendered_headers = new_headers or rendered_headers
                rendered_params_all = new_params or rendered_params_all
                rendered_params_url = {k: v for k, v in rendered_params_all.items() if not (isinstance(v, dict) and v.get("type") == "File")}
                rendered_body = new_body if new_body is not None else rendered_body
                rendered_body = _unwrap_raw_body(rendered_body)
            except PreRequestScriptError as exc:
                fail_item = {
                    "node_id": node.id,
                    "node_key": node.node_key,
                    "node_name": node.name,
                    "status": "failed",
                    "reason": f"前置脚本执行失败: {exc}",
                    "assert_results": [],
                }
                if pre_request_script_input_snapshot is not None:
                    fail_item["pre_request_script_input"] = pre_request_script_input_snapshot
                node_results.append(fail_item)
                if node.on_failed == TestSceneNode.ON_FAILED_STOP:
                    stop_after_failed = True
                continue

        # 2. 节点级前置脚本（在环境脚本之后执行，继承环境脚本已修改的 variable_pool）
        node_script = getattr(node, "pre_request_script", None) or ""
        node_script_timeout = getattr(node, "script_timeout", None)
        if node_script:
            try:
                from test_manager.pre_request_script import execute_pre_request_script_via_subprocess, PreRequestScriptError
                # 超时优先级：节点配置 > 环境配置 > 默认 1000ms
                if node_script_timeout is not None and node_script_timeout > 0:
                    effective_timeout = node_script_timeout
                elif effective_env and getattr(effective_env, "script_timeout", None):
                    effective_timeout = getattr(effective_env, "script_timeout", 1000) or 1000
                else:
                    effective_timeout = 1000
                env_vars_for_script = variables_for_runtime(effective_env.variables or {}) if effective_env else {}
                sanitized = _sanitize_for_json(variable_pool)
                if isinstance(sanitized, dict):
                    for k, v in sanitized.items():
                        if k != "env" and v is not None:
                            env_vars_for_script[k] = v
                safe_headers = _sanitize_for_json(rendered_headers) if isinstance(rendered_headers, dict) else {}
                safe_params = _sanitize_for_json(rendered_params_all) if isinstance(rendered_params_all, dict) else {}
                if isinstance(rendered_body, dict):
                    safe_body = _sanitize_for_json(rendered_body)
                elif isinstance(rendered_body, str):
                    safe_body = rendered_body
                else:
                    safe_body = {}
                new_env2, new_headers2, new_params2, new_body2, new_vars2, node_script_logs = execute_pre_request_script_via_subprocess(
                    script=node_script,
                    env_vars=env_vars_for_script,
                    request_headers=safe_headers,
                    request_params=safe_params,
                    request_body=safe_body,
                    variables={},
                    request_url=full_request_url,
                    request_method=str(node.effective_method or "GET").upper(),
                    content_type=content_type,
                    timeout_ms=effective_timeout,
                )
                variable_pool.update(new_env2)
                variable_pool.update(new_vars2)
                rendered_headers = new_headers2 or rendered_headers
                rendered_params_all = new_params2 or rendered_params_all
                rendered_params_url = {k: v for k, v in rendered_params_all.items() if not (isinstance(v, dict) and v.get("type") == "File")}
                rendered_body = new_body2 if new_body2 is not None else rendered_body
                rendered_body = _unwrap_raw_body(rendered_body)
                script_logs.extend(node_script_logs)
            except PreRequestScriptError as exc:
                # 节点脚本失败：记录警告但继续执行（不影响 HTTP 请求，遵循节点 on_failed 策略）
                import sys
                logger.warning("节点脚本执行警告: node=%s id=%s: %s", node.node_key, node.id, exc)
        elif node_script_timeout is not None and node_script_timeout > 0:
            # 节点未配置脚本但配置了超时，脚本日志标记为空（跳过）
            pass

        if not node_base_url and scene_base_url_fallback:
            node_base_url = scene_base_url_fallback
        if not node_base_url:
            node_base_url = effective_runtime_config.get("base_url", "")
        base_url, url_path = _split_base_and_path(rendered_url, node_base_url)
        proxy_env = ProxyEnvironment(base_url=base_url, variables={})
        proxy_case = _build_proxy_case(node, rendered_headers, rendered_params_url, rendered_params_all, rendered_body, url_path)
        try:
            run_result = execute_test_case(proxy_case, proxy_env, variables=variable_pool)
        except Exception as exc:
            run_result = {
                "status": "failed",
                "error_message": f"执行器异常: {exc}",
                "response_status_code": None,
                "response_headers": {},
                "response_body": None,
                "response_time": 0,
            }

        # proxy_case.request_url 已经通过 _merge_query_params_into_url 合并了 params（见第474行）
        # 因此直接使用即可，不需要重复添加 params
        full_url_with_params = proxy_case.request_url or (base_url or "")

        # ---- 文件下载处理 ----
        file_downloads = []
        if run_result.get("is_file_download") and run_result.get("raw_response_body_b64"):
            try:
                raw_bytes = base64.b64decode(run_result["raw_response_body_b64"])
                md5 = hashlib.md5(raw_bytes).hexdigest()
                resp_headers = run_result.get("response_headers") or {}
                content_type = resp_headers.get("Content-Type", "")
                filename = _extract_filename_from_headers(resp_headers, full_url_with_params)

                # 文件名无扩展名时根据 Content-Type 补充
                if "." not in filename and content_type:
                    _ext_map = {
                        "application/zip": ".zip",
                        "application/gzip": ".gz", "application/x-gzip": ".gz",
                        "application/x-tar": ".tar",
                        "application/x-bzip2": ".bz2",
                        "application/pdf": ".pdf",
                        "application/json": ".json",
                        "application/xml": ".xml", "text/xml": ".xml",
                        "text/csv": ".csv",
                        "text/plain": ".txt",
                        "text/html": ".html",
                        "text/markdown": ".md",
                        "image/jpeg": ".jpg", "image/pjpeg": ".jpg",
                        "image/png": ".png",
                        "image/gif": ".gif",
                        "image/webp": ".webp",
                        "image/svg+xml": ".svg",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
                        "application/vnd.ms-excel": ".xls",
                        "application/vnd.ms-powerpoint": ".ppt",
                        "application/octet-stream": ".bin",
                    }
                    base_ct = content_type.split(";")[0].strip().lower()
                    ext = _ext_map.get(base_ct, "")
                    if ext:
                        filename = filename + ext

                # 构建存储路径：downloads/YYYY/MM/exec{id}_node{node_id}_{uuid8}_{filename}
                date_path = datetime.now().strftime("%Y/%m")
                unique_tag = uuid.uuid4().hex[:8]
                storage_path = f"downloads/{date_path}/exec{execution.id}_node{node.id}_{unique_tag}_{filename}"

                saved_path = default_storage.save(storage_path, ContentFile(raw_bytes))
                file_size = len(raw_bytes)

                dl_record = SceneDownloadedFile.objects.create(
                    execution=execution,
                    node=node,
                    scene=scene,
                    project=scene.project,
                    filename=filename,
                    file_path=saved_path,
                    file_size=file_size,
                    md5=md5,
                    content_type=content_type,
                    created_by=operator,
                )

                download_file_info = {
                    "id": dl_record.id,
                    "filename": filename,
                    "file_size": file_size,
                    "md5": md5,
                }
                file_downloads.append(download_file_info)

                # 从 run_result 中移除原始字节，避免存入 DB JSONField 时过大
                run_result.pop("raw_response_body_b64", None)
                logger.info("下载文件已保存: node=%s filename=%s size=%d md5=%s",
                            node.node_key, filename, file_size, md5)
            except Exception as exc:
                logger.error("保存下载文件失败: node=%s id=%s error=%s", node.node_key, node.id, exc)

        node_context = {
            "status_code": run_result.get("response_status_code"),
            "response": run_result.get("response_body"),
            "headers": run_result.get("response_headers"),
            "request": {
                "method": proxy_case.request_method,
                "url": full_url_with_params,      # params 已在 _build_proxy_case 中合并到 URL
                "url_path": proxy_case.request_url,
                "headers": rendered_headers,
                # body 单独添加（有值时才添加），params 已合并到 URL 不再单独保存
                "body": proxy_case.request_body if proxy_case.request_body else None,
                "environment_source": env_source,
            },
        }
        if file_downloads:
            node_context["download_file"] = file_downloads[0]

        assert_passed, assert_details = evaluate_assertions(
            node.assert_rules, node_context, variable_pool,
            default_on_failed=node.on_failed,
        )
        node_status = run_result.get("status")
        run_ok = node_status == "passed"
        success = bool(run_ok and assert_passed)
        extracted = {}
        extract_error = ""
        if success:
            try:
                extracted = apply_extract_rules(node.extract_rules, node_context, variable_pool)
            except Exception as exc:
                success = False
                extract_error = f"提取变量失败: {exc}"

        # 节点执行完成后，将节点结果写回变量池，供后续节点按 node_{node_id}.response 取值。
        # 使用 node.id 作为 key，避免 node_key 同名时变量被覆盖（ISSUE-08）
        # 同时以 node_key 作为兼容别名，方便用户在断言/脚本中继续用 {{step_1.response}}
        node_var_key = f"node_{node.id}"
        variable_pool[node_var_key] = {
            "status": "passed" if success else "failed",
            "node_key": node.node_key,          # 兼容别名，供 {{node_key.xxx}} 引用
            "status_code": node_context["status_code"],
            "response": node_context["response"],
            "headers": node_context["headers"],
            "request": node_context["request"],
            "assert_results": assert_details,
            "extracted": extracted,
        }
        if file_downloads:
            variable_pool[node_var_key]["download_file"] = file_downloads[0]
        # 兼容：node_key 别名直接指向同一份数据（key 冲突时后者覆盖前者，DB 已有 unique 约束保证同一 scene 内不重名）
        if node.node_key in variable_pool and node.node_key not in ("env", "scene") and not callable(variable_pool.get(node.node_key)):
            logger.warning("节点 node_key '%s' 覆盖了已有的变量（可能为场景变量、环境变量或 debugtalk 函数）", node.node_key)
        variable_pool[node.node_key] = variable_pool[node_var_key]

        reason = ""
        if not run_ok:
            reason = run_result.get("error_message") or "接口调用失败"
        elif not assert_passed:
            reason = "断言失败"
        elif extract_error:
            reason = extract_error

        node_result_item = {
            "node_id": node.id,
            "node_key": node.node_key,
            "node_name": node.name,
            "status": "passed" if success else "failed",
            "reason": reason,
            "request": node_context["request"],
            "response": {
                "status_code": node_context["status_code"],
                "headers": node_context["headers"],
                "body": node_context["response"],
                "duration_ms": run_result.get("response_time"),
            },
            "assert_results": assert_details,
            "extracted": extracted,
        }
        if file_downloads:
            node_result_item["file_downloads"] = file_downloads
        if script_logs:
            node_result_item["script_logs"] = [{"level": l.get("level", "log"), "msg": l.get("msg", "")} for l in script_logs]
        if pre_request_script_input_snapshot is not None:
            node_result_item["pre_request_script_input"] = pre_request_script_input_snapshot
        node_results.append(node_result_item)
        if not success and node.on_failed == TestSceneNode.ON_FAILED_STOP:
            stop_after_failed = True

    total = len(node_results)
    passed = len([item for item in node_results if item.get("status") == "passed"])
    failed = len([item for item in node_results if item.get("status") == "failed"])
    skipped = len([item for item in node_results if item.get("status") == "skipped"])
    soft_nodes = sum(1 for item in node_results if _node_has_soft_assertion_failure(item.get("assert_results")))
    soft_assert_count = sum(
        _soft_assertion_failure_count(item.get("assert_results")) for item in node_results
    )
    # 硬通过节点：状态为 passed 且无软断言失败（ISSUE-08 计数澄清）
    hard_passed = sum(
        1 for item in node_results
        if item.get("status") == "passed" and not _node_has_soft_assertion_failure(item.get("assert_results"))
    )
    duration_ms = int((time.time() - start_ts) * 1000)

    execution.total_nodes = total
    execution.passed_nodes = passed
    execution.failed_nodes = failed
    execution.skipped_nodes = skipped
    execution.duration_ms = duration_ms
    execution.node_results = node_results
    summary = {
        "passed_nodes": passed,
        "hard_passed_nodes": hard_passed,     # 所有断言均通过（不含软断言失败）
        "failed_nodes": failed,
        "skipped_nodes": skipped,
        "soft_assertion_failed_nodes": soft_nodes,
        "soft_assertion_failure_count": soft_assert_count,
        "final_variables": _sanitize_for_json(variable_pool),
    }
    if env_obj:
        summary["environment"] = {"id": env_obj.id, "name": env_obj.name, "base_url": env_obj.base_url}
    execution.summary = summary
    execution.finished_at = timezone.now()
    if failed > 0:
        execution.status = TestSceneExecution.STATUS_FAILED
        first_failed = next((item for item in node_results if item.get("status") == "failed"), {})
        execution.error_message = first_failed.get("reason") or "场景存在失败节点"
    elif soft_nodes > 0:
        execution.status = TestSceneExecution.STATUS_PARTIAL_SUCCESS
        execution.error_message = "存在失败继续类断言未通过，场景计为部分成功"
    else:
        execution.status = TestSceneExecution.STATUS_SUCCESS
        execution.error_message = ""
    execution.save(
        update_fields=[
            "total_nodes",
            "passed_nodes",
            "failed_nodes",
            "skipped_nodes",
            "duration_ms",
            "node_results",
            "summary",
            "status",
            "finished_at",
            "error_message",
            "updated_at",
        ]
    )
    return execution
