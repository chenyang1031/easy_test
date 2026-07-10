# -*- coding: utf-8 -*-
"""
HTTP Archive (HAR) 解析器

解析 Fiddler / Chrome 等导出的 HAR JSON，输出结构与 goreplay_parser.parse_gor_file 一致。
"""
import base64
import json
import re
from datetime import datetime
from io import BytesIO
from urllib.parse import parse_qs, urlparse

from test_manager.utils.goreplay_parser import ALLOWED_METHODS, normalize_url_for_match

# multipart boundary 文本解析用正则（预编译提升性能）
_MULTIPART_FIELD_RE = re.compile(r'name="([^"]*)"\s*\n\s*\n(.*?)(?=\n-{2,}|\Z)', re.DOTALL)
_MULTIPART_TRAIL_RE = re.compile(r'\n-{2,}.*$', re.DOTALL)

# 跳过的静态资源路径扩展名（仅路径最后一段）
_STATIC_EXT_RE = re.compile(
    r"\.(?:js|mjs|cjs|css|png|jpe?g|gif|webp|svg|ico|woff2?|ttf|eot|map|mp4|webm|mp3|wav)$",
    re.I,
)

_MAX_RESPONSE_TEXT_BYTES = 512 * 1024


def _headers_to_dict(header_list):
    """HAR headers 数组 -> dict，同名后者覆盖。"""
    out = {}
    if not header_list:
        return out
    for h in header_list:
        if not isinstance(h, dict):
            continue
        name = (h.get("name") or "").strip()
        if not name:
            continue
        out[name] = h.get("value") or ""
    return out


def _query_string_to_params(qs_list):
    """HAR queryString 数组 -> params dict。"""
    params = {}
    if not qs_list:
        return params
    for item in qs_list:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if name is None:
            continue
        params[name] = item.get("value", "")
    return params


def _parse_multipart_body(text):
    """从 multipart/form-data 原始 boundary 文本提取键值对。

    部分 HAR 导出工具（如 Fiddler）的 postData 只有 text 没有 params 数组，
    此函数作为 fallback，行为对齐 goreplay 的 form 解析。
    """
    if not text:
        return None
    normalized = text.replace("\r\n", "\n")
    result = {}
    for m in _MULTIPART_FIELD_RE.finditer(normalized):
        val = _MULTIPART_TRAIL_RE.sub("", m.group(2)).strip()
        result[m.group(1)] = val
    return result if result else None


def _parse_request_body(post_data, headers_dict):
    """根据 postData 与 Content-Type 解析请求体，行为对齐 goreplay _parse_http_request。"""
    if not post_data or not isinstance(post_data, dict):
        return None

    mime = (post_data.get("mimeType") or "").lower()
    text = post_data.get("text")
    params_list = post_data.get("params")

    content_type = (headers_dict.get("Content-Type") or "").lower()
    if not mime:
        mime = content_type

    if "multipart" in mime or "multipart" in content_type:
        # HAR 的 multipart/form-data 在 postData.params 中已解析好键值对，优先使用
        if params_list and isinstance(params_list, list):
            merged = {}
            for p in params_list:
                if not isinstance(p, dict):
                    continue
                k = p.get("name")
                if k is None:
                    continue
                merged[k] = p.get("value", "")
            if merged:
                return merged
        # Fiddler 等导出工具可能无 params，尝试从 boundary 文本解析
        if text:
            parsed = _parse_multipart_body(text)
            if parsed:
                return parsed
            return {"_raw": text}
        return {"_raw": "<multipart form data>"}

    if params_list and isinstance(params_list, list):
        merged = {}
        for p in params_list:
            if not isinstance(p, dict):
                continue
            k = p.get("name")
            if k is None:
                continue
            merged[k] = p.get("value", "")
        if merged:
            return merged

    if text is None or text == "":
        return None

    if "application/json" in mime or "application/json" in content_type or "+json" in mime:
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
            # 原始 JSON 值（加密字符串/数字/布尔）wrap 为 _raw，防下游 isinstance(body, dict) 检查丢弃
            return {"_raw": text}
        except (json.JSONDecodeError, TypeError):
            return {"_raw": text}

    if "application/x-www-form-urlencoded" in mime or "application/x-www-form-urlencoded" in content_type:
        try:
            parsed = parse_qs(str(text), keep_blank_values=True)
            return {k: (v[0] if len(v) == 1 else v) for k, v in parsed.items()}
        except Exception:
            return {"_raw": text}

    return {"_raw": text}


def _parse_response_body(content_obj, resp_headers_dict):
    """解析 HAR response.content，含 base64 解码。"""
    if not content_obj or not isinstance(content_obj, dict):
        return None

    mime = (content_obj.get("mimeType") or "").lower()
    text = content_obj.get("text")
    encoding = (content_obj.get("encoding") or "").lower()
    hdr_ct = (resp_headers_dict.get("Content-Type") or "").lower()
    if not mime:
        mime = hdr_ct

    raw_str = None
    if encoding == "base64" and text:
        try:
            raw = base64.b64decode(text, validate=False)
            if len(raw) > _MAX_RESPONSE_TEXT_BYTES:
                return {"_raw": f"<binary {len(raw)} bytes>"}
            raw_str = raw.decode("utf-8", errors="replace")
        except Exception:
            return {"_raw": "<invalid base64>"}
    elif text is not None and text != "":
        raw_str = text
    else:
        return None

    if "application/json" in mime or "application/json" in hdr_ct or "+json" in mime:
        try:
            parsed = json.loads(raw_str)
            if isinstance(parsed, (dict, list)):
                return parsed
            # 原始 JSON 值（字符串/数字/布尔）wrap 为 _raw，防下游 isinstance(body, dict) 检查丢弃
            return {"_raw": raw_str}
        except (json.JSONDecodeError, TypeError):
            return {"_raw": raw_str}

    # base64 后偶见 Content-Type 为 octet-stream，但实为 JSON 文本
    s = raw_str.strip()
    if s[:1] in "{[":
        try:
            return json.loads(raw_str)
        except (json.JSONDecodeError, TypeError):
            pass

    return {"_raw": raw_str}


def _should_skip_static(url):
    """按路径末段扩展名过滤常见静态资源。"""
    if not url:
        return False
    try:
        path = urlparse(url).path or ""
    except Exception:
        return False
    if not path or path.endswith("/"):
        return False
    last = path.rsplit("/", 1)[-1]
    if not last or "." not in last:
        return False
    return bool(_STATIC_EXT_RE.search(last))


def _parse_started_time(entry):
    """返回用于排序的时间戳（datetime），失败则 None。"""
    s = entry.get("startedDateTime")
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def parse_har_file(file_obj, max_requests=500):
    """
    解析 HAR 文件，返回请求列表（结构与 parse_gor_file 一致）。

    :param file_obj: 支持 read() 的文件对象
    :param max_requests: 最大请求条数
    :return: list[dict]，每项含 method, url, url_full, headers, params, body,
             request_id, timestamp, response（或 None）
    :raises ValueError: 非 HAR、无有效条目等
    """
    raw = file_obj.read()
    if isinstance(raw, str):
        text = raw.lstrip("\ufeff")
    else:
        # utf-8-sig：兼容 Fiddler 等工具导出的带 BOM 的 UTF-8（否则 json.loads 会报 Unexpected UTF-8 BOM）
        text = raw.decode("utf-8-sig", errors="replace")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError("JSON 解析失败") from e

    if not isinstance(data, dict):
        raise ValueError("根节点必须为 JSON 对象")

    log = data.get("log")
    if not isinstance(log, dict):
        raise ValueError("缺少 log 对象")

    entries = log.get("entries")
    if not isinstance(entries, list):
        raise ValueError("缺少 log.entries 数组")

    # 过滤 CONNECT、静态资源，并按时间排序
    prepared = []
    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        req = entry.get("request")
        if not isinstance(req, dict):
            continue
        method = (req.get("method") or "").upper()
        if method == "CONNECT":
            continue
        if method not in ALLOWED_METHODS:
            continue
        url = (req.get("url") or "").strip()
        if not url:
            continue
        if _should_skip_static(url):
            continue
        t = _parse_started_time(entry)
        prepared.append((t, idx, entry))

    prepared.sort(key=lambda x: (x[0] is not None, x[0] or datetime.min, x[1]))

    results = []
    for sort_key in prepared:
        if len(results) >= max_requests:
            break
        entry = sort_key[2]
        req = entry.get("request") or {}
        method = (req.get("method") or "").upper()
        url = (req.get("url") or "").strip()

        headers_dict = _headers_to_dict(req.get("headers"))
        params = _query_string_to_params(req.get("queryString"))
        body = _parse_request_body(req.get("postData"), headers_dict)

        url_norm = normalize_url_for_match(url)
        started = entry.get("startedDateTime") or ""
        rid = f"har-{len(results)}"

        item = {
            "method": method,
            "url": url_norm,
            "url_full": url,
            "headers": headers_dict,
            "params": params,
            "body": body,
            "request_id": rid,
            "timestamp": started,
        }

        resp_obj = entry.get("response")
        if isinstance(resp_obj, dict):
            status = int(resp_obj.get("status") or 0) or 200
            rheaders = _headers_to_dict(resp_obj.get("headers"))
            content = resp_obj.get("content")
            rbody = _parse_response_body(content if isinstance(content, dict) else {}, rheaders)
            item["response"] = {
                "status_code": status,
                "headers": rheaders,
                "body": rbody,
            }
        else:
            item["response"] = None

        results.append(item)

    return results


def parse_har_bytes(data: bytes, max_requests=500):
    """供测试或内存字节调用的便捷封装。"""
    return parse_har_file(BytesIO(data), max_requests=max_requests)
