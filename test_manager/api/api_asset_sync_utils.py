# -*- coding: utf-8 -*-
"""
API 资产与场景节点同步工具：差异计算、变更记录创建等。
"""
from django.utils import timezone

from test_manager.models import ApiAsset, ApiAssetChangeRecord, TestSceneNode


def _normalize_kv_payload_to_dict(payload):
    """将 request_headers/request_params 归一化为 dict，支持 list 格式。"""
    if not payload:
        return {}
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, list):
        result = {}
        for item in payload:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or item.get("name") or "").strip()
            if not key:
                continue
            result[key] = item.get("value", "")
        return result
    return {}


def _normalize_formdata_body_to_dict(payload):
    """
    将 API 资产 form-data 请求体从数组格式转为节点 dict 格式。

    数组格式（API 资产存储）：
        [{key, type, value, fileName}, ...]

    Dict 格式（执行器 / 节点存储）：
        {key: {value, type}}  或  {key: {type: "File", file_path, file_name}}

    与前端 kvRowsToObjectWithType() 行为对齐。
    """
    if not payload:
        return {}
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, list):
        result = {}
        for item in payload:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or "").strip()
            if not key:
                continue
            raw_type = str(item.get("type") or "string").lower()
            val = item.get("value", "")
            if raw_type == "file" and val:
                result[key] = {
                    "type": "File",
                    "file_path": val,
                    "file_name": item.get("fileName") or item.get("file_name") or "",
                }
            else:
                result[key] = {
                    "value": val,
                    "type": raw_type,
                }
        return result
    return {}


def _extract_param_keys(payload):
    """从 request_params/request_headers/request_body 中提取参数 key 列表。"""
    d = _normalize_kv_payload_to_dict(payload)
    keys = set()
    for key in d:
        if not key or str(key).startswith("_"):
            continue
        keys.add(str(key).strip())
    return keys


def _extract_kv_value(val):
    """从键值对中提取可比较的字符串值。"""
    if val is None:
        return ""
    if isinstance(val, dict) and "value" in val:
        return str(val.get("value") or "")
    if isinstance(val, (str, int, float, bool)):
        return str(val)
    return str(val) if val else ""


def _extract_schema_paths(schema, prefix=""):
    """从 response_schema 中提取字段路径列表（扁平化）。
    支持对象根节点和数组根节点（{"type":"array","items":{"properties":...}}）格式。
    """
    if not schema or not isinstance(schema, dict):
        return set()
    paths = set()

    # 数组根节点：从 items.properties 中提取字段路径
    if schema.get("type") == "array" and isinstance(schema.get("items"), dict):
        items_schema = schema["items"]
        props = items_schema.get("properties")
        if isinstance(props, dict):
            for key, value in props.items():
                if not key:
                    continue
                path = f"{prefix}.{key}" if prefix else key
                paths.add(path)
                if isinstance(value, dict) and ("properties" in value or "items" in value):
                    sub = value.get("properties") or (value.get("items") or {}).get("properties") or {}
                    if isinstance(sub, dict):
                        paths.update(_extract_schema_paths({"properties": sub}, path))
        return paths

    # 标准对象根节点
    props = schema.get("properties") or schema
    if not isinstance(props, dict):
        return paths
    for key, value in props.items():
        if not key:
            continue
        path = f"{prefix}.{key}" if prefix else key
        paths.add(path)
        if isinstance(value, dict) and ("properties" in value or "items" in value):
            sub = value.get("properties") or (value.get("items") or {}).get("properties") or {}
            if isinstance(sub, dict):
                paths.update(_extract_schema_paths({"properties": sub}, path))
    return paths


def compute_node_api_diff(node):
    """
    计算节点与关联 API 资产的差异。
    返回 dict: basic, request, response, sync_status
    """
    if not node or not node.api_asset_id:
        return None
    asset = node.api_asset
    if not asset:
        return None

    # 使用 api_sync_snapshot 作为「上次同步时的 API 状态」，若无则用当前 asset 视为已同步
    synced_snapshot = node.api_sync_snapshot or {}
    asset_updated_at = asset.updated_at

    # 判断基础信息是否已同步：api_synced_at >= asset.updated_at 或 无差异
    basic_synced = False
    if node.api_synced_at and asset_updated_at:
        basic_synced = node.api_synced_at >= asset_updated_at
    elif not synced_snapshot:
        # 从未同步过，检查是否有差异
        basic_synced = False

    old_url = synced_snapshot.get("url") or asset.url
    old_method = synced_snapshot.get("method") or asset.method
    url_changed = (asset.url or "") != (old_url or "")
    method_changed = (asset.method or "").upper() != (old_method or "").upper()

    basic = {
        "url": {
            "changed": url_changed,
            "old": old_url or "",
            "new": asset.url or "",
        },
        "method": {
            "changed": method_changed,
            "old": old_method or "",
            "new": asset.method or "",
        },
    }

    # 请求参数差异
    asset_params = _extract_param_keys(asset.request_params or {})
    asset_headers_dict = _normalize_kv_payload_to_dict(asset.request_headers or {})
    node_headers_dict = _normalize_kv_payload_to_dict(node.request_headers or {})
    asset_headers = _extract_param_keys(asset_headers_dict)
    node_headers = _extract_param_keys(node_headers_dict)
    node_params = _extract_param_keys(node.request_params or {})

    params_added = list(asset_params - node_params)
    params_removed = list(node_params - asset_params)
    headers_added = list(asset_headers - node_headers)
    headers_removed = list(node_headers - asset_headers)

    # 请求头值变更：同 key 但 value 不同
    headers_value_changed = []
    for key in asset_headers & node_headers:
        asset_val = _extract_kv_value(asset_headers_dict.get(key))
        node_val = _extract_kv_value(node_headers_dict.get(key))
        if asset_val != node_val:
            headers_value_changed.append({"key": key, "old": node_val, "new": asset_val})

    old_body_format = synced_snapshot.get("request_body_format") or asset.request_body_format
    body_format_changed = (asset.request_body_format or "json") != (old_body_format or "json")

    request_diff = {
        "params_added": params_added,
        "params_removed": params_removed,
        "headers_added": headers_added,
        "headers_removed": headers_removed,
        "headers_value_changed": headers_value_changed,
        "body_format_changed": body_format_changed,
    }

    # 响应结构差异：仅当存在同步快照中的 response_schema 时才能计算「新增/删除」字段
    # 若无同步快照（节点从未执行过 sync-basic），无基准可比较，不应误报「新增响应字段」
    asset_schema = asset.response_schema or {}
    asset_paths = _extract_schema_paths(asset_schema)
    synced_paths = _extract_schema_paths(synced_snapshot.get("response_schema") or {})
    has_response_baseline = "response_schema" in synced_snapshot
    if has_response_baseline:
        fields_added = list(asset_paths - synced_paths)
        fields_removed = list(synced_paths - asset_paths)
    else:
        fields_added = []
        fields_removed = []

    # 检查断言/提取规则中引用的路径是否已失效
    warnings = []
    if isinstance(node.assert_rules, list):
        for rule in node.assert_rules:
            path = rule.get("path") or rule.get("field") or rule.get("json_path") or ""
            if path and path in fields_removed:
                warnings.append(f"断言路径 {path} 可能已失效")
    if isinstance(node.extract_rules, list):
        for rule in node.extract_rules:
            path = rule.get("path") or rule.get("json_path") or rule.get("source") or ""
            if path and path in fields_removed:
                warnings.append(f"提取规则路径 {path} 可能已失效")

    response_diff = {
        "fields_added": fields_added,
        "fields_removed": fields_removed,
        "warnings": list(set(warnings)),
    }

    has_any_diff = (
        url_changed or method_changed
        or params_added or params_removed or headers_added or headers_removed or headers_value_changed
        or body_format_changed
        or fields_added or fields_removed
    )

    sync_status = {
        "basic_synced": basic_synced and not (url_changed or method_changed),
        "can_sync_basic": url_changed or method_changed,
        "can_add_params": bool(params_added or headers_added),
        "can_sync_params": bool(params_added or params_removed),
        "can_sync_headers": bool(headers_added or headers_value_changed or headers_removed),
    }

    return {
        "node_id": node.id,
        "api_asset_id": asset.id,
        "api_asset_name": asset.name or "",
        "api_updated_at": asset_updated_at.isoformat() if asset_updated_at else None,
        "diffs": {
            "basic": basic,
            "request": request_diff,
            "response": response_diff,
        },
        "sync_status": sync_status,
        "has_diff": has_any_diff,
    }


def _normalize_url_for_compare(url):
    """URL 归一化：去除首尾空格，用于检测无意义变更（仅空格变化）。"""
    return (url or "").strip()


def _normalize_method_for_compare(method):
    """Method 归一化：转大写，用于检测无意义变更（仅大小写变化）。"""
    return (method or "").upper()


def _extract_param_core_schema(payload):
    """
    从参数字典提取核心结构（字段名、必传性、类型），过滤描述等非核心字段。
    用于变更检测时仅关注核心变更。支持 dict 和 list 格式。
    """
    d = _normalize_kv_payload_to_dict(payload)
    if not d:
        return {}
    result = {}
    for key, val in d.items():
        if not key or str(key).startswith("_"):
            continue
        k = str(key).strip()
        if isinstance(val, dict):
            result[k] = {
                "required": bool(val.get("required")),
                "type": str(val.get("type") or (val.get("schema") or {}).get("type") or "string"),
            }
        else:
            result[k] = {"required": False, "type": "string"}
    return result


def create_api_asset_change_records(asset, before_snapshot, after_snapshot, operator=None):
    """
    API 资产更新后，创建变更记录。
    before_snapshot / after_snapshot 为 _asset_snapshot 格式。
    仅检测核心变更，过滤非核心变更（接口名称、备注、参数描述）及无意义变更（URL/Method 仅空格/大小写）。
    """
    records = []
    change_types = []

    # URL/Method：仅当实际值变化时记录，过滤仅空格/大小写变化
    url_before = _normalize_url_for_compare(before_snapshot.get("url"))
    url_after = _normalize_url_for_compare(after_snapshot.get("url"))
    if url_before != url_after:
        change_types.append(ApiAssetChangeRecord.CHANGE_URL_METHOD)
    method_before = _normalize_method_for_compare(before_snapshot.get("method"))
    method_after = _normalize_method_for_compare(after_snapshot.get("method"))
    if method_before != method_after:
        if ApiAssetChangeRecord.CHANGE_URL_METHOD not in change_types:
            change_types.append(ApiAssetChangeRecord.CHANGE_URL_METHOD)

    # 请求参数：仅比较字段名、必传性、类型，过滤参数描述
    params_core_before = _extract_param_core_schema(before_snapshot.get("request_params"))
    params_core_after = _extract_param_core_schema(after_snapshot.get("request_params"))
    if params_core_before != params_core_after:
        change_types.append(ApiAssetChangeRecord.CHANGE_REQUEST_PARAMS)
    headers_core_before = _extract_param_core_schema(before_snapshot.get("request_headers"))
    headers_core_after = _extract_param_core_schema(after_snapshot.get("request_headers"))
    if headers_core_before != headers_core_after:
        change_types.append(ApiAssetChangeRecord.CHANGE_REQUEST_PARAMS)

    # 请求体格式、请求体结构
    if (before_snapshot.get("request_body_format") or "") != (after_snapshot.get("request_body_format") or ""):
        change_types.append(ApiAssetChangeRecord.CHANGE_REQUEST_BODY)
    if _normalize_compare(before_snapshot.get("request_body")) != _normalize_compare(after_snapshot.get("request_body")):
        change_types.append(ApiAssetChangeRecord.CHANGE_REQUEST_BODY)

    # 响应 Schema、错误码
    if _normalize_compare(before_snapshot.get("response_schema")) != _normalize_compare(after_snapshot.get("response_schema")):
        change_types.append(ApiAssetChangeRecord.CHANGE_RESPONSE_SCHEMA)
    if _normalize_compare(before_snapshot.get("error_code")) != _normalize_compare(after_snapshot.get("error_code")):
        change_types.append(ApiAssetChangeRecord.CHANGE_ERROR_CODE)

    for ct in set(change_types):
        rec = ApiAssetChangeRecord.objects.create(
            asset=asset,
            change_type=ct,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            created_by=operator,
        )
        records.append(rec)
    return records


def _normalize_compare(value):
    """用于比较的归一化。"""
    if value is None:
        return {}
    if isinstance(value, dict):
        return {str(k): _normalize_compare(v) for k, v in sorted(value.items(), key=lambda x: str(x[0]))}
    if isinstance(value, list):
        return [_normalize_compare(item) for item in value]
    return value


def get_node_snapshot_for_rollback(node):
    """获取节点当前配置快照，用于回滚。"""
    return {
        "request_headers": node.request_headers or {},
        "request_params": node.request_params or {},
        "request_body": node.request_body or {},
        "param_type": node.param_type or "json",
        "body_type": node.body_type or "json",
        "assert_rules": node.assert_rules or [],
        "extract_rules": node.extract_rules or [],
        "expected_status_code": node.expected_status_code or 200,
        "api_synced_at": node.api_synced_at.isoformat() if node.api_synced_at else None,
        "api_sync_snapshot": node.api_sync_snapshot or {},
    }


def build_asset_snapshot_for_node(asset):
    """构建用于节点同步的 API 资产快照。"""
    return {
        "url": asset.url or "",
        "method": asset.method or "",
        "request_params": asset.request_params or {},
        "request_headers": asset.request_headers or {},
        "request_body": asset.request_body or {},
        "request_body_format": asset.request_body_format or "json",
        "response_schema": asset.response_schema or {},
        "error_code": asset.error_code or [],
    }
