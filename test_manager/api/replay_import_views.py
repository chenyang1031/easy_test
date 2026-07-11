# -*- coding: utf-8 -*-
"""
回放导入 ViewSet（GoReplay .gor / HAR）

提供预览和确认导入接口，将录制的流量解析后创建测试场景，并自动匹配或新建 API 资产。
"""
from urllib.parse import parse_qs, urlparse

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from test_manager.models import ApiAsset, ApiGroup, ApiProject, TestScene, TestSceneNode
from test_manager.utils.goreplay_parser import parse_gor_file
from test_manager.utils.har_parser import parse_har_file
from test_manager.api.api_asset_sync_utils import build_asset_snapshot_for_node


def _can_access_project(user, project):
    if user.is_staff:
        return True
    return project.created_by_id == user.id


# 回放导入时忽略的请求头（HTTP 协议级/浏览器自动添加，无 API 测试价值）
_IGNORED_REQUEST_HEADERS = {
    "host", "content-length", "connection",
    "accept", "accept-encoding", "accept-language",
    "user-agent", "cache-control", "pragma",
    "upgrade-insecure-requests",
    "sec-fetch-site", "sec-fetch-mode", "sec-fetch-dest", "sec-fetch-user",
    "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform",
    "dnt", "sec-gpc",
    "origin", "referer",
}


def _filter_noise_headers(headers):
    """过滤掉浏览器/代理自动添加的噪音请求头。"""
    if not headers:
        return {}
    if isinstance(headers, dict):
        return {k: v for k, v in headers.items() if k.lower() not in _IGNORED_REQUEST_HEADERS}
    # list[dict] 格式（[{key, value}]）
    if isinstance(headers, list):
        return [h for h in headers if isinstance(h, dict) and h.get("key", "").lower() not in _IGNORED_REQUEST_HEADERS]
    return headers


def _match_api_asset(project_id, method, url_path):
    """
    按 Method + URL 匹配已有 API 资产。
    先尝试 path+query 精确匹配，再尝试 path 匹配（兼容仅存 path 的资产）。
    """
    method = (method or "GET").upper()
    url_path = (url_path or "/").strip()
    if not url_path.startswith("/"):
        url_path = "/" + url_path

    # 精确匹配 path+query
    asset = ApiAsset.objects.filter(
        project_id=project_id,
        method=method,
        url=url_path,
        is_deleted=False,
    ).first()
    if asset:
        return asset

    # 尝试 path-only 匹配（去除 query）
    parsed = urlparse(url_path)
    path_only = parsed.path or "/"
    if path_only != url_path:
        asset = ApiAsset.objects.filter(
            project_id=project_id,
            method=method,
            url=path_only,
            is_deleted=False,
        ).first()
        if asset:
            return asset
    return None


def _resolve_group(project, group_id):
    """解析目标分组。"""
    if not group_id:
        return None
    return get_object_or_404(ApiGroup, id=group_id, project=project)


def _replay_file_kind(upload_file):
    """
    根据文件名与 Content-Type 判断回放文件类型。
    返回 'gor' | 'har' | None。

    扩展名优先于 Content-Type，避免 .gor 被误判为 JSON/HAR。
    """
    fn = (getattr(upload_file, "name", "") or "").lower()
    ct = (getattr(upload_file, "content_type", "") or "").lower()
    if fn.endswith(".har"):
        return "har"
    if fn.endswith(".gor") or fn.endswith(".gz"):
        return "gor"
    if "application/json" in ct:
        return "har"
    return None


class ReplayImportViewSet(viewsets.ViewSet):
    """回放导入（GoReplay / HAR）：预览与确认。"""
    permission_classes = [permissions.IsAuthenticated]

    def _ensure_project_permission(self, project):
        if not _can_access_project(self.request.user, project):
            raise PermissionDenied("无权限操作该项目")

    def _preview_requests(self, requests, project_id):
        """为请求列表补充匹配状态，并包含响应数据。"""
        result = []
        for idx, req in enumerate(requests):
            method = req.get("method", "GET")
            url_path = req.get("url", "/")
            asset = _match_api_asset(project_id, method, url_path)
            resp = req.get("response")
            item = {
                "index": idx + 1,
                "method": method,
                "url": url_path,
                "url_full": req.get("url_full", url_path),
                "headers": req.get("headers", {}),
                "params": req.get("params", {}),
                "body": req.get("body"),
                "match_status": "matched" if asset else "unmatched",
                "api_asset_id": asset.id if asset else None,
                "api_asset_name": asset.name if asset else None,
            }
            if resp:
                item["response"] = {
                    "status_code": resp.get("status_code", 200),
                    "headers": resp.get("headers") or {},
                    "body": resp.get("body"),
                }
            else:
                item["response"] = None
            result.append(item)
        return result

    def preview(self, request):
        """
        POST /api/test-scenes/replay-import/preview/
        上传 .gor / .gor.gz / .har 等，解析并返回预览数据（含匹配状态）。
        """
        upload_file = request.FILES.get("file")
        project_id = request.data.get("project_id")
        if not upload_file:
            return Response(
                {"detail": "请上传 GoReplay(.gor/.gor.gz) 或 Fiddler 导出的 HAR(.har) 文件"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not project_id:
            return Response({"detail": "project_id 不能为空"}, status=status.HTTP_400_BAD_REQUEST)

        project = get_object_or_404(ApiProject, id=project_id)
        self._ensure_project_permission(project)

        kind = _replay_file_kind(upload_file)
        if not kind:
            return Response(
                {"detail": "仅支持 .gor、.gor.gz 或 .har（亦可为 application/json 的 HAR）"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if kind == "har":
                requests = parse_har_file(upload_file)
            else:
                filename = getattr(upload_file, "name", "") or ""
                gzip_mode = filename.lower().endswith(".gz")
                requests = parse_gor_file(upload_file, gzip_mode=gzip_mode)
        except ValueError as e:
            msg = str(e) or "格式错误"
            if kind == "har":
                detail = f"不是有效的 HAR 文件：{msg[:200]}"
            else:
                detail = f"不是有效的 GoReplay 文件：{msg[:200]}"
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            if kind == "har":
                detail = f"无法解析 HAR：{str(e)[:200]}"
            else:
                detail = f"无法解析，请确认为 GoReplay .gor 格式：{str(e)[:200]}"
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        if not requests:
            return Response(
                {"detail": "未解析到有效 HTTP 请求"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        enriched = self._preview_requests(requests, project.id)
        matched_count = sum(1 for r in enriched if r["match_status"] == "matched")
        unmatched_count = len(enriched) - matched_count

        return Response({
            "total_requests": len(enriched),
            "matched_count": matched_count,
            "unmatched_count": unmatched_count,
            "requests": enriched,
        })

    def confirm(self, request):
        """
        POST /api/test-scenes/replay-import/confirm/
        确认导入，创建场景与节点，未匹配接口自动新建 ApiAsset。
        """
        project_id = request.data.get("project_id")
        group_id = request.data.get("group_id")
        scene_name = request.data.get("scene_name") or f"从回放导入-{timezone.now().strftime('%Y%m%d%H%M')}"
        scene_description = request.data.get("scene_description") or "来自 GoReplay 流量"
        selected_indices = request.data.get("selected_indices")  # 用户勾选的 index 列表，空则全部
        requests_data = request.data.get("requests") or []

        if not project_id:
            return Response({"detail": "project_id 不能为空"}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(requests_data, list):
            return Response({"detail": "requests 必须为数组"}, status=status.HTTP_400_BAD_REQUEST)

        project = get_object_or_404(ApiProject, id=project_id)
        self._ensure_project_permission(project)
        target_group = _resolve_group(project, group_id)

        # 筛选要导入的请求
        if selected_indices and isinstance(selected_indices, list):
            index_set = {int(i) for i in selected_indices if str(i).isdigit()}
            selected = [r for r in requests_data if isinstance(r, dict) and r.get("index") in index_set]
        else:
            selected = [r for r in requests_data if isinstance(r, dict)]

        if not selected:
            return Response({"detail": "请至少勾选一条请求导入"}, status=status.HTTP_400_BAD_REQUEST)

        # 按 index 排序
        selected.sort(key=lambda x: x.get("index", 0))

        assets_created = 0
        assets_matched = 0

        with transaction.atomic():
            scene = TestScene.objects.create(
                project=project,
                name=scene_name[:150],
                description=scene_description[:500] or "",
                variables={},
                runtime_config={},
                is_active=True,
                created_by=request.user,
            )

            for idx, req in enumerate(selected):
                method = (req.get("method") or "GET").upper()
                url_path = (req.get("url") or "/").strip()
                if not url_path.startswith("/"):
                    url_path = "/" + url_path

                # 从 URL 中剥离查询参数，提取干净 path 用于资产存储
                _parsed_url = urlparse(url_path)
                clean_url = _parsed_url.path or "/"
                if not clean_url.startswith("/"):
                    clean_url = "/" + clean_url
                # 将 URL 中的查询参数与 HAR 解析的 params 合并
                _url_query_params = {}
                if _parsed_url.query:
                    for k, v in parse_qs(_parsed_url.query, keep_blank_values=True).items():
                        _url_query_params[k] = v[0] if len(v) == 1 else v
                _har_params = req.get("params") or {}
                _merged_params = {**_url_query_params, **_har_params}

                resp = req.get("response")
                expected_status = 200
                expected_headers = {}
                expected_body = None
                if resp:
                    expected_status = resp.get("status_code", 200)
                    expected_headers = resp.get("headers") or {}
                    expected_body = resp.get("body")
                    if isinstance(expected_body, dict) and "_raw" in expected_body:
                        expected_body = None  # 非 JSON 响应体不存储

                asset = _match_api_asset(project.id, method, url_path)

                # ----- 匹配到已有资产：节点配置优先使用 API 资产数据 -----
                if asset:
                    har_headers = _filter_noise_headers(req.get("headers") or {})

                    # --- request_headers: 资产数据优先，空则 HAR 回填 ---
                    if asset.request_headers:
                        raw = asset.request_headers
                        if isinstance(raw, list):
                            asset_headers = {}
                            for item in raw:
                                if isinstance(item, dict) and item.get("key"):
                                    asset_headers[item["key"]] = item.get("value", "")
                            if asset_headers != asset.request_headers:
                                asset.request_headers = asset_headers
                        else:
                            asset_headers = raw
                    else:
                        asset_headers = har_headers
                        # 回填资产
                        if har_headers:
                            asset.request_headers = har_headers
                            asset.save(update_fields=["request_headers"])

                    node_headers = asset_headers

                    # --- request_params: 资产数据优先，空则 HAR 回填 ---
                    # 仅保留执行需要的字段（value / type），去除 desc / required / default / validation 等对执行无影响的元数据
                    asset_params = asset.request_params
                    if asset_params:
                        if isinstance(asset_params, list):
                            node_params = {}
                            for item in asset_params:
                                if isinstance(item, dict) and item.get("key"):
                                    node_params[item["key"]] = {
                                        "value": item.get("value", ""),
                                        "type": item.get("type", "string"),
                                    }
                        else:
                            node_params = asset_params if isinstance(asset_params, dict) else {}
                    else:
                        node_params = _merged_params

                    # --- request_body: 资产数据优先，空则 HAR 回填 ---
                    asset_body = asset.request_body
                    if asset_body and isinstance(asset_body, dict):
                        node_body = asset_body
                    else:
                        node_body = req.get("body") if isinstance(req.get("body"), dict) else {}

                    # response_schema 回填：资产为空且有 HAR JSON 响应体时补上（支持 dict/list 等）
                    if not asset.response_schema and expected_body is not None:
                        if not (isinstance(expected_body, dict) and "_raw" in expected_body):
                            asset.response_schema = expected_body
                            asset.save(update_fields=["response_schema"])

                else:
                    node_headers = _filter_noise_headers(req.get("headers") or {})
                    node_params = _merged_params
                    node_body = req.get("body") if isinstance(req.get("body"), dict) else {}

                if not asset:
                    # 新建 ApiAsset，若有响应体可推断 response_schema
                    name = req.get("api_asset_name") or f"{method} {clean_url}"
                    if len(name) > 150:
                        name = name[:147] + "..."
                    body = req.get("body")
                    body_format = "json"
                    if isinstance(body, dict) and "_raw" in body:
                        body_format = "form-data" if "form" in str(body).lower() else "json"
                    elif isinstance(body, dict):
                        # 修复：没有 _raw 的干净 dict 可能是 form-data（HAR 解析器已解析好），
                        # 不能仅靠 isinstance 判断为 JSON，需回查 Content-Type
                        req_ct = ((req.get("headers") or {}).get("Content-Type") or "").lower()
                        body_format = "form-data" if ("form-data" in req_ct or "x-www-form-urlencoded" in req_ct) else "json"

                    response_schema = {}
                    if isinstance(expected_body, dict) and "_raw" not in expected_body:
                        response_schema = expected_body

                    asset = ApiAsset.objects.create(
                        project=project,
                        group=target_group,
                        name=name,
                        method=method,
                        url=clean_url,
                        request_headers=_filter_noise_headers(req.get("headers") or {}),
                        request_params=[{"key": k, "value": v} for k, v in _merged_params.items()] if isinstance(_merged_params, dict) else _merged_params,
                        request_body_format=body_format,
                        request_body=body if isinstance(body, dict) else {},
                        response_schema=response_schema,
                        status=ApiAsset.STATUS_ACTIVE,
                        source=ApiAsset.SOURCE_GOREPLAY,
                        external_id="",
                        created_by=request.user,
                    )
                    assets_created += 1
                else:
                    # 匹配到已有资产，使用资产的 response_schema 作为预期响应体（优先于 HAR 录制值）
                    if asset.response_schema:
                        expected_body = asset.response_schema
                    assets_matched += 1

                node_key = f"node_replay_{idx}_{int(timezone.now().timestamp())}"
                now = timezone.now()
                # 有请求参数且无请求体时，参数展示为键值对；否则为 JSON
                _has_params = bool(node_params)
                _has_body = bool(node_body)
                node_param_type = "form-data" if _has_params and not _has_body else "json"
                TestSceneNode.objects.create(
                    scene=scene,
                    api_asset=asset,
                    node_key=node_key[:80],
                    name=asset.name,
                    description=asset.interface_desc or "",
                    method=asset.method or "",
                    request_headers=node_headers,
                    request_params=node_params,
                    request_body=node_body,
                    param_type=node_param_type,
                    body_type=asset.request_body_format or "json",
                    assert_rules=[],
                    extract_rules=[],
                    expected_status_code=expected_status,
                    expected_response_headers=expected_headers,
                    expected_response_body=expected_body,
                    on_failed=TestSceneNode.ON_FAILED_CONTINUE,
                    sort=idx,
                    is_enabled=True,
                    api_synced_at=now,
                    api_sync_snapshot=build_asset_snapshot_for_node(asset),
                )

        return Response({
            "scene_id": scene.id,
            "scene_name": scene.name,
            "nodes_created": len(selected),
            "assets_created": assets_created,
            "assets_matched": assets_matched,
        }, status=status.HTTP_201_CREATED)
