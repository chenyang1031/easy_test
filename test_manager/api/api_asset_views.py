import difflib
import json
import os
import re
from copy import deepcopy
from datetime import timedelta
from math import ceil
from urllib.parse import urljoin

import requests
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from test_manager.models import ApiAsset, ApiGroup, ApiHistory, ApiProject, Project, TestCase, ApiPreset, ApiAssetDraft
from .api_asset_sync_utils import create_api_asset_change_records
from .apifox_environment_import import (
    apply_apifox_environment_import,
    empty_apifox_environment_import_stats,
    parse_apifox_environments_from_json,
)
from .serializers import (
    ApiAssetSerializer,
    ApiAssetLiteSerializer,
    ApiGroupListSerializer,
    ApiGroupSerializer,
    ApiHistorySerializer,
    ApiProjectSerializer,
    ApiPresetSerializer,
    ApiAssetDraftSerializer,
    _dict_params_to_array,
)

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


def _safe_json_loads(text, default=None):
    if default is None:
        default = {}
    try:
        return json.loads(text)
    except Exception:
        return default


def _asset_snapshot(asset):
    return {
        "id": asset.id,
        "project": asset.project_id,
        "group": asset.group_id,
        "name": asset.name,
        "method": asset.method,
        "url": asset.url,
        "interface_desc": asset.interface_desc or "",
        "request_headers": asset.request_headers or {},
        "request_params": asset.request_params or {},
        "request_body_format": asset.request_body_format,
        "request_body": asset.request_body or {},
        "response_schema": asset.response_schema or {},
        "error_code": asset.error_code or [],
        "auth_config": asset.auth_config or {},
        "status": asset.status,
        "source": asset.source,
        "external_id": asset.external_id,
        "required": asset.required,
        "param_type": asset.param_type,
        "sort": asset.sort,
        "param_status": asset.param_status,
    }


def _create_history(asset, operator, operation, content):
    ApiHistory.objects.create(asset=asset, operator=operator, operation=operation, content=content)


def _normalize_method(method):
    return str(method or "GET").upper()


def _normalize_body_format(raw_format):
    text = str(raw_format or "json").strip().lower()
    if text in ["form-data", "formdata", "multipart/form-data", "x-www-form-urlencoded", "urlencoded"]:
        return "form-data"
    return "json"


def _normalize_kv_payload(payload):
    if not payload:
        return {}
    if isinstance(payload, dict):
        return {str(key).strip(): value for key, value in payload.items() if str(key).strip()}
    if isinstance(payload, list):
        result = {}
        for item in payload:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or item.get("name") or "").strip()
            if not key:
                continue
            result[key] = item.get("value")
        return result
    return {}


def _get_request_params_keys(request_params) -> list:
    """兼容 dict 和 list 格式，提取所有参数 key"""
    if isinstance(request_params, dict):
        return list(request_params.keys())
    if isinstance(request_params, list):
        return [item.get("key", "") for item in request_params if isinstance(item, dict) and item.get("key")]
    return []


def _normalize_body_payload(payload, body_format):
    if body_format == "form-data":
        return _normalize_kv_payload(payload)
    return payload or {}


def _normalize_compare_value(value):
    if isinstance(value, dict):
        return {str(k): _normalize_compare_value(v) for k, v in sorted(value.items(), key=lambda x: str(x[0]))}
    if isinstance(value, list):
        return [_normalize_compare_value(item) for item in value]
    if value is None:
        return {}
    return value


def _compose_after_snapshot(asset, validated_data):
    after = deepcopy(_asset_snapshot(asset))
    relation_fields = {"project", "group"}
    for key, value in validated_data.items():
        if key in relation_fields:
            after[key] = value.id if value else None
        else:
            after[key] = value
    return after


def _cleanup_expired_asset_drafts():
    ApiAssetDraft.objects.filter(expires_at__lte=timezone.now()).delete()


def _normalize_param_rows(payload, asset_obj):
    payload = payload or {}
    if not isinstance(payload, dict):
        return {}

    normalized = {}
    default_required = bool(getattr(asset_obj, "required", False))
    default_type = str(getattr(asset_obj, "param_type", "string") or "string")
    default_status = str(getattr(asset_obj, "param_status", ApiAsset.PARAM_STATUS_ENABLED) or ApiAsset.PARAM_STATUS_ENABLED)

    for idx, (key, value) in enumerate(payload.items()):
        row_key = str(key).strip()
        if not row_key:
            continue
        row_id = row_key
        row_value = value
        row_required = default_required
        row_type = default_type
        row_sort = idx
        row_status = default_status
        row_desc = ""
        if isinstance(value, dict) and "value" in value:
            row_value = value.get("value")
            row_required = bool(value.get("required", row_required))
            row_type = str(value.get("type", row_type) or row_type)
            row_sort = int(value.get("sort", row_sort) or row_sort)
            row_status = str(value.get("status", row_status) or row_status)
            row_desc = str(value.get("description", "") or "")
            row_id = str(value.get("_row_id", row_key) or row_key)

        if row_status not in {ApiAsset.PARAM_STATUS_ENABLED, ApiAsset.PARAM_STATUS_DISABLED}:
            row_status = ApiAsset.PARAM_STATUS_ENABLED

        normalized[row_key] = {
            "_row_id": row_id,
            "value": row_value,
            "required": row_required,
            "type": row_type,
            "sort": row_sort,
            "status": row_status,
            "description": row_desc,
        }
    return normalized


def _normalize_item(raw_item, source):
    body_format = _normalize_body_format(raw_item.get("request_body_format"))
    return {
        "name": raw_item.get("name") or f"{_normalize_method(raw_item.get('method'))} {raw_item.get('url', '')}",
        "method": _normalize_method(raw_item.get("method")),
        "url": str(raw_item.get("url") or "").strip(),
        "request_headers": _normalize_kv_payload(raw_item.get("request_headers") or raw_item.get("headers")),
        "request_params": _normalize_kv_payload(raw_item.get("request_params") or raw_item.get("query_params")),
        "request_body_format": body_format,
        "request_body": _normalize_body_payload(raw_item.get("request_body") or raw_item.get("body"), body_format),
        "response_schema": raw_item.get("response_schema") or {},
        "auth_config": raw_item.get("auth_config") or {},
        "source": source,
        "external_id": str(raw_item.get("external_id") or ""),
        "group_path": raw_item.get("group_path") or [],
    }


def _read_upload_data(upload_file):
    raw = upload_file.read()
    text = raw.decode("utf-8", errors="ignore")
    data = _safe_json_loads(text, default=None)
    if data is not None:
        return data
    if yaml:
        try:
            return yaml.safe_load(text)
        except Exception:
            return None
    return None


def _fetch_and_parse_from_url(url):
    """
    从在线链接拉取并解析 API 规范数据。
    支持 OpenAPI/Swagger v2/v3。
    返回 (data, error_message)，成功时 error_message 为 None。
    """
    url = str(url or "").strip()
    if not url:
        return None, "请输入有效的链接地址"
    if not re.match(r"^https?://", url, re.I):
        return None, "链接必须以 http:// 或 https:// 开头"
    try:
        resp = requests.get(url, timeout=30, headers={"Accept": "application/json, application/yaml, text/yaml"})
    except requests.exceptions.Timeout:
        return None, "链接访问超时，请检查网络或稍后重试"
    except requests.exceptions.ConnectionError:
        return None, "链接无法访问，请检查地址或网络连接"
    except requests.exceptions.RequestException as e:
        return None, f"链接访问失败：{str(e)[:100]}"
    if resp.status_code == 403:
        return None, "权限不足，无法访问该链接"
    if resp.status_code == 404:
        return None, "链接不存在或已失效"
    if resp.status_code >= 400:
        return None, f"链接返回错误 {resp.status_code}，请检查地址或网络"
    text = resp.text
    if not text or not text.strip():
        return None, "链接返回内容为空"
    data = _safe_json_loads(text, default=None)
    if data is not None:
        return data, None
    if yaml:
        try:
            data = yaml.safe_load(text)
            if data:
                return data, None
        except Exception:
            pass
    return None, "格式不支持，请确认链接返回的是有效的 JSON 或 YAML 格式"


def _parse_postman_collection(data):
    items = []

    def parse_url(url_obj):
        if isinstance(url_obj, str):
            return url_obj, {}
        if isinstance(url_obj, dict):
            raw = url_obj.get("raw") or ""
            query_items = url_obj.get("query") or []
            query_params = {}
            for q in query_items:
                if isinstance(q, dict):
                    query_params[str(q.get("key", ""))] = q.get("value")
            return raw, query_params
        return "", {}

    def parse_headers(header_items):
        headers = {}
        for h in header_items or []:
            if isinstance(h, dict):
                key = str(h.get("key", "")).strip()
                if key:
                    headers[key] = h.get("value")
        return headers

    def walk(node_items, path):
        for node in node_items or []:
            if not isinstance(node, dict):
                continue
            child_items = node.get("item")
            if isinstance(child_items, list) and "request" not in node:
                walk(child_items, path + [node.get("name") or "未命名分组"])
                continue

            request = node.get("request") or {}
            method = request.get("method") or "GET"
            url, query_params = parse_url(request.get("url"))
            headers = parse_headers(request.get("header"))
            body = {}
            body_format = "json"
            req_body = request.get("body") or {}
            if req_body.get("raw"):
                body = _safe_json_loads(req_body.get("raw"), default={"raw": req_body.get("raw")})
            elif req_body.get("urlencoded"):
                body = {str(i.get("key")): i.get("value") for i in req_body.get("urlencoded", []) if isinstance(i, dict)}
                body_format = "form-data"
            elif req_body.get("formdata"):
                body = {str(i.get("key")): i.get("value") for i in req_body.get("formdata", []) if isinstance(i, dict)}
                body_format = "form-data"

            response_schema = {}
            responses = node.get("response") or []
            if responses:
                first = responses[0]
                response_schema = _safe_json_loads(first.get("body") or "", default={})

            items.append(
                _normalize_item(
                    {
                        "name": node.get("name"),
                        "method": method,
                        "url": url,
                        "request_headers": headers,
                        "request_params": query_params,
                        "request_body_format": body_format,
                        "request_body": body,
                        "response_schema": response_schema,
                        "auth_config": request.get("auth") or {},
                        "external_id": node.get("id") or "",
                        "group_path": path,
                    },
                    source=ApiAsset.SOURCE_POSTMAN,
                )
            )

    walk(data.get("item") or [], [])
    return items


def _is_openapi_or_swagger(data):
    """判断数据是否为 OpenAPI/Swagger 规范（含 v1/v2/v3）。"""
    if not isinstance(data, dict):
        return False
    if "openapi" in data or "swagger" in data:
        return True
    swagger_ver = str(data.get("swaggerVersion") or "").strip()
    return swagger_ver in ("1.0", "1.1", "1.2")


def _is_swagger_1x(data):
    """判断是否为 Swagger 1.0/1.1/1.2 规范。"""
    if not isinstance(data, dict):
        return False
    swagger_ver = str(data.get("swaggerVersion") or "").strip()
    return swagger_ver in ("1.0", "1.1", "1.2")


def _parse_swagger_1x(data):
    """
    解析 Swagger 1.0/1.1/1.2 规范。
    支持 API Declaration（apis 含 operations）及 Resource Listing（需按 path 拉取子文档）。
    """
    items = []
    apis = data.get("apis") or []
    base_path = str(data.get("basePath") or "").rstrip("/")

    for api_item in apis:
        if not isinstance(api_item, dict):
            continue
        path_prefix = str(api_item.get("path") or "").strip().lstrip("/")
        operations = api_item.get("operations") or []

        for op in operations:
            if not isinstance(op, dict):
                continue
            method = _normalize_method(op.get("method") or op.get("httpMethod"))
            if method not in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"):
                continue

            op_path = str(op.get("path") or path_prefix or "").strip().lstrip("/")
            if not op_path:
                op_path = path_prefix
            full_path = "/" + (base_path.strip("/") + "/" + op_path if base_path else op_path).strip("/")
            if full_path == "/":
                full_path = "/" + (path_prefix or "unknown")

            headers = {}
            query_params = {}
            for p in op.get("parameters") or []:
                if not isinstance(p, dict):
                    continue
                p_name = str(p.get("name") or "")
                p_in = str(p.get("paramType") or p.get("in") or "query").lower()
                if p_in == "path":
                    continue
                if p_in == "header":
                    headers[p_name] = ""
                else:
                    query_params[p_name] = ""

            items.append(
                _normalize_item(
                    {
                        "name": op.get("summary") or op.get("nickname") or op.get("operationId") or f"{method} {full_path}",
                        "method": method,
                        "url": full_path,
                        "request_headers": headers,
                        "request_params": query_params,
                        "request_body_format": "json",
                        "request_body": {},
                        "response_schema": {},
                        "auth_config": {},
                        "external_id": op.get("nickname") or op.get("operationId") or "",
                        "group_path": [path_prefix] if path_prefix else [],
                    },
                    source=ApiAsset.SOURCE_OPENAPI,
                )
            )
    return items


def _fetch_swagger_1x_resource_listing(base_url, data):
    """
    Swagger 1.x Resource Listing：apis 无 operations，需按 path 拉取子文档并合并。
    """
    all_items = []
    apis = data.get("apis") or []
    for api_item in apis:
        if not isinstance(api_item, dict):
            continue
        path = api_item.get("path")
        if not path:
            continue
        sub_url = urljoin(base_url, path)
        try:
            resp = requests.get(sub_url, timeout=15, headers={"Accept": "application/json"})
            if resp.status_code != 200:
                continue
            sub_data = _safe_json_loads(resp.text, default=None)
            if sub_data and _is_swagger_1x(sub_data):
                all_items.extend(_parse_swagger_1x(sub_data))
        except Exception:
            continue
    return all_items


def _resolve_ref(data, ref_path):
    """
    解析 $ref，如 "#/definitions/yhy.response.respType" 或 "#/components/schemas/XXX"。
    """
    if not ref_path or not ref_path.startswith("#/"):
        return None
    parts = ref_path[2:].split("/")
    obj = data
    for part in parts:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(part)
    return obj


def _resolve_schema_refs(data, schema, definitions=None):
    """解析 schema 中的 $ref，返回展开后的 schema。"""
    if not isinstance(schema, dict):
        return schema
    definitions = definitions or data.get("definitions") or data.get("components", {}).get("schemas") or {}
    ref_val = schema.get("$ref")
    if ref_val:
        resolved = _resolve_ref(data, ref_val)
        if resolved is not None:
            return _resolve_schema_refs(data, resolved, definitions)
        ref_name = ref_val.split("/")[-1] if ref_val else ""
        if ref_name in definitions:
            return _resolve_schema_refs(data, definitions[ref_name], definitions)
    return schema


def _parse_openapi(data):
    items = []
    paths = data.get("paths") or {}
    base_path = str(data.get("basePath") or "").rstrip("/")
    definitions = data.get("definitions") or data.get("components", {}).get("schemas") or {}

    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        full_path = (base_path + path) if base_path else path
        for method, detail in methods.items():
            method_upper = _normalize_method(method)
            if method_upper not in ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]:
                continue
            if not isinstance(detail, dict):
                continue

            headers = {}
            query_params = {}
            body_schema = {}
            body_format = "json"
            consumes = detail.get("consumes") or []

            for p in detail.get("parameters") or []:
                if not isinstance(p, dict):
                    continue
                p_name = str(p.get("name") or "")
                p_in = str(p.get("in") or "").lower()
                if p_in == "header":
                    headers[p_name] = ""
                elif p_in == "query":
                    query_params[p_name] = ""
                elif p_in in ("formdata", "formData"):
                    body_format = "form-data"
                    body_schema[p_name] = {
                        "value": "",
                        "required": bool(p.get("required", False)),
                        "description": str(p.get("description") or ""),
                        "type": str(p.get("type") or "string"),
                    }
                elif p_in == "body":
                    body_format = "json"
                    body_schema = p.get("schema") or {}
                    if isinstance(body_schema, dict) and body_schema.get("$ref"):
                        body_schema = _resolve_schema_refs(data, body_schema, definitions) or {}

            if not body_schema and ("multipart/form-data" in consumes or "application/x-www-form-urlencoded" in consumes):
                body_format = "form-data"

            req_body = detail.get("requestBody") or {}
            content = req_body.get("content") or {}
            if not body_schema:
                json_content = content.get("application/json") or {}
                if isinstance(json_content, dict):
                    body_schema = json_content.get("schema") or {}
                    if body_schema.get("$ref"):
                        body_schema = _resolve_schema_refs(data, body_schema, definitions) or {}
                elif content.get("multipart/form-data"):
                    body_schema = content.get("multipart/form-data", {}).get("schema") or {}
                    body_format = "form-data"

            response_schema = {}
            responses = detail.get("responses") or {}
            resp_200 = responses.get("200") or responses.get("default") or {}
            if isinstance(resp_200, dict):
                resp_content = resp_200.get("content") or {}
                resp_json = resp_content.get("application/json") or {}
                raw_schema = resp_json.get("schema") if resp_json else resp_200.get("schema")
                if isinstance(raw_schema, dict):
                    response_schema = _resolve_schema_refs(data, raw_schema, definitions) or {}

            tags = detail.get("tags") or []
            group_path = [str(tags[0])] if tags else []

            items.append(
                _normalize_item(
                    {
                        "name": detail.get("summary") or detail.get("operationId") or f"{method_upper} {full_path}",
                        "method": method_upper,
                        "url": full_path,
                        "request_headers": headers,
                        "request_params": query_params,
                        "request_body_format": body_format,
                        "request_body": body_schema,
                        "response_schema": response_schema,
                        "auth_config": {},
                        "external_id": detail.get("operationId") or "",
                        "group_path": group_path,
                    },
                    source=ApiAsset.SOURCE_OPENAPI,
                )
            )
    return items


def _apifox_param_list_to_dict(param_list):
    """将 Apifox 参数数组 [{name, value, example, sampleValue, ...}] 转为 {name: value}。"""
    out = {}
    if not isinstance(param_list, list):
        return out
    for h in param_list:
        if not isinstance(h, dict):
            continue
        key = str(h.get("name") or h.get("key") or "").strip()
        if not key:
            continue
        val = h.get("value")
        if val is None:
            val = h.get("example")
        if val is None:
            val = h.get("sampleValue")
        out[key] = val
    return out


def _apifox_split_parameters(parameters):
    """解析 Apifox HTTP 接口 parameters.header / query / path。"""
    if not isinstance(parameters, dict):
        return {}, {}
    headers = _apifox_param_list_to_dict(parameters.get("header") or [])
    query_params = {}
    for key in ("query", "path"):
        query_params.update(_apifox_param_list_to_dict(parameters.get(key) or []))
    return headers, query_params


def _apifox_try_parse_json(text):
    """解析 Apifox 示例等 JSON 字符串，失败返回 None。"""
    if text is None:
        return None
    if isinstance(text, (dict, list)):
        return text
    if not isinstance(text, str) or not text.strip():
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def _apifox_request_body_examples_to_payload(req_body):
    """
    从 Apifox requestBody.examples（设计-示例）解析可 JSON 反序列化的请求体对象。
    与响应侧 responseExamples 一致，便于场景编排使用真实数据结构而非仅 Schema。
    """
    if not isinstance(req_body, dict):
        return None
    examples = req_body.get("examples")
    if not isinstance(examples, list) or not examples:
        return None

    def _iter_example_fields(ex):
        if not isinstance(ex, dict):
            return
        for key in ("value", "data", "raw"):
            val = ex.get(key)
            if val is not None:
                yield val

    json_first = []
    rest = []
    for ex in examples:
        if not isinstance(ex, dict):
            continue
        mt = str(ex.get("mediaType") or "").lower()
        if "json" in mt or not mt.strip():
            json_first.append(ex)
        else:
            rest.append(ex)

    for bucket in (json_first, rest):
        for ex in bucket:
            for field in _iter_example_fields(ex):
                parsed = _apifox_try_parse_json(field)
                if parsed is not None:
                    return parsed
    return None


def _apifox_extract_body_format_and_payload(req_body):
    """Apifox requestBody -> (原始格式字符串, 供 _normalize_body_payload 使用的负载)。"""
    if not isinstance(req_body, dict):
        return "json", {}
    type_str = str(req_body.get("type") or "").lower()
    if any(x in type_str for x in ("multipart", "form-data", "urlencoded", "x-www-form-urlencoded")):
        params = req_body.get("parameters") or req_body.get("urlencoded") or []
        return "form-data", _apifox_param_list_to_dict(params)

    # JSON 体：优先「设计 - 示例」；否则 JSON Schema（新版导出常见：parameters 为空数组但仍为 JSON 体）
    from_examples = _apifox_request_body_examples_to_payload(req_body)
    if from_examples is not None:
        return "json", from_examples

    json_schema = req_body.get("jsonSchema")
    if json_schema:
        return "json", json_schema

    if req_body.get("parameters"):
        return "form-data", _apifox_param_list_to_dict(req_body.get("parameters") or [])
    return "json", req_body


def _apifox_schema_from_single_response(resp):
    """从单条响应对象中提取 Schema（兼容 jsonSchema / schema / itemSchema）。"""
    if not isinstance(resp, dict):
        return None
    for key in ("jsonSchema", "schema"):
        val = resp.get(key)
        if isinstance(val, dict) and val:
            return val
    item = resp.get("itemSchema")
    if isinstance(item, dict) and item:
        return item
    return None


def _apifox_response_sort_key(resp):
    """优先 2xx，其次状态码数值。"""
    if not isinstance(resp, dict):
        return (99, 9999)
    code = resp.get("code")
    try:
        c = int(code) if code is not None and str(code).strip() != "" else 9999
    except (TypeError, ValueError):
        c = 9999
    if 200 <= c < 300:
        return (0, c)
    if 100 <= c < 600:
        return (1, c)
    return (2, c)


def _apifox_pick_example_for_response(response_id, examples):
    """按 responseId 匹配 responseExamples[].data。"""
    if response_id is None or not examples:
        return None
    rid = str(response_id)
    for ex in examples:
        if not isinstance(ex, dict):
            continue
        if str(ex.get("responseId") or "") != rid:
            continue
        parsed = _apifox_try_parse_json(ex.get("data"))
        if parsed is not None:
            return parsed
    return None


def _apifox_response_examples_to_body(api_obj):
    """
    从 Apifox responseExamples 解析成功响应体 JSON，用于写入 API 资产的 response_schema，
    与场景节点「响应预览 / 复制路径」一致（真实 JSON 形状，而非 JSON Schema）。
    返回 dict / list；无法解析时返回 None。
    """
    if not isinstance(api_obj, dict):
        return None
    responses = api_obj.get("responses") or []
    response_examples = api_obj.get("responseExamples") or []
    if not response_examples:
        return None

    sorted_responses = sorted(
        [r for r in responses if isinstance(r, dict)],
        key=_apifox_response_sort_key,
    )
    # 优先：与优先 2xx 响应对应的示例（responseId 对齐）
    for r in sorted_responses:
        rid = r.get("id")
        parsed = _apifox_pick_example_for_response(rid, response_examples)
        if parsed is not None:
            return _apifox_normalize_example_root(parsed)

    # 其次：任一可解析示例（常见为「成功示例」）
    for ex in response_examples:
        if not isinstance(ex, dict):
            continue
        parsed = _apifox_try_parse_json(ex.get("data"))
        if parsed is not None:
            return _apifox_normalize_example_root(parsed)

    return None


def _apifox_normalize_example_root(parsed):
    """response_schema 存 dict/list；标量包一层便于表单与预览。"""
    if isinstance(parsed, (dict, list)):
        return parsed
    if parsed is None:
        return None
    return {"example": parsed}


def _apifox_extract_response_schema(api_obj):
    """
    映射为 API 资产的 response_schema（「响应 Schema (JSON)」字段）。

    优先使用 Apifox responseExamples 中的成功示例（解析为真实响应 JSON），便于后续节点配置路径；
    无可用示例时回退到 responses 中的 JSON Schema。
    兼容：api 节点、以及含 responses/responseExamples 的扁平请求节点。
    """
    if not isinstance(api_obj, dict):
        return {}

    body = _apifox_response_examples_to_body(api_obj)
    if body is not None:
        return body

    responses = api_obj.get("responses") or []
    sorted_responses = sorted(
        [r for r in responses if isinstance(r, dict)],
        key=_apifox_response_sort_key,
    )
    for r in sorted_responses:
        sch = _apifox_schema_from_single_response(r)
        if sch:
            return sch

    return {}


def _parse_apifox(data):
    items = []
    # 与业务无关的顶层目录名，不写入 group_path
    skip_folder_names = frozenset({"根目录", "Root", "root", "默认目录"})

    def _folder_path_append(path, name):
        label = (name or "").strip()
        if not label or label in skip_folder_names:
            return path
        return path + [label]

    def append_from_api_object(api_obj, path, display_name):
        if not isinstance(api_obj, dict):
            return
        method = api_obj.get("method") or api_obj.get("httpMethod")
        url = api_obj.get("path") or api_obj.get("url")
        if not method or not url:
            return
        parameters = api_obj.get("parameters") or {}
        headers, query_params = _apifox_split_parameters(parameters)
        body_fmt_raw, body_payload = _apifox_extract_body_format_and_payload(api_obj.get("requestBody") or {})
        response_schema = _apifox_extract_response_schema(api_obj)
        name = display_name or api_obj.get("name") or api_obj.get("summary") or ""
        items.append(
            _normalize_item(
                {
                    "name": name,
                    "method": method,
                    "url": url,
                    "request_headers": headers,
                    "request_params": query_params,
                    "request_body_format": body_fmt_raw,
                    "request_body": body_payload,
                    "response_schema": response_schema,
                    "auth_config": api_obj.get("auth") or {},
                    "external_id": str(api_obj.get("id") or ""),
                    "group_path": path,
                },
                source=ApiAsset.SOURCE_APIFOX,
            )
        )

    def collect(nodes, path):
        for node in nodes or []:
            if not isinstance(node, dict):
                continue

            # 新版 Apifox 项目导出：HTTP 接口在 node.api 下
            api_obj = node.get("api")
            if isinstance(api_obj, dict):
                method = api_obj.get("method") or api_obj.get("httpMethod")
                url = api_obj.get("path") or api_obj.get("url")
                if method and url:
                    append_from_api_object(api_obj, path, node.get("name"))
                    continue

            method = node.get("method") or node.get("httpMethod")
            url = node.get("url") or node.get("path")
            if method and url:
                headers = {}
                for h in node.get("headers") or []:
                    if isinstance(h, dict):
                        key = str(h.get("name") or h.get("key") or "")
                        if key:
                            headers[key] = h.get("value")

                query_params = {}
                for q in node.get("queryParameters") or node.get("query") or []:
                    if isinstance(q, dict):
                        key = str(q.get("name") or q.get("key") or "")
                        if key:
                            query_params[key] = q.get("value")

                params_block = node.get("parameters") or {}
                if isinstance(params_block, dict):
                    headers.update(_apifox_param_list_to_dict(params_block.get("header") or []))
                    for k in ("query", "path"):
                        query_params.update(_apifox_param_list_to_dict(params_block.get(k) or []))

                req_body = node.get("requestBody") or {}
                body_fmt_raw, body_payload = _apifox_extract_body_format_and_payload(req_body)

                response_schema = _apifox_extract_response_schema(node)
                if not response_schema:
                    legacy = node.get("response") or node.get("responseSchema")
                    if isinstance(legacy, dict) and legacy:
                        response_schema = legacy

                items.append(
                    _normalize_item(
                        {
                            "name": node.get("name"),
                            "method": method,
                            "url": url,
                            "request_headers": headers,
                            "request_params": query_params,
                            "request_body_format": body_fmt_raw,
                            "request_body": body_payload,
                            "response_schema": response_schema,
                            "auth_config": node.get("auth") or {},
                            "external_id": str(node.get("id") or ""),
                            "group_path": path,
                        },
                        source=ApiAsset.SOURCE_APIFOX,
                    )
                )
                continue

            new_path = _folder_path_append(path, node.get("name"))
            # 新版用 items 嵌套子目录/接口；旧版用 children
            for child_key in ("children", "items"):
                child_nodes = node.get(child_key)
                if child_nodes:
                    collect(child_nodes, new_path)

    roots = []
    roots.extend(data.get("apiCollection") or [])
    roots.extend(data.get("requestCollection") or [])
    roots.extend(data.get("folders") or [])
    roots.extend(data.get("items") or [])
    if isinstance(roots, list) and roots:
        collect(roots, [])
    elif isinstance(data, dict):
        collect([data], [])
    return items


def _resolve_apifox_environment_payload_for_confirm(request):
    """
    确认导入时解析 Apifox 环境载荷：优先使用请求体中的 apifox_environment_import（与预览一致）；
    若无则尝试从同时上传的 apifox 源文件中解析（兼容未改前端的脚本或旧客户端）。
    """
    body = request.data.get("apifox_environment_import")
    if isinstance(body, dict) and "environments" in body:
        return body
    upload = request.FILES.get("file")
    if upload and str(request.data.get("file_type") or "").lower() == "apifox":
        data = _read_upload_data(upload)
        if isinstance(data, dict):
            return parse_apifox_environments_from_json(data)
    return None


def _should_attempt_apifox_environment_import(request, items):
    """
    仅在 Apifox 导入链路中尝试写入环境变量，避免 Postman/OpenAPI 确认导入时出现误导性的 skip 原因。
    """
    if request.data.get("apifox_environment_import") is not None:
        return True
    if str(request.data.get("file_type") or "").lower() == "apifox":
        return True
    for raw in items or []:
        if isinstance(raw, dict) and raw.get("source") == ApiAsset.SOURCE_APIFOX:
            return True
    return False


class ApiProjectViewSet(viewsets.ModelViewSet):
    queryset = ApiProject.objects.all()
    serializer_class = ApiProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = ApiProject.objects.select_related("platform_project", "created_by").all().order_by("-created_at")
        q = self.request.query_params.get("q")
        if q:
            queryset = queryset.filter(Q(name__icontains=q) | Q(description__icontains=q))
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["post"], url_path="resolve-platform-project")
    def resolve_platform_project(self, request):
        platform_project_id = request.data.get("platform_project_id")
        if not platform_project_id:
            return Response({"detail": "platform_project_id不能为空"}, status=status.HTTP_400_BAD_REQUEST)

        platform_project = get_object_or_404(Project, id=platform_project_id)
        api_project, _ = ApiProject.objects.get_or_create(
            platform_project=platform_project,
            defaults={
                "name": platform_project.name,
                "description": platform_project.description or "",
                "created_by": request.user,
            },
        )
        if not api_project.name:
            api_project.name = platform_project.name
            api_project.description = platform_project.description or ""
            api_project.save(update_fields=["name", "description", "updated_at"])

        return Response({"api_project_id": api_project.id, "platform_project_id": platform_project.id, "name": api_project.name})

    @action(detail=True, methods=["get"])
    def stats(self, request, pk=None):
        project = self.get_object()
        total = project.assets.filter(is_deleted=False).count()
        status_dist = project.assets.filter(is_deleted=False).values("status").annotate(count=Count("id")).order_by("status")
        group_count = project.groups.count()
        # 空分组：该分组及所有子分组下均无接口
        empty_count = 0
        for g in project.groups.all():
            gids = _get_group_and_descendant_ids(g)
            if not ApiAsset.objects.filter(group_id__in=gids, is_deleted=False).exists():
                empty_count += 1
        return Response(
            {
                "project_id": project.id,
                "total_assets": total,
                "group_count": group_count,
                "empty_group_count": empty_count,
                "status_distribution": list(status_dist),
            }
        )


def _get_group_and_descendant_ids(group):
    """获取分组及其所有子分组的 ID 列表。"""
    ids = [group.id]
    children = ApiGroup.objects.filter(parent_id=group.id).values_list("id", flat=True)
    for cid in children:
        child = ApiGroup.objects.filter(id=cid).first()
        if child:
            ids.extend(_get_group_and_descendant_ids(child))
    return ids


class ApiGroupPagination(PageNumberPagination):
    """API 分组列表分页，支持大 page_size 以获取完整树结构"""
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 2000


class ApiGroupViewSet(viewsets.ModelViewSet):
    queryset = ApiGroup.objects.select_related("project", "parent").all()
    serializer_class = ApiGroupSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ApiGroupPagination

    def get_serializer_class(self):
        if getattr(self, "action", None) == "list":
            return ApiGroupListSerializer
        return ApiGroupSerializer

    def get_queryset(self):
        queryset = ApiGroup.objects.select_related("project", "parent").all()
        project_id = self.request.query_params.get("project")
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        queryset = queryset.order_by("sort_order", "id")
        # list：一次 annotate 替代每个节点上的 COUNT 子查询；扁平序列化替代递归 children
        if getattr(self, "action", None) == "list":
            queryset = queryset.annotate(
                asset_count=Count("assets", filter=Q(assets__is_deleted=False)),
                child_count=Count("children"),
            )
        return queryset

    def destroy(self, request, *args, **kwargs):
        group = self.get_object()
        group_ids = _get_group_and_descendant_ids(group)
        asset_count = ApiAsset.objects.filter(group_id__in=group_ids, is_deleted=False).count()
        if asset_count > 0:
            return Response(
                {
                    "detail": f"该分组或子分组下存在 {asset_count} 个接口，请先移动或删除接口后再删除分组，或使用「删除并迁移至根分组」",
                    "asset_count": asset_count,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="delete-with-migrate")
    def delete_with_migrate(self, request, pk=None):
        """删除分组，可选将子分组和接口迁移至根分组。"""
        group = self.get_object()
        migrate_to_root = request.data.get("migrate_to_root", False)
        group_ids = _get_group_and_descendant_ids(group)
        asset_count = ApiAsset.objects.filter(group_id__in=group_ids, is_deleted=False).count()

        if asset_count > 0 and not migrate_to_root:
            return Response(
                {
                    "detail": f"该分组或子分组下存在 {asset_count} 个接口，请选择「迁移至根分组」或先在 API 资产管理中移动接口",
                    "asset_count": asset_count,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if migrate_to_root:
            ApiAsset.objects.filter(group_id__in=group_ids, is_deleted=False).update(group=None)
            ApiGroup.objects.filter(parent_id=group.id).update(parent=None)

        group.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ApiAssetViewSet(viewsets.ModelViewSet):
    queryset = ApiAsset.objects.select_related("project", "group", "created_by").filter(is_deleted=False)
    serializer_class = ApiAssetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = ApiAsset.objects.select_related("project", "group", "created_by").filter(is_deleted=False)
        params = self.request.query_params
        project_id = params.get("project")
        group_param = params.get("group_id") or params.get("group")
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        if group_param:
            queryset = queryset.filter(group_id=group_param)
        method = params.get("method")
        if method:
            queryset = queryset.filter(method=_normalize_method(method))
        status_value = params.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value)
        source_value = params.get("source")
        if source_value:
            queryset = queryset.filter(source=source_value)
        search = params.get("search") or params.get("q")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(url__icontains=search) | Q(interface_desc__icontains=search)
            )
        return queryset.order_by("-created_at", "-id")

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        try:
            page = int(request.query_params.get("page", 1))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(request.query_params.get("page_size", 20))
        except (TypeError, ValueError):
            page_size = 20

        page = max(page, 1)
        page_size = min(max(page_size, 1), 200)
        total = queryset.count()
        total_pages = max(1, ceil(total / page_size)) if total else 1
        if page > total_pages:
            page = total_pages

        offset = (page - 1) * page_size
        items = queryset[offset: offset + page_size]
        serializer = self.get_serializer(items, many=True)
        return Response(
            {
                "count": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "results": serializer.data,
            }
        )

    @action(detail=False, methods=["get"], url_path="lite")
    def lite(self, request):
        """
        轻量列表接口：仅返回 API 资产 id/name，避免场景编排页面初始化加载大 JSON 配置。
        """
        project_id = request.query_params.get("project")
        if not project_id:
            return Response({"detail": "project不能为空"}, status=status.HTTP_400_BAD_REQUEST)
        queryset = ApiAsset.objects.filter(project_id=project_id, is_deleted=False).only("id", "name").order_by("-created_at", "-id")
        serializer = ApiAssetLiteSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="upload")
    def upload(self, request):
        """
        文件上传接口：接收 file 并存储到默认存储后端。
        返回 file_path、file_name、file_url，供场景编排节点参数中的 file 类型使用。
        """
        upload_file = request.FILES.get("file")
        if not upload_file:
            return Response({"success": False, "detail": "未接收到上传文件"}, status=status.HTTP_400_BAD_REQUEST)

        date_path = timezone.now().strftime("%Y/%m/%d")
        ext = os.path.splitext(upload_file.name or "")[1]
        file_name = f"api_asset_{int(timezone.now().timestamp() * 1000)}{ext}"
        storage_path = f"api_asset_files/{date_path}/{file_name}"
        saved_path = default_storage.save(storage_path, upload_file)
        return Response({
            "success": True,
            "file_name": upload_file.name,
            "file_path": saved_path,
            "file_url": default_storage.url(saved_path),
        })

    @action(detail=True, methods=["get"], url_path="config")
    def config(self, request, pk=None):
        """
        详情配置接口：按 apiId 返回创建场景节点需要的完整请求配置。
        """
        asset = self.get_object()
        return Response(
            {
                "id": asset.id,
                "name": asset.name,
                "description": asset.interface_desc or "",
                "method": asset.method,
                "url": asset.url,
                "headers": asset.request_headers or {},
                "params": asset.request_params or {},
                "body": asset.request_body or {},
                "request_body_format": asset.request_body_format or "json",
                "on_failed": "continue",
                "enabled": True,
            },
            status=status.HTTP_200_OK,
        )

    def _find_linked_test_cases(self, asset):
        queryset = TestCase.objects.filter(
            request_method__iexact=asset.method,
            request_url=asset.url,
        )
        if asset.project and asset.project.platform_project_id:
            queryset = queryset.filter(project_id=asset.project.platform_project_id)
        linked_count = queryset.count()
        linked_samples = list(queryset.values("id", "name")[:5])
        return linked_count, linked_samples

    def perform_create(self, serializer):
        asset = serializer.save(created_by=self.request.user)
        _create_history(
            asset=asset,
            operator=self.request.user,
            operation=ApiHistory.OP_CREATE,
            content={"after": _asset_snapshot(asset)},
        )

    def perform_update(self, serializer):
        before = _asset_snapshot(serializer.instance)
        after = _compose_after_snapshot(serializer.instance, serializer.validated_data)
        if _normalize_compare_value(before) == _normalize_compare_value(after):
            return
        asset = serializer.save()
        _create_history(
            asset=asset,
            operator=self.request.user,
            operation=ApiHistory.OP_UPDATE,
            content={"before": before, "after": _asset_snapshot(asset)},
        )
        create_api_asset_change_records(
            asset=asset,
            before_snapshot=before,
            after_snapshot=_asset_snapshot(asset),
            operator=self.request.user,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        before = _asset_snapshot(instance)
        after = _compose_after_snapshot(instance, serializer.validated_data)
        if _normalize_compare_value(before) == _normalize_compare_value(after):
            payload = self.get_serializer(instance).data
            payload["operation_status"] = "noop"
            payload["detail"] = "无变更，跳过更新"
            return Response(payload, status=status.HTTP_200_OK)

        self.perform_update(serializer)
        payload = serializer.data
        payload["operation_status"] = "updated"
        payload["detail"] = "更新成功"
        return Response(payload, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        asset = self.get_object()
        linked_count, linked_samples = self._find_linked_test_cases(asset)
        if linked_count > 0:
            return Response(
                {
                    "success": False,
                    "detail": "删除失败：该接口已被测试用例关联，请先解除关联",
                    "linked_count": linked_count,
                    "linked_samples": linked_samples,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        asset_id = asset.id
        asset_name = asset.name
        asset.is_deleted = True
        asset.save(update_fields=["is_deleted", "updated_at"])
        return Response(
            {
                "success": True,
                "id": asset_id,
                "name": asset_name,
                "detail": "删除成功",
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        asset = self.get_object()
        queryset = asset.histories.select_related("operator").order_by("-created_at")
        serializer = ApiHistorySerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def rollback(self, request, pk=None):
        asset = self.get_object()
        history_id = request.data.get("history_id")
        if not history_id:
            return Response({"detail": "history_id不能为空"}, status=status.HTTP_400_BAD_REQUEST)
        history = get_object_or_404(ApiHistory, id=history_id, asset=asset)
        target = history.content.get("after") or history.content.get("before")
        if not isinstance(target, dict):
            return Response({"detail": "回滚历史快照无效"}, status=status.HTTP_400_BAD_REQUEST)

        field_names = [
            "project",
            "group",
            "name",
            "method",
            "url",
            "interface_desc",
            "request_headers",
            "request_params",
            "request_body_format",
            "request_body",
            "response_schema",
            "error_code",
            "auth_config",
            "status",
            "source",
            "external_id",
            "required",
            "param_type",
            "sort",
            "param_status",
        ]
        for name in field_names:
            if name not in target:
                continue
            value = target.get(name)
            if name == "project":
                if value:
                    asset.project = get_object_or_404(ApiProject, id=value)
                continue
            if name == "group":
                asset.group = get_object_or_404(ApiGroup, id=value) if value else None
                continue
            setattr(asset, name, value)
        asset.save()

        _create_history(
            asset=asset,
            operator=request.user,
            operation=ApiHistory.OP_ROLLBACK,
            content={"from_history_id": history.id, "after": _asset_snapshot(asset)},
        )
        return Response({"detail": "回滚成功", "asset_id": asset.id})

    @action(detail=True, methods=["get"])
    def compare(self, request, pk=None):
        asset = self.get_object()
        from_history_id = request.query_params.get("from")
        to_history_id = request.query_params.get("to")
        if not from_history_id or not to_history_id:
            return Response({"detail": "from和to参数不能为空"}, status=status.HTTP_400_BAD_REQUEST)
        from_history = get_object_or_404(ApiHistory, id=from_history_id, asset=asset)
        to_history = get_object_or_404(ApiHistory, id=to_history_id, asset=asset)
        from_snapshot = from_history.content.get("after") or from_history.content.get("before") or {}
        to_snapshot = to_history.content.get("after") or to_history.content.get("before") or {}
        from_text = json.dumps(from_snapshot, ensure_ascii=False, indent=2, sort_keys=True).splitlines()
        to_text = json.dumps(to_snapshot, ensure_ascii=False, indent=2, sort_keys=True).splitlines()
        diff = "\n".join(difflib.unified_diff(from_text, to_text, fromfile=f"history:{from_history_id}", tofile=f"history:{to_history_id}", lineterm=""))
        return Response({"diff": diff, "from": from_snapshot, "to": to_snapshot})

    @action(detail=True, methods=["post"], url_path="copy-url")
    def copy_url(self, request, pk=None):
        asset = self.get_object()
        return Response({"id": asset.id, "url": asset.url, "method": asset.method})

    @action(detail=False, methods=["post"], url_path="batch-update-status")
    def batch_update_status(self, request):
        ids = request.data.get("ids") or []
        status_value = request.data.get("status")
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "ids不能为空"}, status=status.HTTP_400_BAD_REQUEST)
        allowed_status = {item[0] for item in ApiAsset.STATUS_CHOICES}
        if status_value not in allowed_status:
            return Response({"detail": "status不合法"}, status=status.HTTP_400_BAD_REQUEST)

        queryset = ApiAsset.objects.filter(id__in=ids)
        before_map = {obj.id: _asset_snapshot(obj) for obj in queryset}
        updated = queryset.update(status=status_value)
        for obj in ApiAsset.objects.filter(id__in=ids):
            _create_history(
                asset=obj,
                operator=request.user,
                operation=ApiHistory.OP_UPDATE,
                content={"before": before_map.get(obj.id, {}), "after": _asset_snapshot(obj), "batch": True},
            )
        return Response({"updated_count": updated, "status": status_value})

    @action(detail=True, methods=["post"], url_path="batch-update-params")
    def batch_update_params(self, request, pk=None):
        asset = self.get_object()
        scope = str(request.data.get("scope") or "").strip()
        row_ids = request.data.get("row_ids") or []
        updates = request.data.get("updates") or {}

        scope_to_field = {
            "request_headers": "request_headers",
            "request_params": "request_params",
            "form_data": "request_body",
        }
        if scope not in scope_to_field:
            return Response({"detail": "scope不合法"}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(row_ids, list) or not row_ids:
            return Response({"detail": "row_ids不能为空"}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(updates, dict) or not updates:
            return Response({"detail": "updates不能为空"}, status=status.HTTP_400_BAD_REQUEST)

        target_field = scope_to_field[scope]
        if scope == "form_data" and asset.request_body_format != "form-data":
            return Response({"detail": "当前接口不是form-data模式"}, status=status.HTTP_400_BAD_REQUEST)

        before = _asset_snapshot(asset)
        payload = getattr(asset, target_field) or {}
        rows = _normalize_param_rows(payload, asset)
        row_id_set = {str(item) for item in row_ids}
        updated_count = 0

        for row_key, row_data in rows.items():
            if str(row_data.get("_row_id")) not in row_id_set:
                continue
            if "value" in updates:
                row_data["value"] = updates.get("value")
            if "description" in updates:
                row_data["description"] = str(updates.get("description") or "")
            if "required" in updates:
                row_data["required"] = bool(updates.get("required"))
            if "type" in updates:
                row_data["type"] = str(updates.get("type") or row_data.get("type") or "string")
            rows[row_key] = row_data
            updated_count += 1

        setattr(asset, target_field, rows)
        asset.save(update_fields=[target_field, "updated_at"])
        _create_history(
            asset=asset,
            operator=request.user,
            operation=ApiHistory.OP_UPDATE,
            content={
                "before": before,
                "after": _asset_snapshot(asset),
                "batch_param_update": True,
                "scope": scope,
                "updated_count": updated_count,
            },
        )
        return Response(
            {
                "updated_count": updated_count,
                "scope": scope,
                "payload": getattr(asset, target_field) or {},
            }
        )

    @action(detail=False, methods=["post"], url_path="batch-move-group")
    def batch_move_group(self, request):
        ids = request.data.get("ids") or []
        group_id = request.data.get("group_id")
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "ids不能为空"}, status=status.HTTP_400_BAD_REQUEST)

        queryset = ApiAsset.objects.filter(id__in=ids)
        if not queryset.exists():
            return Response({"detail": "未找到可操作资产"}, status=status.HTTP_404_NOT_FOUND)

        project_ids = set(queryset.values_list("project_id", flat=True))
        if len(project_ids) > 1:
            return Response({"detail": "批量移分组仅支持同一项目内资产"}, status=status.HTTP_400_BAD_REQUEST)

        target_group = None
        if group_id:
            target_group = get_object_or_404(ApiGroup, id=group_id, project_id=next(iter(project_ids)))

        before_map = {obj.id: _asset_snapshot(obj) for obj in queryset}
        moved = queryset.update(group=target_group)
        for obj in ApiAsset.objects.filter(id__in=ids):
            _create_history(
                asset=obj,
                operator=request.user,
                operation=ApiHistory.OP_UPDATE,
                content={"before": before_map.get(obj.id, {}), "after": _asset_snapshot(obj), "batch": True},
            )
        return Response({"moved_count": moved, "group_id": target_group.id if target_group else None})

    @action(detail=False, methods=["post"], url_path="batch-export")
    def batch_export(self, request):
        ids = request.data.get("ids") or []
        export_format = str(request.data.get("format") or "json").lower()
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "ids不能为空"}, status=status.HTTP_400_BAD_REQUEST)
        if export_format not in ["json", "openapi"]:
            return Response({"detail": "仅支持json/openapi"}, status=status.HTTP_400_BAD_REQUEST)

        assets = ApiAsset.objects.select_related("group").filter(id__in=ids).order_by("method", "url")
        if not assets.exists():
            return Response({"detail": "未找到可导出资产"}, status=status.HTTP_404_NOT_FOUND)

        openapi_data = {
            "openapi": "3.0.3",
            "info": {"title": "Batch Export APIs", "version": "1.0.0", "description": "Batch exported API assets"},
            "paths": {},
        }
        for asset in assets:
            path_item = openapi_data["paths"].setdefault(asset.url, {})
            path_item[asset.method.lower()] = {
                "summary": asset.name,
                "tags": [asset.group.name] if asset.group else [],
                "parameters": [
                    {"name": key, "in": "query", "schema": {"type": "string"}}
                    for key in _get_request_params_keys(asset.request_params)
                ],
                "requestBody": (
                    {"content": {"multipart/form-data": {"schema": asset.request_body or {}}}}
                    if asset.request_body_format == "form-data"
                    else {"content": {"application/json": {"schema": asset.request_body or {}}}}
                ),
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {"application/json": {"schema": asset.response_schema or {}}},
                    }
                },
            }
        return Response(
            {
                "format": export_format,
                "content": openapi_data,
                "ids": list(assets.values_list("id", flat=True)),
                "count": assets.count(),
            }
        )

    @action(detail=False, methods=["post"], url_path="batch-delete")
    def batch_delete(self, request):
        ids = request.data.get("ids") or []
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "ids不能为空"}, status=status.HTTP_400_BAD_REQUEST)

        requested_ids = [int(i) for i in ids if str(i).isdigit()]
        unique_ids = list(dict.fromkeys(requested_ids))
        assets = {asset.id: asset for asset in ApiAsset.objects.filter(id__in=unique_ids)}

        deleted_count = 0
        failed_items = []
        for asset_id in unique_ids:
            asset = assets.get(asset_id)
            if not asset:
                failed_items.append({"id": asset_id, "reason": "接口不存在"})
                continue

            linked_count, _ = self._find_linked_test_cases(asset)
            if linked_count > 0:
                failed_items.append(
                    {
                        "id": asset_id,
                        "name": asset.name,
                        "reason": f"已被{linked_count}条测试用例关联，无法删除",
                    }
                )
                continue

            asset.delete()
            deleted_count += 1

        failed_count = len(failed_items)
        return Response(
            {
                "success": failed_count == 0,
                "deleted_count": deleted_count,
                "failed_count": failed_count,
                "failed_items": failed_items,
            }
        )


class ApiPresetViewSet(viewsets.ModelViewSet):
    queryset = ApiPreset.objects.select_related("project", "created_by").all()
    serializer_class = ApiPresetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = ApiPreset.objects.select_related("project", "created_by").all()
        project_id = self.request.query_params.get("project")
        preset_type = self.request.query_params.get("preset_type")
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        if preset_type:
            queryset = queryset.filter(preset_type=preset_type)
        return queryset.order_by("-updated_at", "-id")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        if serializer.instance.created_by_id != self.request.user.id and not self.request.user.is_staff:
            raise PermissionDenied("仅创建人可修改预设")
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        preset = self.get_object()
        if preset.created_by_id != request.user.id and not request.user.is_staff:
            return Response({"detail": "仅创建人可删除预设"}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


class ApiAssetDraftViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def _resolve_project(self, request):
        project_id = request.data.get("project_id") or request.query_params.get("project_id")
        if not project_id:
            return None
        return get_object_or_404(ApiProject, id=project_id)

    @action(detail=False, methods=["post"], url_path="upsert")
    def upsert(self, request):
        _cleanup_expired_asset_drafts()
        asset_id = request.data.get("asset_id")
        draft_key = str(request.data.get("draft_key") or "").strip()
        draft_data = request.data.get("draft_data") or {}
        if not isinstance(draft_data, dict):
            return Response({"detail": "draft_data必须为对象"}, status=status.HTTP_400_BAD_REQUEST)

        asset = None
        project = None
        if asset_id:
            asset = get_object_or_404(ApiAsset, id=asset_id)
            project = asset.project
        else:
            project = self._resolve_project(request)
            if not project:
                return Response({"detail": "asset_id或project_id必填"}, status=status.HTTP_400_BAD_REQUEST)
            if not draft_key:
                return Response({"detail": "新建草稿需提供draft_key"}, status=status.HTTP_400_BAD_REQUEST)

        expires_at = timezone.now() + timedelta(hours=24)
        if asset:
            draft_obj, _ = ApiAssetDraft.objects.get_or_create(
                project=project,
                asset=asset,
                created_by=request.user,
                defaults={"draft_key": "", "draft_data": {}, "expires_at": expires_at},
            )
        else:
            draft_obj, _ = ApiAssetDraft.objects.get_or_create(
                project=project,
                draft_key=draft_key,
                asset=None,
                created_by=request.user,
                defaults={"draft_data": {}, "expires_at": expires_at},
            )

        draft_obj.draft_data = draft_data
        draft_obj.expires_at = expires_at
        draft_obj.save(update_fields=["draft_data", "expires_at", "updated_at"])
        return Response(ApiAssetDraftSerializer(draft_obj).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="load")
    def load(self, request):
        _cleanup_expired_asset_drafts()
        asset_id = request.query_params.get("asset_id")
        draft_key = str(request.query_params.get("draft_key") or "").strip()
        project = self._resolve_project(request)

        queryset = ApiAssetDraft.objects.filter(created_by=request.user, expires_at__gt=timezone.now())
        if asset_id:
            queryset = queryset.filter(asset_id=asset_id)
        else:
            if not project or not draft_key:
                return Response({"detail": "asset_id或(project_id+draft_key)必填"}, status=status.HTTP_400_BAD_REQUEST)
            queryset = queryset.filter(project=project, asset__isnull=True, draft_key=draft_key)

        draft_obj = queryset.order_by("-updated_at").first()
        if not draft_obj:
            return Response({"detail": "未找到草稿"}, status=status.HTTP_404_NOT_FOUND)
        return Response(ApiAssetDraftSerializer(draft_obj).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="clear")
    def clear(self, request):
        asset_id = request.data.get("asset_id")
        draft_key = str(request.data.get("draft_key") or "").strip()
        project = self._resolve_project(request)

        queryset = ApiAssetDraft.objects.filter(created_by=request.user)
        if asset_id:
            queryset = queryset.filter(asset_id=asset_id)
        else:
            if not project or not draft_key:
                return Response({"detail": "asset_id或(project_id+draft_key)必填"}, status=status.HTTP_400_BAD_REQUEST)
            queryset = queryset.filter(project=project, asset__isnull=True, draft_key=draft_key)

        deleted_count, _ = queryset.delete()
        return Response({"cleared_count": deleted_count}, status=status.HTTP_200_OK)


def _find_conflict_assets(project_id, items):
    """
    以 URL + Method 为唯一标识，查找与现有 API 资产冲突的接口。
    返回: { (method, url): ApiAsset } 的映射。
    """
    if not project_id or not items:
        return {}
    method_urls = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        method = _normalize_method(item.get("method"))
        url = str(item.get("url") or "").strip()
        if method and url:
            method_urls.add((method, url))
    if not method_urls:
        return {}
    q = Q()
    for method, url in method_urls:
        q |= Q(method=method, url=url)
    existing = ApiAsset.objects.filter(project_id=project_id, is_deleted=False).filter(q)
    return {(a.method, a.url): a for a in existing}


class ApiImportExportViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="preview")
    def preview_import(self, request):
        upload_file = request.FILES.get("file")
        file_type = request.data.get("file_type")
        project_id = request.data.get("project_id")
        if not upload_file or not file_type:
            return Response({"detail": "file和file_type不能为空"}, status=status.HTTP_400_BAD_REQUEST)

        data = _read_upload_data(upload_file)
        if data is None:
            return Response({"detail": "导入文件解析失败"}, status=status.HTTP_400_BAD_REQUEST)

        file_type = str(file_type).lower()
        if file_type == "postman":
            items = _parse_postman_collection(data)
        elif file_type == "openapi":
            items = _parse_openapi(data)
        elif file_type == "apifox":
            items = _parse_apifox(data)
        else:
            return Response({"detail": "不支持的file_type"}, status=status.HTTP_400_BAD_REQUEST)

        conflict_map = _find_conflict_assets(project_id, items)
        for item in items:
            method = _normalize_method(item.get("method"))
            url = str(item.get("url") or "").strip()
            existing = conflict_map.get((method, url))
            if existing:
                item["_conflict"] = {
                    "existing_id": existing.id,
                    "existing_name": existing.name,
                    "existing_updated_at": existing.updated_at.isoformat() if existing.updated_at else None,
                }
            else:
                item["_conflict"] = None

        response_payload = {"count": len(items), "items": items, "conflict_count": len(conflict_map)}
        # Apifox：同时解析 environments，供确认导入时回传并写入平台「环境」模块（无 environments 时为空列表，不报错）
        if file_type == "apifox":
            response_payload["apifox_environment_import"] = parse_apifox_environments_from_json(data)
        return Response(response_payload)

    @action(detail=False, methods=["post"], url_path="preview-url")
    def preview_url(self, request):
        """在线导入：从 URL 拉取并解析 OpenAPI/Swagger 规范。"""
        url = request.data.get("url")
        project_id = request.data.get("project_id")
        if not url:
            return Response({"detail": "url不能为空"}, status=status.HTTP_400_BAD_REQUEST)

        data, err = _fetch_and_parse_from_url(url)
        if err:
            return Response({"detail": err}, status=status.HTTP_400_BAD_REQUEST)

        if not _is_openapi_or_swagger(data):
            return Response({"detail": "链接格式不支持，仅支持 OpenAPI/Swagger v1/v2/v3 规范"}, status=status.HTTP_400_BAD_REQUEST)

        if _is_swagger_1x(data):
            items = _parse_swagger_1x(data)
            if not items:
                items = _fetch_swagger_1x_resource_listing(url, data)
        else:
            items = _parse_openapi(data)

        if not items:
            return Response({"detail": "未解析到任何接口，请检查链接内容"}, status=status.HTTP_400_BAD_REQUEST)

        conflict_map = _find_conflict_assets(project_id, items)
        for item in items:
            method = _normalize_method(item.get("method"))
            url_str = str(item.get("url") or "").strip()
            existing = conflict_map.get((method, url_str))
            if existing:
                item["_conflict"] = {
                    "existing_id": existing.id,
                    "existing_name": existing.name,
                    "existing_updated_at": existing.updated_at.isoformat() if existing.updated_at else None,
                }
            else:
                item["_conflict"] = None

        return Response({"count": len(items), "items": items, "conflict_count": len(conflict_map)})

    @action(detail=False, methods=["post"], url_path="confirm")
    def confirm_import(self, request):
        project_id = request.data.get("project_id")
        target_group_id = request.data.get("group_id")
        items = request.data.get("items")
        default_conflict_strategy = str(request.data.get("default_conflict_strategy") or "skip").lower()
        if default_conflict_strategy not in ("overwrite", "skip", "keep_both"):
            default_conflict_strategy = "skip"
        if not project_id or not isinstance(items, list):
            return Response({"detail": "project_id和items不能为空"}, status=status.HTTP_400_BAD_REQUEST)

        project = get_object_or_404(ApiProject, id=project_id)
        target_group = None
        if target_group_id:
            target_group = get_object_or_404(ApiGroup, id=target_group_id, project=project)

        with transaction.atomic():
            # Apifox 环境变量：与接口资产在同一事务中提交，保证「环境 + 变量」与 API 导入一致回滚
            platform_project = getattr(project, "platform_project", None)
            if not platform_project:
                env_import_stats = empty_apifox_environment_import_stats("api_project_not_bound_to_platform_project")
            elif not _should_attempt_apifox_environment_import(request, items):
                env_import_stats = empty_apifox_environment_import_stats("skipped_not_apifox_environment_import")
            else:
                payload = _resolve_apifox_environment_payload_for_confirm(request)
                if payload is not None:
                    env_import_stats = apply_apifox_environment_import(platform_project, payload)
                else:
                    env_import_stats = empty_apifox_environment_import_stats("no_apifox_environment_payload")

            group_cache = {}
            import_suffix = f"_import_{timezone.now().strftime('%Y%m%d')}"

            def resolve_group(group_path):
                if not group_path:
                    return target_group
                current_parent = target_group
                for name in group_path:
                    key = (current_parent.id if current_parent else 0, str(name))
                    if key in group_cache:
                        current_parent = group_cache[key]
                        continue
                    group_obj, _ = ApiGroup.objects.get_or_create(
                        project=project,
                        parent=current_parent,
                        name=str(name)[:200],
                        defaults={"sort_order": 0},
                    )
                    group_cache[key] = group_obj
                    current_parent = group_obj
                return current_parent

            created_count = 0
            updated_count = 0
            skipped_count = 0
            imported_ids = []
            for raw in items:
                if not isinstance(raw, dict):
                    continue
                normalized = _normalize_item(raw, raw.get("source") or ApiAsset.SOURCE_MANUAL)
                # request_params 必须为 list（模型 default=list），导入流程产出 dict 时需转换
                if isinstance(normalized.get("request_params"), dict):
                    normalized["request_params"] = _dict_params_to_array(normalized["request_params"])
                name = (normalized.get("name") or "")[:150]
                method = _normalize_method(normalized.get("method"))
                url = normalized.get("url") or ""
                external_id = normalized.get("external_id") or ""
                source = normalized.get("source") or ApiAsset.SOURCE_MANUAL
                conflict_info = raw.get("_conflict")
                strategy = str(raw.get("_conflict_strategy") or default_conflict_strategy).lower()
                if strategy not in ("overwrite", "skip", "keep_both"):
                    strategy = default_conflict_strategy

                existing = None
                if conflict_info and conflict_info.get("existing_id"):
                    existing = ApiAsset.objects.filter(
                        project=project, id=conflict_info["existing_id"], is_deleted=False
                    ).first()
                if not existing:
                    existing = ApiAsset.objects.filter(
                        project=project, method=method, url=url, is_deleted=False
                    ).first()

                if existing:
                    if strategy == "skip":
                        skipped_count += 1
                        continue
                    if strategy == "overwrite":
                        existing.name = name or f"{method} {url}"
                        existing.request_headers = normalized.get("request_headers") or {}
                        existing.request_params = normalized.get("request_params") or {}
                        existing.request_body_format = _normalize_body_format(normalized.get("request_body_format"))
                        existing.request_body = normalized.get("request_body") or {}
                        existing.response_schema = normalized.get("response_schema") or {}
                        existing.auth_config = normalized.get("auth_config") or {}
                        existing.source = source
                        existing.external_id = str(external_id)[:200]
                        existing.save(update_fields=[
                            "name", "request_headers", "request_params", "request_body_format",
                            "request_body", "response_schema", "auth_config", "source", "external_id", "updated_at"
                        ])
                        _create_history(existing, request.user, ApiHistory.OP_UPDATE, {
                            "after": _asset_snapshot(existing), "imported": True, "strategy": "overwrite"
                        })
                        updated_count += 1
                        imported_ids.append(existing.id)
                        continue
                    if strategy == "keep_both":
                        name = (name or f"{method} {url}").rstrip()
                        if len(name) > 150 - len(import_suffix):
                            name = name[: 150 - len(import_suffix)]
                        name = name + import_suffix

                group = resolve_group(normalized.get("group_path") or [])
                asset = ApiAsset.objects.create(
                    project=project,
                    group=group,
                    name=name or f"{method} {url}",
                    method=method,
                    url=url,
                    request_headers=normalized.get("request_headers") or {},
                    request_params=normalized.get("request_params") or {},
                    request_body_format=_normalize_body_format(normalized.get("request_body_format")),
                    request_body=normalized.get("request_body") or {},
                    response_schema=normalized.get("response_schema") or {},
                    auth_config=normalized.get("auth_config") or {},
                    status=ApiAsset.STATUS_ACTIVE,
                    source=source,
                    external_id=str(external_id)[:200],
                    created_by=request.user,
                )
                _create_history(asset, request.user, ApiHistory.OP_CREATE, {"after": _asset_snapshot(asset), "imported": True})
                created_count += 1
                imported_ids.append(asset.id)

        return Response({
            "created_count": created_count,
            "updated_count": updated_count,
            "skipped_count": skipped_count,
            "imported_ids": imported_ids,
            "environment_import": env_import_stats,
        })

    @action(detail=False, methods=["post"], url_path="export")
    def export_assets(self, request):
        project_id = request.data.get("project_id")
        export_format = str(request.data.get("format") or "json").lower()
        if not project_id:
            return Response({"detail": "project_id不能为空"}, status=status.HTTP_400_BAD_REQUEST)
        project = get_object_or_404(ApiProject, id=project_id)
        assets = project.assets.select_related("group").order_by("group_id", "id")

        openapi_data = {
            "openapi": "3.0.3",
            "info": {"title": project.name, "version": "1.0.0"},
            "paths": {},
        }
        for asset in assets:
            path = asset.url or "/"
            if path not in openapi_data["paths"]:
                openapi_data["paths"][path] = {}
            method = (asset.method or "GET").lower()
            operation = {
                "summary": asset.name,
                "tags": [asset.group.name] if asset.group else [],
                "parameters": [],
                "responses": {"200": {"description": "Success"}},
            }

            for key in _get_request_params_keys(asset.request_headers):
                operation["parameters"].append({"name": key, "in": "header", "schema": {"type": "string"}})
            for key in _get_request_params_keys(asset.request_params):
                operation["parameters"].append({"name": key, "in": "query", "schema": {"type": "string"}})

            if asset.request_body:
                content_type = "application/json" if asset.request_body_format == "json" else "multipart/form-data"
                operation["requestBody"] = {
                    "required": False,
                    "content": {content_type: {"schema": asset.request_body}},
                }
            if asset.response_schema:
                operation["responses"]["200"]["content"] = {"application/json": {"schema": asset.response_schema}}

            openapi_data["paths"][path][method] = operation

        if export_format == "yaml":
            if not yaml:
                return Response({"detail": "环境未安装PyYAML，无法导出YAML"}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"format": "yaml", "content": yaml.safe_dump(openapi_data, sort_keys=False, allow_unicode=True)})
        return Response({"format": "json", "content": openapi_data})
