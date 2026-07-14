import copy
from datetime import timedelta
from math import ceil

from django.db import transaction
from django.db.models import Count, OuterRef, Q, Subquery
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.files.storage import default_storage
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from test_manager.env_variables_compat import variables_for_runtime
from test_manager.models import ApiAsset, ApiGroup, ApiProject, Environment, TestScene, TestSceneExecution, TestSceneNode, TestSceneNodeSyncLog, SceneDownloadedFile
from test_manager.httprunner_executor import get_debugtalk_functions_meta
from .scene_engine import execute_scene
from .api_asset_sync_utils import (
    compute_node_api_diff,
    get_node_snapshot_for_rollback,
    build_asset_snapshot_for_node,
    _normalize_kv_payload_to_dict,
    _normalize_formdata_body_to_dict,
)
from .serializers import (
    ApiAssetLiteSerializer,
    ApiGroupSerializer,
    TestSceneExecutionListSerializer,
    TestSceneExecutionSerializer,
    TestSceneNodeSerializer,
    TestSceneSerializer,
    SceneDownloadedFileSerializer,
)
from .pagination import StandardResultsSetPagination


def _touch_scene_updated_at(scene):
    """节点变更时同步更新父场景的 updated_at。"""
    TestScene.objects.filter(pk=scene.pk).update(updated_at=timezone.now())


def _flatten_paths(payload, prefix, depth=0):
    if depth > 5:
        return []
    if payload is None:
        return [prefix]
    if isinstance(payload, dict):
        if not payload:
            return [prefix]
        paths = []
        for key, value in payload.items():
            paths.extend(_flatten_paths(value, f"{prefix}.{key}", depth + 1))
        return paths
    if isinstance(payload, list):
        if not payload:
            return [prefix]
        return _flatten_paths(payload[0], f"{prefix}.0", depth + 1)
    return [prefix]


def _can_access_project(user, project):
    if user.is_staff:
        return True
    return project.created_by_id == user.id


def _project_queryset_for_user(user):
    if user.is_staff:
        return ApiProject.objects.all()
    return ApiProject.objects.filter(created_by=user)


class TestSceneViewSet(viewsets.ModelViewSet):
    queryset = TestScene.objects.select_related("project", "created_by").filter(is_deleted=False)
    serializer_class = TestSceneSerializer
    permission_classes = [permissions.IsAuthenticated]

    def _ensure_project_permission(self, project):
        if not _can_access_project(self.request.user, project):
            raise PermissionDenied("无权限操作该项目下场景")

    def get_queryset(self):
        latest_exec = TestSceneExecution.objects.filter(scene=OuterRef("pk")).order_by("-created_at")
        queryset = (
            TestScene.objects.select_related("project", "created_by")
            .filter(is_deleted=False)
            .annotate(node_count=Count("nodes", filter=Q(nodes__is_deleted=False)))
            .annotate(latest_execution_status=Subquery(latest_exec.values("status")[:1]))
            .annotate(latest_execution_started_at=Subquery(latest_exec.values("started_at")[:1]))
            .annotate(latest_execution_duration_ms=Subquery(latest_exec.values("duration_ms")[:1]))
            .annotate(latest_execution_error_message=Subquery(latest_exec.values("error_message")[:1]))
        )
        if not self.request.user.is_staff:
            queryset = queryset.filter(project__in=_project_queryset_for_user(self.request.user))
        params = self.request.query_params
        project_id = params.get("project")
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        group = params.get("group")
        if group:
            queryset = queryset.filter(group_id=group)
        is_active = params.get("is_active")
        if is_active in {"true", "1"}:
            queryset = queryset.filter(is_active=True)
        if is_active in {"false", "0"}:
            queryset = queryset.filter(is_active=False)
        q = params.get("q")
        if q:
            queryset = queryset.filter(Q(name__icontains=q) | Q(description__icontains=q))
        category = params.get("category")
        if category:
            queryset = queryset.filter(category=category)
        exec_status = params.get("latest_execution_status")
        if exec_status:
            if exec_status == "never":
                queryset = queryset.filter(latest_execution_status__isnull=True)
            else:
                queryset = queryset.filter(latest_execution_status=exec_status)
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

        # 预加载节点与 api_asset，用于序列化器计算 api_updated
        scene_ids = [item.id for item in items]
        from collections import defaultdict
        prefetched_nodes = defaultdict(list)
        if scene_ids:
            nodes = TestSceneNode.objects.filter(
                scene_id__in=scene_ids, is_deleted=False
            ).select_related('api_asset')
            for node in nodes:
                prefetched_nodes[node.scene_id].append(node)

        context = self.get_serializer_context()
        context['_prefetched_nodes'] = dict(prefetched_nodes)
        serializer = self.get_serializer(items, many=True, context=context)
        return Response(
            {
                "count": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "results": serializer.data,
            }
        )

    def perform_create(self, serializer):
        project = serializer.validated_data["project"]
        self._ensure_project_permission(project)
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        instance = self.get_object()
        project = serializer.validated_data.get("project", instance.project)
        self._ensure_project_permission(project)
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        scene = self.get_object()
        self._ensure_project_permission(scene.project)
        scene.is_deleted = True
        scene.save(update_fields=["is_deleted", "updated_at"])
        scene.nodes.filter(is_deleted=False).update(is_deleted=True, updated_at=timezone.now())
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="designer-init")
    def designer_init(self, request, pk=None):
        target_id = pk
        # 直接查询场景，避免 get_queryset 中 5 个冗余注解子查询
        scene = get_object_or_404(
            TestScene.objects.select_related("project", "created_by"),
            id=target_id,
            is_deleted=False,
        )
        self._ensure_project_permission(scene.project)
        # 预加载 api_asset.group 避免节点序列化中的 N+1
        nodes = scene.nodes.filter(is_deleted=False).select_related(
            "api_asset", "api_asset__group", "environment"
        ).order_by("sort", "id")
        # 一次性加载所有分组，Python 组树，避免 ApiGroupSerializer 递归 N+1
        all_groups = list(
            ApiGroup.objects.filter(project_id=scene.project_id)
            .order_by("sort_order", "id")
            .values("id", "parent", "name", "sort_order")
        )
        id_map = {g["id"]: {**g, "children": []} for g in all_groups}
        roots = []
        for g in id_map.values():
            pid = g["parent"]
            if pid and pid in id_map:
                id_map[pid]["children"].append(g)
            else:
                roots.append(g)
        assets = ApiAsset.objects.filter(project_id=scene.project_id, is_deleted=False).only("id", "name", "group_id")
        platform_project_id = getattr(scene.project, "platform_project_id", None)
        envs = []
        if platform_project_id:
            from django.db.models import Q
            env_qs = Environment.objects.filter(
                Q(project_id=platform_project_id) | Q(is_global_visible=True)
            ).order_by("name")
            envs = [
                {
                    "id": e.id,
                    "name": e.name,
                    "base_url": e.base_url,
                    "category": getattr(e, "category", "default"),
                    # 供场景编排变量选择器列出 {{env.xxx}}，与前端 variableOptions 一致
                    "variables": e.variables or {},
                }
                for e in env_qs
            ]
        return Response(
            {
                "scene": TestSceneSerializer(scene, context={
                    '_prefetched_nodes': {scene.id: list(nodes)}
                }).data,
                "nodes": TestSceneNodeSerializer(nodes, many=True).data,
                "groups": roots,
                "api_assets": ApiAssetLiteSerializer(assets, many=True).data,
                "environments": envs,
                "debugtalk_functions": get_debugtalk_functions_meta(),
            }
        )

    @action(detail=True, methods=["post"])
    def copy(self, request, pk=None):
        scene = self.get_object()
        self._ensure_project_permission(scene.project)
        new_name = str(request.data.get("name") or f"{scene.name}-副本").strip()[:150]
        copied = TestScene.objects.create(
            project=scene.project,
            group=scene.group,
            name=new_name,
            category=scene.category,
            description=scene.description,
            variables=scene.variables or {},
            runtime_config=scene.runtime_config or {},
            is_active=scene.is_active,
            created_by=request.user,
        )
        old_nodes = scene.nodes.select_related("api_asset").filter(is_deleted=False).order_by("sort", "id")
        for node in old_nodes:
            TestSceneNode.objects.create(
                scene=copied,
                api_asset=node.api_asset,
                node_key=f"{node.node_key}_copy",
                name=node.name,
                description=node.description,
                method=node.method or node.effective_method,
                request_headers=node.request_headers or {},
                request_params=node.request_params or {},
                request_body=node.request_body or {},
                param_type=node.param_type or "json",
                body_type=node.body_type or "json",
                assert_rules=node.assert_rules or [],
                extract_rules=node.extract_rules or [],
                expected_status_code=node.expected_status_code,
                expected_response_headers=node.expected_response_headers or {},
                expected_response_body=node.expected_response_body,
                timeout=node.timeout,
                on_failed=node.on_failed,
                sort=node.sort,
                is_enabled=node.is_enabled,
                environment=node.environment,
                custom_base_url=node.custom_base_url or "",
                api_synced_at=node.api_synced_at,
                api_sync_snapshot=node.api_sync_snapshot or {},
                pre_request_script=node.pre_request_script or "",
                script_timeout=node.script_timeout,
            )
        data = self.get_serializer(copied).data
        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def execute(self, request, pk=None):
        scene = self.get_object()
        self._ensure_project_permission(scene.project)
        run_mode = str(request.data.get("run_mode") or TestSceneExecution.RUN_MODE_ALL).lower()
        node_id = request.data.get("node_id")
        environment_id = request.data.get("environment_id")
        target_node = None
        if run_mode == TestSceneExecution.RUN_MODE_SINGLE:
            if not node_id:
                return Response({"detail": "单步执行需传 node_id"}, status=status.HTTP_400_BAD_REQUEST)
            target_node = get_object_or_404(TestSceneNode, id=node_id, scene=scene)
            if not target_node.is_enabled:
                return Response({"detail": "目标节点已禁用，无法单步执行"}, status=status.HTTP_400_BAD_REQUEST)
        elif run_mode != TestSceneExecution.RUN_MODE_ALL:
            return Response({"detail": "run_mode仅支持 all/single"}, status=status.HTTP_400_BAD_REQUEST)

        if not environment_id:
            return Response(
                {"detail": "请先选择运行环境", "error_code": "environment_required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        env_obj = Environment.objects.filter(id=environment_id).first()
        if not env_obj:
            return Response({"detail": "运行环境不存在"}, status=status.HTTP_400_BAD_REQUEST)
        platform_project_id = getattr(scene.project, "platform_project_id", None)
        if platform_project_id and env_obj.project_id != platform_project_id:
            return Response(
                {"detail": "运行环境不属于当前场景绑定的项目"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        runtime_config = dict(scene.runtime_config or {})
        runtime_config["environment_id"] = int(environment_id)
        runtime_config["base_url"] = env_obj.base_url or ""

        try:
            execution = execute_scene(
                scene=scene,
                operator=request.user,
                run_mode=run_mode,
                target_node=target_node,
                runtime_config_override=runtime_config,
            )
        except Exception as exc:
            return Response(
                {
                    "detail": "场景执行失败",
                    "error_code": "scene_execute_failed",
                    "error_message": str(exc),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(TestSceneExecutionSerializer(execution).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="mark-execution-timeout")
    def mark_execution_timeout(self, request, pk=None):
        """客户端请求超时时，将场景下仍在 running 的最新执行标记为失败，避免状态一直显示「执行中」。"""
        scene = self.get_object()
        self._ensure_project_permission(scene.project)
        latest = (
            scene.executions.filter(status=TestSceneExecution.STATUS_RUNNING)
            .order_by("-started_at")
            .first()
        )
        if latest:
            latest.status = TestSceneExecution.STATUS_FAILED
            latest.error_message = "客户端请求超时，执行已标记为失败"
            latest.finished_at = timezone.now()
            latest.save(update_fields=["status", "error_message", "finished_at"])
        return Response({"detail": "已处理" if latest else "无正在执行的记录"})

    @action(detail=True, methods=["get"], url_path="executions")
    def executions(self, request, pk=None):
        scene = self.get_object()
        self._ensure_project_permission(scene.project)
        # 限制返回条数，避免序列化全部历史记录的 node_results 大 JSON
        limit = request.query_params.get("limit")
        try:
            limit = max(1, min(int(limit), 100)) if limit is not None else 20
        except (TypeError, ValueError):
            limit = 20
        queryset = scene.executions.select_related(
            "target_node", "created_by", "environment",
            "scene", "scene__project", "scene__project__platform_project",
        ).order_by("-created_at")[:limit]
        serializer = TestSceneExecutionSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="variable-fields-preview")
    def variable_fields_preview(self, request, pk=None):
        scene = self.get_object()
        self._ensure_project_permission(scene.project)
        runtime_config = scene.runtime_config or {}
        # 优先使用请求参数中的 environment_id（编辑时未保存的选中环境），否则用场景已保存的配置
        env_id = request.query_params.get("environment_id")
        if env_id is not None:
            try:
                env_id = int(env_id)
            except (TypeError, ValueError):
                env_id = None
        if env_id is None:
            env_id = runtime_config.get("environment_id")
        env_data = {}
        if env_id:
            env_obj = Environment.objects.filter(id=env_id).first()
            if env_obj:
                env_data = variables_for_runtime(env_obj.variables or {})

        env_paths = _flatten_paths(env_data, "env")
        scene_var_paths = _flatten_paths(scene.variables or {}, "scene")

        current_node_id = request.query_params.get("current_node_id")
        current_sort = None
        if current_node_id:
            try:
                row = scene.nodes.filter(
                    id=int(current_node_id), is_deleted=False
                ).values_list("sort", flat=True).first()
                if row is not None:
                    current_sort = row
            except (TypeError, ValueError):
                pass

        node_paths = []
        for node in scene.nodes.filter(is_deleted=False).order_by("sort", "id"):
            if current_sort is not None and (node.sort or 0) >= current_sort:
                continue
            node_key = node.node_key or f"node_{node.id}"
            node_paths.extend(
                [
                    f"{node_key}.response.data.xxx",
                    f"{node_key}.response.status_code",
                    f"{node_key}.response.headers.xxx",
                ]
            )
            if isinstance(node.extract_rules, dict):
                for key in list(node.extract_rules.keys())[:10]:
                    node_paths.append(f"{node_key}.extracted.{key}")
            elif isinstance(node.extract_rules, list):
                for rule in (node.extract_rules or [])[:10]:
                    if isinstance(rule, dict) and rule.get("name"):
                        node_paths.append(f"{node_key}.extracted.{rule['name']}")

        unique_paths = sorted(set(env_paths + scene_var_paths + node_paths))
        return Response(
            {
                "execution_id": None,
                "count": len(unique_paths),
                "paths": unique_paths,
                "sample": unique_paths[:200],
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="sync-all-nodes")
    def sync_all_nodes(self, request, pk=None):
        """一键同步场景中所有节点的 API 资产更新（基础信息 + 参数 + 请求头）。"""
        scene = self.get_object()
        self._ensure_project_permission(scene.project)

        nodes = list(
            scene.nodes.filter(is_deleted=False, api_asset__isnull=False)
            .select_related("api_asset")
            .order_by("sort", "id")
        )
        if not nodes:
            return Response({"detail": "场景中没有关联 API 资产的节点"}, status=status.HTTP_400_BAD_REQUEST)

        # 筛选 stale 节点
        stale_nodes = []
        for node in nodes:
            asset = node.api_asset
            if asset.is_deleted:
                continue
            if node.api_synced_at and asset.updated_at <= node.api_synced_at:
                continue
            stale_nodes.append(node)

        if not stale_nodes:
            return Response({"synced_count": 0, "nodes": []})

        results = []
        with transaction.atomic():
            for node in stale_nodes:
                asset = node.api_asset
                diff = compute_node_api_diff(node)
                if not diff or not diff.get("has_diff"):
                    continue

                before_snapshot = get_node_snapshot_for_rollback(node)
                synced_basic = False
                synced_params = False
                synced_headers = False
                update_fields = set()
                node_diffs = diff.get("diffs") or {}

                # 1. sync basic (URL / Method)
                basic_diff = node_diffs.get("basic") or {}
                if basic_diff.get("url", {}).get("changed") or basic_diff.get("method", {}).get("changed"):
                    synced_basic = True

                # 2. sync params — 完整覆盖
                req_diff = node_diffs.get("request") or {}
                params_changed = bool(
                    req_diff.get("params_added")
                    or req_diff.get("params_removed")
                )
                if params_changed:
                    source = asset.request_params or {}
                    if isinstance(source, list):
                        target = {}
                        for item in source:
                            if isinstance(item, dict):
                                k = str(item.get("key") or item.get("name") or "").strip()
                                if k:
                                    target[k] = copy.deepcopy(item)
                    else:
                        target = copy.deepcopy(source) if isinstance(source, dict) else {}
                    node.request_params = target
                    update_fields.add("request_params")
                    synced_params = True

                # 3. sync headers — 完整覆盖
                headers_changed = bool(
                    req_diff.get("headers_added")
                    or req_diff.get("headers_removed")
                    or req_diff.get("headers_value_changed")
                )
                if headers_changed:
                    source = asset.request_headers or {}
                    if isinstance(source, list):
                        target = {}
                        for item in source:
                            if isinstance(item, dict):
                                k = str(item.get("key") or item.get("name") or "").strip()
                                if k:
                                    target[k] = copy.deepcopy(item)
                    else:
                        target = copy.deepcopy(source) if isinstance(source, dict) else {}
                    node.request_headers = target
                    update_fields.add("request_headers")
                    synced_headers = True

                # 有任何同步动作则更新同步时间戳
                if synced_basic or synced_params or synced_headers:
                    node.api_synced_at = timezone.now()
                    node.api_sync_snapshot = build_asset_snapshot_for_node(asset)
                    update_fields.update(["api_synced_at", "api_sync_snapshot", "updated_at"])
                    node.save(update_fields=list(update_fields))

                    after_snapshot = get_node_snapshot_for_rollback(node)
                    TestSceneNodeSyncLog.objects.create(
                        node=node,
                        sync_type=TestSceneNodeSyncLog.SYNC_BASIC,
                        before_snapshot=before_snapshot,
                        after_snapshot=after_snapshot,
                        node_snapshot_before=before_snapshot,
                        node_snapshot_after=after_snapshot,
                        created_by=request.user,
                    )

                results.append({
                    "node_id": node.id,
                    "node_name": node.name,
                    "synced_basic": synced_basic,
                    "synced_params": synced_params,
                    "synced_headers": synced_headers,
                })

            if results:
                _touch_scene_updated_at(scene)

        return Response({"synced_count": len(results), "nodes": results})


class TestSceneNodeViewSet(viewsets.ModelViewSet):
    queryset = TestSceneNode.objects.select_related("scene", "scene__project", "api_asset").filter(
        is_deleted=False,
        scene__is_deleted=False,
    )
    serializer_class = TestSceneNodeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def _ensure_scene_permission(self, scene):
        if not _can_access_project(self.request.user, scene.project):
            raise PermissionDenied("无权限操作该项目下节点")

    def get_queryset(self):
        queryset = TestSceneNode.objects.select_related("scene", "scene__project", "api_asset").filter(
            is_deleted=False,
            scene__is_deleted=False,
        )
        if not self.request.user.is_staff:
            queryset = queryset.filter(scene__project__in=_project_queryset_for_user(self.request.user))
        scene_id = self.request.query_params.get("scene_id")
        if scene_id:
            queryset = queryset.filter(scene_id=scene_id, scene__is_deleted=False)
        fields = [item.strip() for item in str(self.request.query_params.get("fields") or "").split(",") if item.strip()]
        if fields:
            self._requested_fields = fields
        return queryset.order_by("sort", "id")

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        fields = getattr(self, "_requested_fields", None)
        if not fields:
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        allowed = {
            "id": "id",
            "name": "name",
            "method": "method",
            "is_enabled": "is_enabled",
            "sort": "sort",
        }
        invalid = [field for field in fields if field not in allowed]
        if invalid:
            return Response({"detail": f"fields包含不支持字段: {', '.join(invalid)}"}, status=status.HTTP_400_BAD_REQUEST)
        values_fields = [allowed[field] for field in fields]
        payload = []
        for row in queryset.values(*values_fields):
            item = {}
            for field in fields:
                source_key = allowed[field]
                item[field] = row.get(source_key)
            payload.append(item)
        return Response(payload)

    def _normalize_node_payload(self, payload):
        if not isinstance(payload, dict):
            return payload
        normalized = dict(payload)
        alias_to_target = {
            "api": "api_asset",
            "enabled": "is_enabled",
            "headers": "request_headers",
            "params": "request_params",
            "body": "request_body",
            "assertions": "assert_rules",
            "sort_order": "sort",
        }
        for alias, target in alias_to_target.items():
            if alias in normalized and target not in normalized:
                normalized[target] = normalized.get(alias)
        return normalized

    def create(self, request, *args, **kwargs):
        payload = self._normalize_node_payload(request.data)
        if not isinstance(payload, dict) or not payload:
            return Response({"detail": "请求体不能为空"}, status=status.HTTP_400_BAD_REQUEST)
        scene_id = payload.get("scene") or payload.get("scene_id")
        api_asset_id = payload.get("api_asset") or payload.get("api_asset_id")
        if scene_id and api_asset_id and not payload.get("name"):
            scene_obj = TestScene.objects.filter(id=scene_id, is_deleted=False).first()
            api_obj = ApiAsset.objects.filter(id=api_asset_id, is_deleted=False).first()
            if not scene_obj or not api_obj:
                return Response({"detail": "scene_id或api_asset_id无效"}, status=status.HTTP_400_BAD_REQUEST)
            payload.setdefault("node_key", f"node_{int(timezone.now().timestamp())}_{api_obj.id}")
            payload.setdefault("name", api_obj.name)
            payload.setdefault("description", api_obj.interface_desc or "")
            # 兼容 ApiAsset 的 list/array 格式 request_headers，转为 TestSceneNode 的 dict 格式
            raw_headers = api_obj.request_headers
            if raw_headers is None:
                raw_headers = {}
            elif isinstance(raw_headers, list):
                raw_headers = _normalize_kv_payload_to_dict(raw_headers)
            payload.setdefault("request_headers", raw_headers)
            # 兼容 ApiAsset 的 list 格式 request_params，转为 TestSceneNode 的 dict 格式
            raw_params = api_obj.request_params
            if raw_params is None:
                raw_params = {}
            elif isinstance(raw_params, list):
                raw_params = _normalize_kv_payload_to_dict(raw_params)
            payload.setdefault("request_params", raw_params)
            # 兼容 ApiAsset 的数组格式 request_body（form-data），转为 TestSceneNode 的 dict 格式
            raw_body = api_obj.request_body
            if raw_body is None:
                raw_body = {}
            elif isinstance(raw_body, list):
                api_body_format = getattr(api_obj, "request_body_format", "json") or "json"
                if api_body_format == "form-data":
                    # form-data 数组 [{key, type, value, ...}] → dict {key: {value, type, ...}}
                    raw_body = _normalize_formdata_body_to_dict(raw_body)
                else:
                    # 非 form-data 的 list 格式用基础转换保留值
                    raw_body = _normalize_kv_payload_to_dict(raw_body)
            payload.setdefault("request_body", raw_body)
            # 如果 API 资产同时有 params 和 body（存量数据兼容），按请求方法优先保留其一
            resolved_params = payload.get("request_params") or {}
            resolved_body = payload.get("request_body") or {}
            if bool(resolved_params) and bool(resolved_body):
                method = str(getattr(api_obj, "method", "") or "").upper()
                if method in ("GET", "DELETE", "HEAD", "OPTIONS"):
                    payload["request_body"] = {}
                else:
                    payload["request_params"] = {}
            payload.setdefault("expected_response_body", api_obj.response_schema or {})
            payload.setdefault("assert_rules", [])
            payload.setdefault("extract_rules", [])
            payload.setdefault("expected_status_code", 200)
            payload.setdefault("timeout", 30)
            payload.setdefault("on_failed", TestSceneNode.ON_FAILED_CONTINUE)
            payload.setdefault("method", api_obj.method or "")
            max_sort = scene_obj.nodes.filter(is_deleted=False).order_by("-sort").values_list("sort", flat=True).first()
            payload.setdefault("sort", (max_sort if max_sort is not None else -1) + 1)
            payload.setdefault("is_enabled", True)
            api_body_format = getattr(api_obj, "request_body_format", "json") or "json"
            payload.setdefault("body_type", api_body_format)
            # param_type 基于冲突解决后节点实际存储的数据判定，而非原始 API 资产
            has_params_after = bool(payload.get("request_params"))
            has_body_after = bool(payload.get("request_body"))
            payload.setdefault(
                "param_type",
                "form-data" if has_params_after and not has_body_after else "json"
            )
        serializer = self.get_serializer(data=payload)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        payload = self._normalize_node_payload(request.data)
        if isinstance(payload, dict):
            assert_rules = payload.get("assert_rules")
            if assert_rules is not None and not isinstance(assert_rules, (list, dict)):
                return Response({"detail": "assert_rules 格式错误"}, status=status.HTTP_400_BAD_REQUEST)
            if isinstance(assert_rules, list) and len(assert_rules) > 50:
                return Response({"detail": "断言规则最多 50 条"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(instance, data=payload, partial=partial)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            self.perform_update(serializer)
        return Response(serializer.data)

    def perform_create(self, serializer):
        scene = serializer.validated_data["scene"]
        self._ensure_scene_permission(scene)
        api_asset = serializer.validated_data.get("api_asset")
        if api_asset and api_asset.project_id != scene.project_id:
            raise PermissionDenied("节点接口必须与场景属于同一项目")
        serializer.save()
        node = serializer.instance
        if node.api_asset_id:
            asset = getattr(node, "api_asset", None) or ApiAsset.objects.filter(pk=node.api_asset_id, is_deleted=False).first()
            if asset:
                now = timezone.now()
                node.api_synced_at = now
                node.api_sync_snapshot = build_asset_snapshot_for_node(asset)
                node.save(update_fields=["api_synced_at", "api_sync_snapshot", "updated_at"])
        _touch_scene_updated_at(scene)

    def perform_update(self, serializer):
        node = self.get_object()
        scene = serializer.validated_data.get("scene", node.scene)
        self._ensure_scene_permission(scene)
        api_asset = serializer.validated_data.get("api_asset", node.api_asset)
        if api_asset and api_asset.project_id != scene.project_id:
            raise PermissionDenied("节点接口必须与场景属于同一项目")
        serializer.save()
        _touch_scene_updated_at(scene)

    def destroy(self, request, *args, **kwargs):
        node = self.get_object()
        self._ensure_scene_permission(node.scene)
        scene = node.scene
        node.is_deleted = True
        node.save(update_fields=["is_deleted", "updated_at"])
        _touch_scene_updated_at(scene)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"], url_path="reorder")
    def reorder(self, request):
        scene_id = request.data.get("scene_id")
        ordered_node_ids = request.data.get("ordered_node_ids") or []
        if not scene_id:
            return Response({"detail": "scene_id不能为空"}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(ordered_node_ids, list) or not ordered_node_ids:
            return Response({"detail": "ordered_node_ids不能为空"}, status=status.HTTP_400_BAD_REQUEST)

        scene = get_object_or_404(TestScene, id=scene_id)
        self._ensure_scene_permission(scene)
        nodes = {node.id: node for node in scene.nodes.filter(is_deleted=False)}
        try:
            ordered_ids = [int(item) for item in ordered_node_ids]
        except (TypeError, ValueError):
            return Response({"detail": "ordered_node_ids必须为整数数组"}, status=status.HTTP_400_BAD_REQUEST)
        if set(nodes.keys()) != set(ordered_ids):
            return Response({"detail": "ordered_node_ids必须覆盖场景下全部节点"}, status=status.HTTP_400_BAD_REQUEST)

        # 两阶段更新，避免 (scene, sort) 唯一约束冲突：先设临时值，再设最终值
        offset = 10000
        for idx, node_id in enumerate(ordered_ids):
            node = nodes.get(int(node_id))
            if not node:
                continue
            node.sort = idx + offset
            node.save(update_fields=["sort", "updated_at"])
        for idx, node_id in enumerate(ordered_ids):
            node = nodes.get(int(node_id))
            if not node:
                continue
            node.sort = idx
            node.save(update_fields=["sort", "updated_at"])
        _touch_scene_updated_at(scene)
        return Response({"detail": "排序更新成功"})

    @action(detail=True, methods=["post"], url_path="copy")
    def copy(self, request, pk=None):
        node = self.get_object()
        self._ensure_scene_permission(node.scene)
        max_sort = node.scene.nodes.filter(is_deleted=False).order_by("-sort").values_list("sort", flat=True).first()
        next_sort = (max_sort or 0) + 1
        node_key = f"{node.node_key}_copy_{int(timezone.now().timestamp())}"
        scene = node.scene
        new_node = TestSceneNode.objects.create(
            scene=scene,
            api_asset=node.api_asset,
            node_key=node_key[:80],
            name=f"{node.name}-副本",
            description=node.description,
            method=node.method or node.effective_method,
            request_headers=node.request_headers or {},
            request_params=node.request_params or {},
            request_body=node.request_body or {},
            param_type=node.param_type or "json",
            body_type=node.body_type or "json",
            assert_rules=node.assert_rules or [],
            extract_rules=node.extract_rules or [],
            expected_status_code=node.expected_status_code,
            timeout=node.timeout,
            on_failed=node.on_failed,
            sort=next_sort,
            is_enabled=node.is_enabled,
            api_synced_at=node.api_synced_at,
            api_sync_snapshot=node.api_sync_snapshot or {},
            pre_request_script=node.pre_request_script or "",
            script_timeout=node.script_timeout,
        )
        _touch_scene_updated_at(scene)
        return Response(TestSceneNodeSerializer(new_node).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="api-diff")
    def api_diff(self, request, pk=None):
        """获取节点与关联 API 资产的差异详情。"""
        node = self.get_object()
        self._ensure_scene_permission(node.scene)
        diff = compute_node_api_diff(node)
        if diff is None:
            return Response(
                {"detail": "节点未关联 API 资产或资产不存在"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(diff, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="sync-basic")
    def sync_basic(self, request, pk=None):
        """一键同步 URL/Method 到节点（标记同步时间与快照）。"""
        node = self.get_object()
        self._ensure_scene_permission(node.scene)
        if not node.api_asset_id:
            return Response({"detail": "节点未关联 API 资产"}, status=status.HTTP_400_BAD_REQUEST)
        asset = node.api_asset
        before_snapshot = get_node_snapshot_for_rollback(node)
        asset_snapshot = build_asset_snapshot_for_node(asset)
        now = timezone.now()
        node.api_synced_at = now
        node.api_sync_snapshot = asset_snapshot
        node.save(update_fields=["api_synced_at", "api_sync_snapshot", "updated_at"])
        after_snapshot = get_node_snapshot_for_rollback(node)
        sync_log = TestSceneNodeSyncLog.objects.create(
            node=node,
            sync_type=TestSceneNodeSyncLog.SYNC_BASIC,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            node_snapshot_before=before_snapshot,
            node_snapshot_after=after_snapshot,
            created_by=request.user,
        )
        rollback_until = (now + timedelta(hours=72)).isoformat()
        return Response(
            {
                "success": True,
                "node_id": node.id,
                "synced_fields": ["url", "method"],
                "sync_log_id": sync_log.id,
                "rollback_until": rollback_until,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="sync-add-params")
    def sync_add_params(self, request, pk=None):
        """将 API 新增的参数以空值追加到节点，不覆盖已有值。"""
        node = self.get_object()
        self._ensure_scene_permission(node.scene)
        if not node.api_asset_id:
            return Response({"detail": "节点未关联 API 资产"}, status=status.HTTP_400_BAD_REQUEST)
        param_keys = request.data.get("param_keys") or []
        scope = str(request.data.get("scope") or "request_params").strip()
        if scope not in ("request_params", "request_headers", "request_body"):
            return Response({"detail": "scope 仅支持 request_params/request_headers/request_body"}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(param_keys, list) or not param_keys:
            return Response({"detail": "param_keys 不能为空"}, status=status.HTTP_400_BAD_REQUEST)
        asset = node.api_asset
        if scope == "request_params":
            raw = asset.request_params or {}
            source = _normalize_kv_payload_to_dict(raw) if isinstance(raw, list) else (raw if isinstance(raw, dict) else {})
            target = dict(node.request_params or {}) if isinstance(node.request_params, dict) else {}
        elif scope == "request_headers":
            raw = asset.request_headers or {}
            source = _normalize_kv_payload_to_dict(raw) if isinstance(raw, list) else (raw if isinstance(raw, dict) else {})
            target = dict(node.request_headers or {}) if isinstance(node.request_headers, dict) else {}
        else:
            if asset.request_body_format != "form-data":
                return Response({"detail": "request_body 仅 form-data 时支持追加参数"}, status=status.HTTP_400_BAD_REQUEST)
            source = asset.request_body or {}
            target = dict(node.request_body or {})
        added = 0
        for key in param_keys:
            key = str(key).strip()
            if not key or key in target:
                continue
            src_val = source.get(key)
            if isinstance(src_val, dict) and "value" in src_val:
                target[key] = {**dict(src_val), "value": ""}
            else:
                target[key] = "" if src_val is None or src_val == "" else src_val
            added += 1
        before_snapshot = get_node_snapshot_for_rollback(node)
        if scope == "request_params":
            node.request_params = target
        elif scope == "request_headers":
            node.request_headers = target
        else:
            node.request_body = target
        now = timezone.now()
        node.api_synced_at = now
        node.api_sync_snapshot = build_asset_snapshot_for_node(asset)
        node.save(update_fields=["request_params", "request_headers", "request_body", "api_synced_at", "api_sync_snapshot", "updated_at"])
        after_snapshot = get_node_snapshot_for_rollback(node)
        TestSceneNodeSyncLog.objects.create(
            node=node,
            sync_type=TestSceneNodeSyncLog.SYNC_PARAMS_ADD,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            node_snapshot_before=before_snapshot,
            node_snapshot_after=after_snapshot,
            created_by=request.user,
        )
        _touch_scene_updated_at(node.scene)
        payload = {"success": True, "node_id": node.id, "added_count": added, "scope": scope}
        if scope == "request_params":
            payload["request_params"] = node.request_params
        elif scope == "request_headers":
            payload["request_headers"] = node.request_headers
        elif scope == "request_body":
            payload["request_body"] = node.request_body
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="sync-headers")
    def sync_headers(self, request, pk=None):
        """完整同步请求头：将 API 资产的 request_headers 同步到节点，覆盖节点现有请求头。"""
        node = self.get_object()
        self._ensure_scene_permission(node.scene)
        if not node.api_asset_id:
            return Response({"detail": "节点未关联 API 资产"}, status=status.HTTP_400_BAD_REQUEST)
        asset = node.api_asset
        source = asset.request_headers or {}
        if isinstance(source, list):
            target = {}
            for item in source:
                if isinstance(item, dict):
                    key = str(item.get("key") or item.get("name") or "").strip()
                    if key:
                        target[key] = copy.deepcopy(item)
        else:
            target = copy.deepcopy(source) if isinstance(source, dict) else {}
        before_snapshot = get_node_snapshot_for_rollback(node)
        node.request_headers = target
        now = timezone.now()
        node.api_synced_at = now
        node.api_sync_snapshot = build_asset_snapshot_for_node(asset)
        node.save(update_fields=["request_headers", "api_synced_at", "api_sync_snapshot", "updated_at"])
        after_snapshot = get_node_snapshot_for_rollback(node)
        TestSceneNodeSyncLog.objects.create(
            node=node,
            sync_type=TestSceneNodeSyncLog.SYNC_PARAMS_ADD,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            node_snapshot_before=before_snapshot,
            node_snapshot_after=after_snapshot,
            created_by=request.user,
        )
        _touch_scene_updated_at(node.scene)
        return Response(
            {
                "success": True,
                "node_id": node.id,
                "synced_headers_count": len(target),
                "request_headers": node.request_headers,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="sync-params")
    def sync_params(self, request, pk=None):
        """完整同步请求参数：将 API 资产的 request_params 同步到节点，覆盖节点现有参数。"""
        node = self.get_object()
        self._ensure_scene_permission(node.scene)
        if not node.api_asset_id:
            return Response({"detail": "节点未关联 API 资产"}, status=status.HTTP_400_BAD_REQUEST)
        asset = node.api_asset
        source = asset.request_params or {}
        if isinstance(source, list):
            target = {}
            for item in source:
                if isinstance(item, dict):
                    key = str(item.get("key") or item.get("name") or "").strip()
                    if key:
                        target[key] = copy.deepcopy(item)
        else:
            target = copy.deepcopy(source) if isinstance(source, dict) else {}
        before_snapshot = get_node_snapshot_for_rollback(node)
        node.request_params = target
        now = timezone.now()
        node.api_synced_at = now
        node.api_sync_snapshot = build_asset_snapshot_for_node(asset)
        node.save(update_fields=["request_params", "api_synced_at", "api_sync_snapshot", "updated_at"])
        after_snapshot = get_node_snapshot_for_rollback(node)
        TestSceneNodeSyncLog.objects.create(
            node=node,
            sync_type=TestSceneNodeSyncLog.SYNC_PARAMS_ADD,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            node_snapshot_before=before_snapshot,
            node_snapshot_after=after_snapshot,
            created_by=request.user,
        )
        _touch_scene_updated_at(node.scene)
        return Response(
            {
                "success": True,
                "node_id": node.id,
                "synced_params_count": len(target),
                "request_params": node.request_params,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="sync-rollback")
    def sync_rollback(self, request, pk=None):
        """回滚到指定同步前的配置，仅 72 小时内有效。"""
        node = self.get_object()
        self._ensure_scene_permission(node.scene)
        sync_log_id = request.data.get("sync_log_id")
        if not sync_log_id:
            return Response({"detail": "sync_log_id 不能为空"}, status=status.HTTP_400_BAD_REQUEST)
        sync_log = get_object_or_404(TestSceneNodeSyncLog, id=sync_log_id, node=node)
        cutoff = timezone.now() - timedelta(hours=72)
        if sync_log.created_at < cutoff:
            return Response(
                {"detail": "该同步记录已超过 72 小时，无法回滚"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        current_before = get_node_snapshot_for_rollback(node)
        # 优先使用 node_snapshot_before（节点完整配置快照），兼容旧记录使用 before_snapshot
        restore_snapshot = sync_log.node_snapshot_before or sync_log.before_snapshot or {}
        node.request_headers = restore_snapshot.get("request_headers", node.request_headers or {})
        node.request_params = restore_snapshot.get("request_params", node.request_params or {})
        node.request_body = restore_snapshot.get("request_body", node.request_body or {})
        node.param_type = restore_snapshot.get("param_type", node.param_type or "json")
        node.body_type = restore_snapshot.get("body_type", node.body_type or "json")
        node.assert_rules = restore_snapshot.get("assert_rules", node.assert_rules or [])
        node.extract_rules = restore_snapshot.get("extract_rules", node.extract_rules or [])
        node.expected_status_code = restore_snapshot.get("expected_status_code", node.expected_status_code or 200)
        if "api_synced_at" in restore_snapshot and restore_snapshot["api_synced_at"]:
            from django.utils.dateparse import parse_datetime
            node.api_synced_at = parse_datetime(restore_snapshot["api_synced_at"])
        else:
            node.api_synced_at = None
        node.api_sync_snapshot = restore_snapshot.get("api_sync_snapshot", node.api_sync_snapshot or {})
        node.save(update_fields=[
            "request_headers", "request_params", "request_body", "param_type", "body_type",
            "assert_rules", "extract_rules", "expected_status_code", "api_synced_at", "api_sync_snapshot", "updated_at",
        ])
        rolled_back_snapshot = get_node_snapshot_for_rollback(node)
        TestSceneNodeSyncLog.objects.create(
            node=node,
            sync_type=TestSceneNodeSyncLog.SYNC_ROLLBACK,
            before_snapshot=current_before,
            after_snapshot=rolled_back_snapshot,
            node_snapshot_before=current_before,
            node_snapshot_after=rolled_back_snapshot,
            created_by=request.user,
        )
        _touch_scene_updated_at(node.scene)
        return Response({"success": True, "node_id": node.id, "detail": "回滚成功"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="batch-operate")
    def batch_operate(self, request):
        return Response(
            {"detail": "batch-operate 已废弃，请改用单节点接口"},
            status=status.HTTP_410_GONE,
        )

    @action(detail=True, methods=["post"], url_path="test-pre-request-script")
    def test_pre_request_script(self, request, pk=None):
        """
        测试场景节点的前置脚本（子进程隔离执行）。
        节点有 pre_request_script 时测试节点脚本；
        无节点脚本时测试环境脚本（模拟当前节点执行时的上下文）。
        """
        import subprocess, sys, json
        from django.conf import settings
        from test_manager.env_variables_compat import variables_for_runtime
        from test_manager.pre_request_script_runner import main as run_script

        node = self.get_object()
        self._ensure_scene_permission(node.scene)

        script = request.data.get("script", "")
        timeout_ms = min(1000, max(100, int(
            request.data.get("script_timeout", getattr(node, "script_timeout", 1000) or 1000)
        )))

        # 脚本内容：优先取节点级，其次取关联环境（用于预览环境脚本）
        if not script:
            script = getattr(node, "pre_request_script", "") or ""

        # 模拟执行时的请求上下文（前端可传测试数据）
        test_headers = request.data.get("request_headers", {})
        test_params  = request.data.get("request_params", {})
        test_body    = request.data.get("request_body", {})
        test_url     = request.data.get("request_url", "")
        test_method  = request.data.get("request_method",
                                        getattr(node.api_asset, "method", "GET") if node.api_asset_id else "GET")

        # 环境变量：取节点 effective_env 的变量
        effective_env = None
        try:
            from test_manager.api.scene_engine import _get_effective_env_for_node
            scene = node.scene
            env_obj = None
            # 从场景 runtime_config 尝试获取 environment_id
            runtime_config = scene.runtime_config or {}
            env_id = runtime_config.get("environment_id")
            if env_id:
                from test_manager.models import Environment
                env_obj = Environment.objects.filter(id=env_id).first()
            effective_env = _get_effective_env_for_node(node, scene, env_obj, runtime_config, {})
        except Exception:
            effective_env = None

        env_vars = {}
        if effective_env:
            env_vars = variables_for_runtime(effective_env.variables or {})
        # 注入场景变量池（供脚本读取）
        scene_vars = request.data.get("variable_pool", {})
        if isinstance(scene_vars, dict):
            for k, v in scene_vars.items():
                if k != "env" and v is not None:
                    env_vars[k] = v

        payload = {
            "mode": "test",
            "script": script,
            "env_vars": env_vars,
            "request_headers": test_headers or {},
            "request_params": test_params or {},
            "request_body": test_body or {},
            "request_url": test_url,
            "request_method": test_method,
            "timeout_ms": timeout_ms,
        }

        proc_env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "test_manager.pre_request_script_runner"],
                input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                capture_output=True, timeout=15,
                cwd=str(settings.BASE_DIR), env=proc_env,
            )
        except subprocess.TimeoutExpired:
            return Response({
                "success": False, "logs": [], "console": [],
                "error": "脚本执行超时（15秒）"
            })
        except Exception as e:
            return Response({
                "success": False, "logs": [], "console": [],
                "error": f"子进程启动失败: {e}"
            })

        if proc.returncode != 0:
            err_msg = proc.stderr.decode("utf-8", errors="replace").strip() or "脚本执行进程异常退出"
            return Response({"success": False, "logs": [], "console": [], "error": err_msg})

        try:
            out = proc.stdout.decode("utf-8", errors="replace")
            result = json.loads(out)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return Response({
                "success": False, "logs": [], "console": [],
                "error": f"解析结果失败: {e}"
            })
        return Response(result)


class TestSceneExecutionViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "delete", "head", "options"]
    queryset = TestSceneExecution.objects.select_related(
        "scene", "scene__project", "scene__project__platform_project",
        "target_node", "created_by", "environment",
    ).defer(
        "node_results", "summary", "error_message",
    ).all()
    serializer_class = TestSceneExecutionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return TestSceneExecutionListSerializer
        return TestSceneExecutionSerializer

    def get_queryset(self):
        queryset = TestSceneExecution.objects.select_related(
            "scene", "scene__project", "scene__project__platform_project",
            "target_node", "created_by", "environment",
        ).defer("node_results", "summary", "error_message")
        if not self.request.user.is_staff:
            queryset = queryset.filter(scene__project__in=_project_queryset_for_user(self.request.user))
        scene_id = self.request.query_params.get("scene_id")
        if scene_id:
            queryset = queryset.filter(scene_id=scene_id)
        project = self.request.query_params.get("project")
        if project:
            queryset = queryset.filter(scene__project__platform_project_id=project)
        status_value = self.request.query_params.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset.order_by("-created_at")

    def perform_destroy(self, instance):
        instance.delete()


class SceneDownloadedFileViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "delete", "head", "options"]
    queryset = SceneDownloadedFile.objects.select_related(
        "execution", "node", "scene", "scene__project", "created_by",
    ).all()
    serializer_class = SceneDownloadedFileSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = SceneDownloadedFile.objects.select_related(
            "execution", "node", "scene", "scene__project", "created_by",
        )
        if not self.request.user.is_staff:
            qs = qs.filter(scene__project__in=_project_queryset_for_user(self.request.user))
        # 过滤参数
        scene_id = self.request.query_params.get("scene_id")
        if scene_id:
            qs = qs.filter(scene_id=scene_id)
        execution_id = self.request.query_params.get("execution_id")
        if execution_id:
            qs = qs.filter(execution_id=execution_id)
        project = self.request.query_params.get("project")
        if project:
            qs = qs.filter(scene__project__platform_project_id=project)
        filename = self.request.query_params.get("filename")
        if filename:
            qs = qs.filter(filename__icontains=filename)
        md5 = self.request.query_params.get("md5")
        if md5:
            qs = qs.filter(md5=md5)
        return qs.order_by("-created_at")

    def perform_destroy(self, instance):
        instance.delete()

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        """下载原始文件。"""
        dl_file = self.get_object()
        if not dl_file.file_path or not default_storage.exists(dl_file.file_path):
            return Response({"detail": "文件不存在"}, status=status.HTTP_404_NOT_FOUND)
        try:
            f = default_storage.open(dl_file.file_path, "rb")
            resp = FileResponse(
                f,
                as_attachment=True,
                filename=dl_file.filename,
                content_type=dl_file.content_type or "application/octet-stream",
            )
            return resp
        except Exception as exc:
            return Response({"detail": f"文件读取失败: {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


            return Response({"detail": f"文件读取失败: {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


