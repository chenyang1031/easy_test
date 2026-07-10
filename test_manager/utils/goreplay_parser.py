# -*- coding: utf-8 -*-
"""
GoReplay .gor 文件解析器

解析 GoReplay 录制的流量文件，提取 HTTP 请求。
文件格式参考: https://docs.goreplay.org/untitled/saving-and-replaying-from-file
"""
import gzip
import json
import re
from urllib.parse import parse_qs, urlparse

# GoReplay 请求分隔符
GOR_SEPARATOR = "\n🐵🙈🙉\n"

# 支持的 HTTP 方法
ALLOWED_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}


def normalize_url_for_match(full_url):
    """
    从完整 URL 提取 path + query，用于与 ApiAsset.url 匹配。
    ApiAsset.url 通常为 /api/xxx 形式。
    """
    if not full_url or not isinstance(full_url, str):
        return "/"
    full_url = full_url.strip()
    if not full_url.startswith(("http://", "https://", "/")):
        full_url = "/" + full_url
    parsed = urlparse(full_url)
    path = parsed.path or "/"
    if parsed.query:
        return f"{path}?{parsed.query}"
    return path


def _read_file_content(file_obj, gzip_mode=False):
    """读取文件内容，支持 gzip 解压。"""
    raw = file_obj.read()
    if gzip_mode:
        try:
            return gzip.decompress(raw).decode("utf-8", errors="replace")
        except (gzip.BadGzipFile, OSError):
            return raw.decode("utf-8", errors="replace")
    return raw.decode("utf-8", errors="replace")


def _parse_http_request(raw_http, request_id="", timestamp=""):
    """
    解析单条 HTTP 请求原始内容。
    返回 dict: method, url, url_full, headers, params, body, request_id, timestamp
    """
    if not raw_http or not isinstance(raw_http, str):
        return None

    # 规范化换行
    raw_http = raw_http.replace("\r\n", "\n").replace("\r", "\n")
    parts = raw_http.split("\n\n", 1)
    header_block = parts[0]
    body_raw = parts[1].strip() if len(parts) > 1 else ""

    header_lines = header_block.strip().split("\n")
    if not header_lines:
        return None

    # 解析请求行: METHOD /path HTTP/1.1
    first_line = header_lines[0].strip()
    match = re.match(r"^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+(\S+)\s+HTTP", first_line, re.I)
    if not match:
        return None

    method = match.group(1).upper()
    if method not in ALLOWED_METHODS:
        return None

    url_raw = match.group(2).strip()
    url_path = normalize_url_for_match(url_raw)

    # 解析 headers
    headers = {}
    for line in header_lines[1:]:
        idx = line.find(":")
        if idx > 0:
            key = line[:idx].strip()
            val = line[idx + 1 :].strip()
            if key:
                headers[key] = val

    # 从 URL 解析 query 参数
    parsed_url = urlparse(url_raw if "://" in url_raw or url_raw.startswith("/") else "/" + url_raw)
    params = {}
    if parsed_url.query:
        for k, v in parse_qs(parsed_url.query, keep_blank_values=True).items():
            params[k] = v[0] if len(v) == 1 else v

    # 解析 body
    body = None
    content_type = (headers.get("Content-Type") or "").lower()
    if body_raw:
        if "application/json" in content_type:
            try:
                body = json.loads(body_raw)
            except (json.JSONDecodeError, TypeError):
                body = {"_raw": body_raw}
        elif "application/x-www-form-urlencoded" in content_type or "multipart" in content_type:
            try:
                parsed = parse_qs(body_raw, keep_blank_values=True)
                body = {k: (v[0] if len(v) == 1 else v) for k, v in parsed.items()}
            except Exception:
                body = {"_raw": body_raw}
        else:
            body = {"_raw": body_raw}

    return {
        "method": method,
        "url": url_path,
        "url_full": url_raw,
        "headers": headers,
        "params": params,
        "body": body,
        "request_id": request_id,
        "timestamp": timestamp,
    }


def _parse_http_response(raw_http, request_id="", timestamp=""):
    """
    解析单条 HTTP 响应原始内容。
    payload_type=2 或 3 的格式与请求类似：首行 + headers + body。
    返回 dict: status_code, headers, body, request_id, timestamp
    """
    if not raw_http or not isinstance(raw_http, str):
        return None

    raw_http = raw_http.replace("\r\n", "\n").replace("\r", "\n")
    parts = raw_http.split("\n\n", 1)
    header_block = parts[0]
    body_raw = parts[1].strip() if len(parts) > 1 else ""

    header_lines = header_block.strip().split("\n")
    if not header_lines:
        return None

    # 解析响应行: HTTP/1.1 200 OK
    first_line = header_lines[0].strip()
    match = re.match(r"^HTTP/\d+\.\d+\s+(\d+)\s*.*", first_line, re.I)
    status_code = int(match.group(1)) if match else 200

    headers = {}
    for line in header_lines[1:]:
        idx = line.find(":")
        if idx > 0:
            key = line[:idx].strip()
            val = line[idx + 1 :].strip()
            if key:
                headers[key] = val

    body = None
    content_type = (headers.get("Content-Type") or "").lower()
    if body_raw:
        if "application/json" in content_type:
            try:
                body = json.loads(body_raw)
            except (json.JSONDecodeError, TypeError):
                body = {"_raw": body_raw}
        else:
            body = {"_raw": body_raw}

    return {
        "status_code": status_code,
        "headers": headers,
        "body": body,
        "request_id": request_id,
        "timestamp": timestamp,
    }


def _parse_single_record(record):
    """
    解析单条 GoReplay 记录。
    payload_type=1 返回请求 dict，payload_type=2/3 返回响应 dict，其他返回 None。
    """
    if not record or not isinstance(record, str):
        return None
    record = record.strip()
    if not record:
        return None

    lines = record.split("\n")
    if not lines:
        return None

    meta_parts = lines[0].split()
    if len(meta_parts) < 3:
        return None
    payload_type = meta_parts[0]
    request_id = meta_parts[1]
    timestamp = meta_parts[2]
    raw_http = "\n".join(lines[1:])

    if payload_type == "1":
        return _parse_http_request(raw_http, request_id=request_id, timestamp=timestamp)
    if payload_type in ("2", "3"):
        return ("response", _parse_http_response(raw_http, request_id=request_id, timestamp=timestamp))
    return None


def parse_gor_file(file_obj, gzip_mode=False, max_requests=500):
    """
    解析 .gor 或 .gor.gz 文件，返回请求列表（含匹配的响应数据）。

    :param file_obj: 文件对象（支持 read()）
    :param gzip_mode: 是否为 gzip 压缩
    :param max_requests: 最大解析请求数，防止大文件耗尽内存
    :return: list of dict，每个 dict 包含 method, url, headers, params, body 等，
             以及 response（若有）: status_code, headers, body
    """
    content = _read_file_content(file_obj, gzip_mode)
    records = content.split(GOR_SEPARATOR)

    # 第一遍：收集请求（保持文件顺序）和响应映射
    requests_ordered = []
    seen_request_ids = set()
    responses_by_id = {}

    for record in records:
        if len(requests_ordered) >= max_requests:
            break
        parsed = _parse_single_record(record)
        if parsed is None:
            continue
        if isinstance(parsed, tuple) and parsed[0] == "response":
            resp = parsed[1]
            if resp and resp.get("request_id"):
                rid = resp["request_id"]
                if rid not in responses_by_id:
                    responses_by_id[rid] = resp
        elif isinstance(parsed, dict):
            rid = parsed.get("request_id")
            if rid and rid not in seen_request_ids:
                seen_request_ids.add(rid)
                requests_ordered.append(parsed)

    # 为每个请求附加匹配的响应
    for req in requests_ordered:
        rid = req.get("request_id")
        resp = responses_by_id.get(rid) if rid else None
        if resp:
            req["response"] = {
                "status_code": resp.get("status_code", 200),
                "headers": resp.get("headers") or {},
                "body": resp.get("body"),
            }
        else:
            req["response"] = None

    return requests_ordered
