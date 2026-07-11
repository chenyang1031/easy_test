"""测试场景编排导出/导入 ViewSet。"""

import json
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from test_manager.models.project import Project, ApiProject
from test_manager.models.api_asset import ApiGroup, ApiAsset
from test_manager.models.environment import Environment
from test_manager.models.scene import TestScene, TestSceneNode

try:
    import yaml
except ImportError:
    yaml = None


EXPORT_VERSION = "1.0"
EXPORT_TYPE = "scene-orchestration"


def _get_group_path(group):
    """沿 parent 链递归收集分组名称路径。"""
    path = []
    current = group
    while current:
        path.append(current.name)
        current = current.parent
    path.reverse()
    return path


def _serialize_group(group, path):
    return {
        "name": group.name,
        "parent_path": path[:-1],
        "sort_order": group.sort_order,
    }


def _serialize_asset(asset, group_path_map):
    return {
        "name": asset.name,
        "method": asset.method,
        "url": asset.url,
        "interface_desc": asset.interface_desc,
        "group_path": group_path_map.get(asset.group_id),
        "request_headers": asset.request_headers,
        "request_params": asset.request_params,
        "request_body_format": asset.request_body_format,
        "request_body": asset.request_body,
        "response_schema": asset.response_schema,
        "error_code": asset.error_code,
        "auth_config": asset.auth_config,
        "status": asset.status,
        "source": asset.source,
    }


def _serialize_env(env):
    return {
        "name": env.name,
        "base_url": env.base_url,
        "variables": env.variables,
        "request_headers": env.request_headers,
        "category": env.category,
        "is_global_visible": env.is_global_visible,
        "pre_request_script": env.pre_request_script,
        "script_timeout": env.script_timeout,
    }


def _serialize_node(node, asset_path_map, env_map):
    data = {
        "node_key": node.node_key,
        "name": node.name,
        "description": node.description,
        "request_headers": node.request_headers,
        "request_params": node.request_params,
        "request_body": node.request_body,
        "param_type": node.param_type,
        "body_type": node.body_type,
        "assert_rules": node.assert_rules,
        "extract_rules": node.extract_rules,
        "expected_status_code": node.expected_status_code,
        "expected_response_headers": node.expected_response_headers,
        "expected_response_body": node.expected_response_body,
        "timeout": node.timeout,
        "on_failed": node.on_failed,
        "sort": node.sort,
        "is_enabled": node.is_enabled,
        "custom_base_url": node.custom_base_url,
        "request_url": node.request_url,
        "pre_request_script": node.pre_request_script,
        "script_timeout": node.script_timeout,
    }
    if node.api_asset_id and node.api_asset_id in asset_path_map:
        data["api_asset_ref"] = asset_path_map[node.api_asset_id]
    if node.environment_id and node.environment_id in env_map:
        data["environment_name"] = env_map[node.environment_id]
    return data


def _serialize_scene(scene, nodes, asset_path_map, env_map, group_path_map):
    return {
        "name": scene.name,
        "description": scene.description,
        "group_path": group_path_map.get(scene.group_id),
        "variables": scene.variables,
        "runtime_config": scene.runtime_config,
        "is_active": scene.is_active,
        "nodes": [
            _serialize_node(n, asset_path_map, env_map)
            for n in nodes
        ],
    }


class SceneImportExportViewSet(viewsets.ViewSet):

    @action(detail=False, methods=["post"], url_path="export-scenes")
    def export_scenes(self, request):
        project_id = request.data.get("project_id")
        scene_ids = request.data.get("scene_ids")
        export_format = str(request.data.get("format") or "json").lower()

        if not project_id:
            return Response(
                {"detail": "project_id不能为空"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        api_project = ApiProject.objects.get(id=project_id)

        scenes_qs = TestScene.objects.filter(
            project=api_project, is_deleted=False
        )
        if scene_ids:
            scenes_qs = scenes_qs.filter(id__in=scene_ids)
        scenes = scenes_qs.prefetch_related("nodes").order_by("id")

        if not scenes.exists():
            return Response(
                {"detail": "没有找到可导出的场景"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ---- 收集关联的 ApiGroup（递归 parent 链） ----
        group_ids = set()
        for s in scenes:
            if s.group_id:
                group_ids.add(s.group_id)

        added = set(group_ids)
        while True:
            parents = set(
                ApiGroup.objects.filter(id__in=added)
                .exclude(parent_id__isnull=True)
                .values_list("parent_id", flat=True)
            )
            new_parents = parents - added
            if not new_parents:
                break
            added.update(new_parents)
        group_ids = added

        # 节点引用的分组
        for scene in scenes:
            for node in scene.nodes.filter(is_deleted=False):
                if node.api_asset_id:
                    try:
                        asset = ApiAsset.objects.get(
                            id=node.api_asset_id
                        )
                        if asset.group_id:
                            group_ids.add(asset.group_id)
                            gid = asset.group_id
                            while True:
                                try:
                                    g = ApiGroup.objects.get(id=gid)
                                    if g.parent_id and g.parent_id not in group_ids:
                                        group_ids.add(g.parent_id)
                                        gid = g.parent_id
                                    else:
                                        break
                                except ApiGroup.DoesNotExist:
                                    break
                    except ApiAsset.DoesNotExist:
                        pass

        groups = ApiGroup.objects.filter(id__in=group_ids).order_by("id")
        group_path_map = {}
        for g in groups:
            path = _get_group_path(g)
            group_path_map[g.id] = path

        # 按层级深度排序（确保导入时父分组先创建）
        sorted_groups = sorted(
            groups, key=lambda g: len(group_path_map[g.id])
        )
        groups_data = [
            _serialize_group(g, group_path_map[g.id]) for g in sorted_groups
        ]

        # ---- 收集关联的 ApiAsset ----
        asset_ids = set()
        for scene in scenes:
            for node in scene.nodes.filter(is_deleted=False):
                if node.api_asset_id:
                    asset_ids.add(node.api_asset_id)

        assets = ApiAsset.objects.filter(id__in=asset_ids)
        asset_path_map = {}
        for a in assets:
            asset_path_map[a.id] = {"method": a.method, "url": a.url}
        assets_data = [
            _serialize_asset(a, group_path_map) for a in assets
        ]

        # ---- 收集关联的 Environment ----
        env_ids = set()
        for scene in scenes:
            for node in scene.nodes.filter(is_deleted=False):
                if node.environment_id:
                    env_ids.add(node.environment_id)

        env_map = {}
        environments = Environment.objects.filter(id__in=env_ids)
        for e in environments:
            env_map[e.id] = e.name
        envs_data = [_serialize_env(e) for e in environments]

        # ---- 组装导出数据 ----
        export_data = {
            "version": EXPORT_VERSION,
            "export_type": EXPORT_TYPE,
            "project_name": api_project.name,
            "groups": groups_data,
            "environments": envs_data,
            "api_assets": assets_data,
            "scenes": [
                _serialize_scene(
                    s,
                    s.nodes.filter(is_deleted=False).order_by("sort"),
                    asset_path_map,
                    env_map,
                    group_path_map,
                )
                for s in scenes
            ],
        }

        filename = f"scenes_{api_project.name}"

        if export_format == "yaml":
            if not yaml:
                return Response(
                    {"detail": "环境未安装PyYAML，无法导出YAML"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response({
                "format": "yaml",
                "content": yaml.safe_dump(
                    export_data, sort_keys=False, allow_unicode=True
                ),
                "filename": f"{filename}.yaml",
            })

        return Response({
            "format": "json",
            "content": export_data,
            "filename": f"{filename}.json",
        })

    # ------------------------------------------------------------------
    # 导入预览
    # ------------------------------------------------------------------
    @action(detail=False, methods=["post"], url_path="import-scenes/preview")
    def preview_import(self, request):
        file_obj = request.FILES.get("file")
        project_id = request.data.get("project_id")

        if not file_obj:
            return Response(
                {"detail": "请上传导出文件"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not project_id:
            return Response(
                {"detail": "project_id不能为空"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response(
                {"detail": "目标项目不存在"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            api_project = ApiProject.objects.get(platform_project=project)
        except ApiProject.DoesNotExist:
            return Response(
                {"detail": "目标项目未关联API项目"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 解析文件
        content = file_obj.read().decode("utf-8")
        file_name = file_obj.name or ""
        if file_name.endswith((".yaml", ".yml")):
            if not yaml:
                return Response(
                    {"detail": "环境未安装PyYAML，无法解析YAML文件"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                data = yaml.safe_load(content)
            except Exception as e:
                return Response(
                    {"detail": f"YAML解析失败: {e}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                return Response(
                    {"detail": f"JSON解析失败: {e}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if not isinstance(data, dict):
            return Response(
                {"detail": "文件格式不正确，应为对象"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if data.get("export_type") != EXPORT_TYPE:
            return Response(
                {"detail": "不支持的导出类型，请使用场景编排导出文件"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 检测冲突
        conflicts = {"groups": [], "environments": [], "api_assets": [], "scenes": []}

        # 分组冲突
        for g in data.get("groups", []):
            parent = None
            parent_path = g.get("parent_path", [])
            for pname in parent_path:
                try:
                    parent = ApiGroup.objects.get(
                        project=api_project, parent=parent, name=pname
                    )
                except ApiGroup.DoesNotExist:
                    parent = None
                    break
            if ApiGroup.objects.filter(
                project=api_project, parent=parent, name=g["name"]
            ).exists():
                conflicts["groups"].append({
                    "name": g["name"],
                    "parent_path": parent_path,
                    "reason": "同名分组已存在",
                })

        # 环境冲突
        for e in data.get("environments", []):
            if Environment.objects.filter(
                project=project, name=e["name"]
            ).exists():
                conflicts["environments"].append({
                    "name": e["name"],
                    "reason": "同名环境已存在",
                })

        # API 资产冲突
        for a in data.get("api_assets", []):
            if ApiAsset.objects.filter(
                project=api_project,
                method=a["method"],
                url=a["url"],
                is_deleted=False,
            ).exists():
                conflicts["api_assets"].append({
                    "name": a["name"],
                    "method": a["method"],
                    "url": a["url"],
                    "reason": "同方法同URL的接口已存在",
                })

        # 场景冲突
        for s in data.get("scenes", []):
            if TestScene.objects.filter(
                project=api_project, name=s["name"], is_deleted=False
            ).exists():
                conflicts["scenes"].append({
                    "name": s["name"],
                    "reason": "同名场景已存在",
                })

        return Response({
            "source_project": data.get("project_name", ""),
            "version": data.get("version", ""),
            "summary": {
                "groups": len(data.get("groups", [])),
                "environments": len(data.get("environments", [])),
                "api_assets": len(data.get("api_assets", [])),
                "scenes": len(data.get("scenes", [])),
                "total_nodes": sum(
                    len(s.get("nodes", [])) for s in data.get("scenes", [])
                ),
            },
            "conflicts": conflicts,
            "data": data,
        })

    # ------------------------------------------------------------------
    # 导入确认
    # ------------------------------------------------------------------
    @action(detail=False, methods=["post"], url_path="import-scenes/confirm")
    def confirm_import(self, request):
        project_id = request.data.get("project_id")
        import_data = request.data.get("data")
        conflict_strategy = request.data.get(
            "default_conflict_strategy", "skip"
        )

        if not project_id or not import_data:
            return Response(
                {"detail": "project_id和data不能为空"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response(
                {"detail": "目标项目不存在"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            api_project = ApiProject.objects.get(platform_project=project)
        except ApiProject.DoesNotExist:
            return Response(
                {"detail": "目标项目未关联API项目"},
                status=status.HTTP_404_NOT_FOUND,
            )

        stats = {
            "scenes": {"created": 0, "updated": 0, "skipped": 0},
            "nodes": {"created": 0},
            "groups": {"created": 0, "updated": 0, "skipped": 0},
            "environments": {"created": 0, "updated": 0, "skipped": 0},
            "api_assets": {"created": 0, "updated": 0, "skipped": 0},
        }

        with transaction.atomic():
            # 1. 导入分组（按 parent_path 长度升序，确保父分组先创建）
            groups_sorted = sorted(
                import_data.get("groups", []),
                key=lambda g: len(g.get("parent_path", [])),
            )
            for g in groups_sorted:
                parent = None
                for pname in g.get("parent_path", []):
                    try:
                        parent = ApiGroup.objects.get(
                            project=api_project, parent=parent, name=pname
                        )
                    except ApiGroup.DoesNotExist:
                        parent = None
                        break

                name = g["name"]
                existing = ApiGroup.objects.filter(
                    project=api_project, parent=parent, name=name
                ).first()

                if existing:
                    if conflict_strategy == "skip":
                        stats["groups"]["skipped"] += 1
                    elif conflict_strategy == "overwrite":
                        existing.sort_order = g.get("sort_order", 0)
                        existing.save()
                        stats["groups"]["updated"] += 1
                    else:  # keep_both
                        new_name = name
                        suffix = 1
                        while ApiGroup.objects.filter(
                            project=api_project, parent=parent, name=new_name
                        ).exists():
                            suffix += 1
                            new_name = f"{name} ({suffix})"
                        ApiGroup.objects.create(
                            project=api_project,
                            parent=parent,
                            name=new_name,
                            sort_order=g.get("sort_order", 0),
                        )
                        stats["groups"]["created"] += 1
                else:
                    ApiGroup.objects.create(
                        project=api_project,
                        parent=parent,
                        name=name,
                        sort_order=g.get("sort_order", 0),
                    )
                    stats["groups"]["created"] += 1

            # 2. 导入环境
            for e in import_data.get("environments", []):
                existing = Environment.objects.filter(
                    project=project, name=e["name"]
                ).first()
                env_defaults = {
                    "base_url": e.get("base_url", ""),
                    "variables": e.get("variables", {}),
                    "request_headers": e.get("request_headers", []),
                    "category": e.get("category", "default"),
                    "is_global_visible": e.get("is_global_visible", False),
                    "pre_request_script": e.get("pre_request_script", ""),
                    "script_timeout": e.get("script_timeout", 1000),
                }
                if existing:
                    if conflict_strategy == "skip":
                        stats["environments"]["skipped"] += 1
                    elif conflict_strategy == "overwrite":
                        for k, v in env_defaults.items():
                            setattr(existing, k, v)
                        existing.save()
                        stats["environments"]["updated"] += 1
                    else:
                        new_name = e["name"]
                        suffix = 1
                        while Environment.objects.filter(
                            project=project, name=new_name
                        ).exists():
                            suffix += 1
                            new_name = f"{e['name']} ({suffix})"
                        Environment.objects.create(
                            project=project, name=new_name, **env_defaults
                        )
                        stats["environments"]["created"] += 1
                else:
                    Environment.objects.create(
                        project=project, name=e["name"], **env_defaults
                    )
                    stats["environments"]["created"] += 1

            # 3. 导入 API 资产
            for a in import_data.get("api_assets", []):
                group = _resolve_group(
                    api_project, a.get("group_path", [])
                )
                asset_defaults = _build_asset_defaults(a, group)

                existing = ApiAsset.objects.filter(
                    project=api_project,
                    method=a["method"],
                    url=a["url"],
                    is_deleted=False,
                ).first()

                if existing:
                    if conflict_strategy == "skip":
                        stats["api_assets"]["skipped"] += 1
                    elif conflict_strategy == "overwrite":
                        for k, v in asset_defaults.items():
                            setattr(existing, k, v)
                        existing.save()
                        stats["api_assets"]["updated"] += 1
                    else:
                        new_name = a["name"]
                        suffix = 1
                        while ApiAsset.objects.filter(
                            project=api_project,
                            method=a["method"],
                            url=a["url"],
                            name=new_name,
                            is_deleted=False,
                        ).exists():
                            suffix += 1
                            new_name = f"{a['name']} ({suffix})"
                        asset_defaults["name"] = new_name
                        ApiAsset.objects.create(
                            project=api_project, **asset_defaults
                        )
                        stats["api_assets"]["created"] += 1
                else:
                    ApiAsset.objects.create(
                        project=api_project, **asset_defaults
                    )
                    stats["api_assets"]["created"] += 1

            # 4. 导入场景 + 节点
            for s in import_data.get("scenes", []):
                scene_group = _resolve_group(
                    api_project, s.get("group_path", [])
                )
                existing_scene = TestScene.objects.filter(
                    project=api_project, name=s["name"], is_deleted=False
                ).first()

                if existing_scene:
                    if conflict_strategy == "skip":
                        stats["scenes"]["skipped"] += 1
                        continue
                    elif conflict_strategy == "overwrite":
                        _update_scene(existing_scene, s, scene_group)
                        stats["scenes"]["updated"] += 1
                        scene_obj = existing_scene
                    else:  # keep_both
                        new_name = s["name"]
                        suffix = 1
                        while TestScene.objects.filter(
                            project=api_project,
                            name=new_name,
                            is_deleted=False,
                        ).exists():
                            suffix += 1
                            new_name = f"{s['name']} ({suffix})"
                        scene_obj = _create_scene(
                            api_project, s, scene_group, new_name,
                            request.user,
                        )
                        stats["scenes"]["created"] += 1
                else:
                    scene_obj = _create_scene(
                        api_project, s, scene_group, s["name"],
                        request.user,
                    )
                    stats["scenes"]["created"] += 1

                # 导入节点
                for n in s.get("nodes", []):
                    api_asset = _resolve_asset(
                        api_project, n.get("api_asset_ref")
                    )
                    environment = _resolve_env(
                        project, n.get("environment_name")
                    )
                    TestSceneNode.objects.create(
                        scene=scene_obj,
                        api_asset=api_asset,
                        node_key=n.get("node_key", ""),
                        name=n.get("name", ""),
                        description=n.get("description", ""),
                        request_headers=n.get("request_headers", {}),
                        request_params=n.get("request_params", {}),
                        request_body=n.get("request_body", {}),
                        param_type=n.get("param_type", "json"),
                        body_type=n.get("body_type", "json"),
                        assert_rules=n.get("assert_rules", []),
                        extract_rules=n.get("extract_rules", []),
                        expected_status_code=n.get(
                            "expected_status_code", 200
                        ),
                        expected_response_headers=n.get(
                            "expected_response_headers", {}
                        ),
                        expected_response_body=n.get(
                            "expected_response_body"
                        ),
                        timeout=n.get("timeout"),
                        on_failed=n.get("on_failed", "stop"),
                        sort=n.get("sort", 0),
                        is_enabled=n.get("is_enabled", True),
                        environment=environment,
                        custom_base_url=n.get("custom_base_url", ""),
                        request_url=n.get("request_url", ""),
                        pre_request_script=n.get(
                            "pre_request_script", ""
                        ),
                        script_timeout=n.get("script_timeout", 1000),
                    )
                    stats["nodes"]["created"] += 1

        return Response(stats)


# ======================================================================
# 辅助函数
# ======================================================================

def _resolve_group(api_project, group_path):
    """根据路径名称列表查找分组。"""
    if not group_path:
        return None
    parent = None
    for name in group_path:
        try:
            parent = ApiGroup.objects.get(
                project=api_project, parent=parent, name=name
            )
        except ApiGroup.DoesNotExist:
            return None
    return parent


def _resolve_asset(api_project, asset_ref):
    """根据 {method, url} 引用查找 API 资产。"""
    if not asset_ref:
        return None
    return ApiAsset.objects.filter(
        project=api_project,
        method=asset_ref.get("method"),
        url=asset_ref.get("url"),
        is_deleted=False,
    ).first()


def _resolve_env(project, env_name):
    """根据名称查找环境。"""
    if not env_name:
        return None
    return Environment.objects.filter(
        project=project, name=env_name
    ).first()


def _build_asset_defaults(asset_data, group):
    return {
        "name": asset_data.get("name", ""),
        "group": group,
        "method": asset_data.get("method", "GET"),
        "url": asset_data.get("url", ""),
        "interface_desc": asset_data.get("interface_desc", ""),
        "request_headers": asset_data.get("request_headers", {}),
        "request_params": asset_data.get("request_params", []),
        "request_body_format": asset_data.get("request_body_format", "json"),
        "request_body": asset_data.get("request_body", {}),
        "response_schema": asset_data.get("response_schema", {}),
        "error_code": asset_data.get("error_code", []),
        "auth_config": asset_data.get("auth_config", {}),
        "status": asset_data.get("status", "draft"),
        "source": asset_data.get("source", "manual"),
    }


def _update_scene(scene, scene_data, group):
    """更新已有场景的字段。"""
    scene.name = scene_data["name"]
    scene.description = scene_data.get("description", "")
    scene.group = group
    scene.variables = scene_data.get("variables", {})
    scene.runtime_config = scene_data.get("runtime_config", {})
    scene.is_active = scene_data.get("is_active", True)
    scene.save()
    # 删除旧节点，重新创建
    scene.nodes.all().delete()


def _create_scene(api_project, scene_data, group, name, user):
    """创建新场景。"""
    return TestScene.objects.create(
        project=api_project,
        group=group,
        name=name,
        description=scene_data.get("description", ""),
        variables=scene_data.get("variables", {}),
        runtime_config=scene_data.get("runtime_config", {}),
        is_active=scene_data.get("is_active", True),
        created_by=user if user and user.is_authenticated else None,
    )
