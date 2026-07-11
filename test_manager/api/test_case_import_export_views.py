"""测试用例导出/导入 ViewSet。"""

import base64
import json
from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from test_manager.models.project import Project
from test_manager.models.test_case import TestCase, TestCaseGroup

try:
    import yaml
except ImportError:
    yaml = None


EXPORT_VERSION = "1.0"
EXPORT_TYPE = "test-cases"


# ======================================================================
# 序列化 / 反序列化辅助函数
# ======================================================================

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
    }


def _serialize_test_case(case, group_path_map):
    data = {
        "name": case.name,
        "description": case.description,
        "request_method": case.request_method,
        "request_url": case.request_url,
        "request_headers": case.request_headers,
        "request_body": case.request_body,
        "request_body_format": case.request_body_format,
        "expected_status_code": case.expected_status_code,
        "validation_rules": case.validation_rules,
        "extract_params": case.extract_params,
        "upload_field_name": case.upload_field_name,
        "timeout": case.timeout,
        "group_path": group_path_map.get(case.group_id),
    }
    if case.upload_file:
        try:
            case.upload_file.open("rb")
            raw = case.upload_file.read()
            case.upload_file.close()
            data["upload_file_base64"] = base64.b64encode(raw).decode("ascii")
            data["upload_file_name"] = case.upload_file.name.split("/")[-1]
        except Exception:
            pass
    return data


def _resolve_group(project, group_path):
    """根据路径名称列表查找 TestCaseGroup。"""
    if not group_path:
        return None
    parent = None
    for name in group_path:
        try:
            parent = TestCaseGroup.objects.get(
                project=project, parent=parent, name=name
            )
        except TestCaseGroup.DoesNotExist:
            return None
    return parent


class TestCaseImportExportViewSet(viewsets.ViewSet):

    # ------------------------------------------------------------------
    # 导出测试用例
    # ------------------------------------------------------------------
    @action(detail=False, methods=["post"], url_path="export")
    def export_test_cases(self, request):
        project_id = request.data.get("project_id")
        case_ids = request.data.get("test_case_ids")
        export_format = str(request.data.get("format") or "json").lower()

        if not project_id:
            return Response(
                {"detail": "project_id不能为空"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response(
                {"detail": "项目不存在"},
                status=status.HTTP_404_NOT_FOUND,
            )

        cases_qs = TestCase.objects.filter(project=project)
        if case_ids:
            cases_qs = cases_qs.filter(id__in=case_ids)
        cases = cases_qs.order_by("id")

        if not cases.exists():
            return Response(
                {"detail": "没有找到可导出的测试用例"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ---- 收集关联的 TestCaseGroup（递归 parent 链） ----
        group_ids = set()
        for c in cases:
            if c.group_id:
                group_ids.add(c.group_id)

        added = set(group_ids)
        while True:
            parents = set(
                TestCaseGroup.objects.filter(id__in=added)
                .exclude(parent_id__isnull=True)
                .values_list("parent_id", flat=True)
            )
            new_parents = parents - added
            if not new_parents:
                break
            added.update(new_parents)
        group_ids = added

        groups = TestCaseGroup.objects.filter(id__in=group_ids).order_by("id")
        group_path_map = {}
        for g in groups:
            path = _get_group_path(g)
            group_path_map[g.id] = path

        sorted_groups = sorted(
            groups, key=lambda g: len(group_path_map[g.id])
        )
        groups_data = [
            _serialize_group(g, group_path_map[g.id]) for g in sorted_groups
        ]

        # ---- 组装导出数据 ----
        export_data = {
            "version": EXPORT_VERSION,
            "export_type": EXPORT_TYPE,
            "project_name": project.name,
            "test_case_groups": groups_data,
            "test_cases": [
                _serialize_test_case(c, group_path_map) for c in cases
            ],
        }

        filename = f"test_cases_{project.name}"

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
    @action(detail=False, methods=["post"], url_path="import/preview")
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
                {"detail": "不支持的导出类型，请使用测试用例导出文件"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 检测冲突
        conflicts = {"test_case_groups": [], "test_cases": []}

        # 分组冲突
        for g in data.get("test_case_groups", []):
            parent = None
            parent_path = g.get("parent_path", [])
            for pname in parent_path:
                try:
                    parent = TestCaseGroup.objects.get(
                        project=project, parent=parent, name=pname
                    )
                except TestCaseGroup.DoesNotExist:
                    parent = None
                    break
            if TestCaseGroup.objects.filter(
                project=project, parent=parent, name=g["name"]
            ).exists():
                conflicts["test_case_groups"].append({
                    "name": g["name"],
                    "parent_path": parent_path,
                    "reason": "同名分组已存在",
                })

        # 用例冲突
        for c in data.get("test_cases", []):
            if TestCase.objects.filter(
                project=project, name=c["name"]
            ).exists():
                conflicts["test_cases"].append({
                    "name": c["name"],
                    "reason": "同名测试用例已存在",
                })

        return Response({
            "source_project": data.get("project_name", ""),
            "version": data.get("version", ""),
            "summary": {
                "test_case_groups": len(data.get("test_case_groups", [])),
                "test_cases": len(data.get("test_cases", [])),
            },
            "conflicts": conflicts,
            "data": data,
        })

    # ------------------------------------------------------------------
    # 导入确认
    # ------------------------------------------------------------------
    @action(detail=False, methods=["post"], url_path="import/confirm")
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

        stats = {
            "test_case_groups": {"created": 0, "skipped": 0},
            "test_cases": {"created": 0, "updated": 0, "skipped": 0},
        }

        with transaction.atomic():
            # 1. 导入分组（按 parent_path 长度升序）
            groups_sorted = sorted(
                import_data.get("test_case_groups", []),
                key=lambda g: len(g.get("parent_path", [])),
            )
            for g in groups_sorted:
                parent = None
                for pname in g.get("parent_path", []):
                    try:
                        parent = TestCaseGroup.objects.get(
                            project=project, parent=parent, name=pname
                        )
                    except TestCaseGroup.DoesNotExist:
                        parent = None
                        break

                name = g["name"]
                existing = TestCaseGroup.objects.filter(
                    project=project, parent=parent, name=name
                ).first()

                if existing:
                    if conflict_strategy == "skip":
                        stats["test_case_groups"]["skipped"] += 1
                    elif conflict_strategy == "overwrite":
                        # 分组只有名称，无需更新
                        stats["test_case_groups"]["skipped"] += 1
                    else:  # keep_both
                        new_name = name
                        suffix = 1
                        while TestCaseGroup.objects.filter(
                            project=project, parent=parent, name=new_name
                        ).exists():
                            suffix += 1
                            new_name = f"{name} ({suffix})"
                        TestCaseGroup.objects.create(
                            project=project,
                            parent=parent,
                            name=new_name,
                            created_by=request.user if request.user and request.user.is_authenticated else None,
                        )
                        stats["test_case_groups"]["created"] += 1
                else:
                    TestCaseGroup.objects.create(
                        project=project,
                        parent=parent,
                        name=name,
                        created_by=request.user if request.user and request.user.is_authenticated else None,
                    )
                    stats["test_case_groups"]["created"] += 1

            # 2. 导入测试用例
            for c in import_data.get("test_cases", []):
                group = _resolve_group(project, c.get("group_path", []))
                existing = TestCase.objects.filter(
                    project=project, name=c["name"]
                ).first()

                case_fields = {
                    "description": c.get("description", ""),
                    "request_method": c.get("request_method", "GET"),
                    "request_url": c.get("request_url", ""),
                    "request_headers": c.get("request_headers", {}),
                    "request_body": c.get("request_body", {}),
                    "request_body_format": c.get("request_body_format", "json"),
                    "expected_status_code": c.get("expected_status_code", 200),
                    "validation_rules": c.get("validation_rules", []),
                    "extract_params": c.get("extract_params", []),
                    "upload_field_name": c.get("upload_field_name", ""),
                    "timeout": c.get("timeout"),
                    "group": group,
                }

                # 处理 Base64 文件
                file_base64 = c.get("upload_file_base64")
                file_name = c.get("upload_file_name", "upload.bin")

                if existing:
                    if conflict_strategy == "skip":
                        stats["test_cases"]["skipped"] += 1
                    elif conflict_strategy == "overwrite":
                        for k, v in case_fields.items():
                            setattr(existing, k, v)
                        if file_base64:
                            decoded = base64.b64decode(file_base64)
                            existing.upload_file.save(
                                file_name, ContentFile(decoded), save=False
                            )
                        existing.save()
                        stats["test_cases"]["updated"] += 1
                    else:  # keep_both
                        new_name = c["name"]
                        suffix = 1
                        while TestCase.objects.filter(
                            project=project, name=new_name
                        ).exists():
                            suffix += 1
                            new_name = f"{c['name']} ({suffix})"
                        new_case = TestCase.objects.create(
                            project=project,
                            name=new_name,
                            created_by=request.user if request.user and request.user.is_authenticated else None,
                            **case_fields,
                        )
                        if file_base64:
                            decoded = base64.b64decode(file_base64)
                            new_case.upload_file.save(
                                file_name, ContentFile(decoded), save=True
                            )
                        stats["test_cases"]["created"] += 1
                else:
                    new_case = TestCase.objects.create(
                        project=project,
                        name=c["name"],
                        created_by=request.user if request.user and request.user.is_authenticated else None,
                        **case_fields,
                    )
                    if file_base64:
                        decoded = base64.b64decode(file_base64)
                        new_case.upload_file.save(
                            file_name, ContentFile(decoded), save=True
                        )
                    stats["test_cases"]["created"] += 1

        return Response(stats)
