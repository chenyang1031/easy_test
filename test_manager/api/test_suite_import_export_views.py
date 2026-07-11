"""测试套件导出/导入 ViewSet。"""

import base64
import json
from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from test_manager.models.project import Project
from test_manager.models.test_case import (
    TestCase, TestCaseGroup, TestSuite, TestSuiteCase, TestSuiteGroup,
)
from test_manager.models.environment import Environment

try:
    import yaml
except ImportError:
    yaml = None


EXPORT_VERSION = "1.0"
EXPORT_TYPE = "test-suites"


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


def _serialize_suite_group(group, path):
    return {
        "name": group.name,
        "parent_path": path[:-1],
    }


def _serialize_case_group(group, path):
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


def _serialize_suite(suite, suite_cases, case_name_map, env_map, group_path_map):
    test_cases_data = []
    for sc in suite_cases:
        case_name = case_name_map.get(sc.test_case_id, sc.test_case.name if sc.test_case else "")
        env_name = env_map.get(sc.environment_id) if sc.environment_id else None
        test_cases_data.append({
            "test_case_name": case_name,
            "environment_name": env_name,
            "order": sc.order,
        })
    return {
        "name": suite.name,
        "description": suite.description,
        "group_path": group_path_map.get(suite.group_id),
        "test_cases": test_cases_data,
    }


def _resolve_case_group(project, group_path):
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


def _resolve_suite_group(project, group_path):
    if not group_path:
        return None
    parent = None
    for name in group_path:
        try:
            parent = TestSuiteGroup.objects.get(
                project=project, parent=parent, name=name
            )
        except TestSuiteGroup.DoesNotExist:
            return None
    return parent


class TestSuiteImportExportViewSet(viewsets.ViewSet):

    # ------------------------------------------------------------------
    # 导出测试套件
    # ------------------------------------------------------------------
    @action(detail=False, methods=["post"], url_path="export")
    def export_test_suites(self, request):
        project_id = request.data.get("project_id")
        suite_ids = request.data.get("test_suite_ids")
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

        suites_qs = TestSuite.objects.filter(project=project)
        if suite_ids:
            suites_qs = suites_qs.filter(id__in=suite_ids)
        suites = suites_qs.order_by("id")

        if not suites.exists():
            return Response(
                {"detail": "没有找到可导出的测试套件"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ---- 收集 TestSuiteGroup（递归 parent 链） ----
        suite_group_ids = set()
        for s in suites:
            if s.group_id:
                suite_group_ids.add(s.group_id)
        added = set(suite_group_ids)
        while True:
            parents = set(
                TestSuiteGroup.objects.filter(id__in=added)
                .exclude(parent_id__isnull=True)
                .values_list("parent_id", flat=True)
            )
            new_parents = parents - added
            if not new_parents:
                break
            added.update(new_parents)
        suite_group_ids = added

        suite_groups = TestSuiteGroup.objects.filter(id__in=suite_group_ids).order_by("id")
        suite_group_path_map = {}
        for g in suite_groups:
            path = _get_group_path(g)
            suite_group_path_map[g.id] = path
        sorted_suite_groups = sorted(
            suite_groups, key=lambda g: len(suite_group_path_map[g.id])
        )
        suite_groups_data = [
            _serialize_suite_group(g, suite_group_path_map[g.id])
            for g in sorted_suite_groups
        ]

        # ---- 收集关联的 TestCase ----
        suite_case_ids = set()
        for s in suites:
            case_ids = s.test_cases.values_list("id", flat=True)
            suite_case_ids.update(case_ids)

        cases = TestCase.objects.filter(id__in=suite_case_ids).order_by("id")

        # 收集用例分组
        case_group_ids = set()
        for c in cases:
            if c.group_id:
                case_group_ids.add(c.group_id)
        added = set(case_group_ids)
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
        case_group_ids = added

        case_groups = TestCaseGroup.objects.filter(id__in=case_group_ids).order_by("id")
        case_group_path_map = {}
        for g in case_groups:
            path = _get_group_path(g)
            case_group_path_map[g.id] = path
        sorted_case_groups = sorted(
            case_groups, key=lambda g: len(case_group_path_map[g.id])
        )
        case_groups_data = [
            _serialize_case_group(g, case_group_path_map[g.id])
            for g in sorted_case_groups
        ]

        cases_data = [
            _serialize_test_case(c, case_group_path_map) for c in cases
        ]

        # ---- 收集关联的 Environment ----
        env_ids = set()
        for s in suites:
            env_id_list = TestSuiteCase.objects.filter(
                test_suite=s
            ).exclude(environment_id__isnull=True).values_list(
                "environment_id", flat=True
            )
            env_ids.update(env_id_list)

        environments = Environment.objects.filter(id__in=env_ids).order_by("id")
        env_map = {}
        for e in environments:
            env_map[e.id] = e.name
        envs_data = [_serialize_env(e) for e in environments]

        # ---- 序列化套件 ----
        case_name_map = {c.id: c.name for c in cases}
        suites_data = []
        for s in suites:
            scs = TestSuiteCase.objects.filter(test_suite=s).select_related(
                "test_case"
            ).order_by("order")
            suites_data.append(
                _serialize_suite(s, scs, case_name_map, env_map, suite_group_path_map)
            )

        # ---- 组装导出数据 ----
        export_data = {
            "version": EXPORT_VERSION,
            "export_type": EXPORT_TYPE,
            "project_name": project.name,
            "test_suite_groups": suite_groups_data,
            "test_case_groups": case_groups_data,
            "environments": envs_data,
            "test_cases": cases_data,
            "test_suites": suites_data,
        }

        filename = f"test_suites_{project.name}"

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
                {"detail": "不支持的导出类型，请使用测试套件导出文件"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 检测冲突
        conflicts = {
            "test_suite_groups": [],
            "test_case_groups": [],
            "environments": [],
            "test_cases": [],
            "test_suites": [],
        }

        # 套件分组冲突
        for g in data.get("test_suite_groups", []):
            parent = None
            parent_path = g.get("parent_path", [])
            for pname in parent_path:
                try:
                    parent = TestSuiteGroup.objects.get(
                        project=project, parent=parent, name=pname
                    )
                except TestSuiteGroup.DoesNotExist:
                    parent = None
                    break
            if TestSuiteGroup.objects.filter(
                project=project, parent=parent, name=g["name"]
            ).exists():
                conflicts["test_suite_groups"].append({
                    "name": g["name"],
                    "parent_path": parent_path,
                    "reason": "同名套件分组已存在",
                })

        # 用例分组冲突
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
                    "reason": "同名用例分组已存在",
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

        # 用例冲突
        for c in data.get("test_cases", []):
            if TestCase.objects.filter(
                project=project, name=c["name"]
            ).exists():
                conflicts["test_cases"].append({
                    "name": c["name"],
                    "reason": "同名测试用例已存在",
                })

        # 套件冲突
        for s in data.get("test_suites", []):
            if TestSuite.objects.filter(
                project=project, name=s["name"]
            ).exists():
                conflicts["test_suites"].append({
                    "name": s["name"],
                    "reason": "同名测试套件已存在",
                })

        return Response({
            "source_project": data.get("project_name", ""),
            "version": data.get("version", ""),
            "summary": {
                "test_suite_groups": len(data.get("test_suite_groups", [])),
                "test_case_groups": len(data.get("test_case_groups", [])),
                "environments": len(data.get("environments", [])),
                "test_cases": len(data.get("test_cases", [])),
                "test_suites": len(data.get("test_suites", [])),
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
            "test_suite_groups": {"created": 0, "skipped": 0},
            "test_case_groups": {"created": 0, "skipped": 0},
            "environments": {"created": 0, "updated": 0, "skipped": 0},
            "test_cases": {"created": 0, "updated": 0, "skipped": 0},
            "test_suites": {"created": 0, "updated": 0, "skipped": 0},
            "suite_cases": {"created": 0},
        }

        with transaction.atomic():
            user = request.user if request.user and request.user.is_authenticated else None

            # 1. 导入套件分组
            groups_sorted = sorted(
                import_data.get("test_suite_groups", []),
                key=lambda g: len(g.get("parent_path", [])),
            )
            for g in groups_sorted:
                parent = None
                for pname in g.get("parent_path", []):
                    try:
                        parent = TestSuiteGroup.objects.get(
                            project=project, parent=parent, name=pname
                        )
                    except TestSuiteGroup.DoesNotExist:
                        parent = None
                        break

                name = g["name"]
                existing = TestSuiteGroup.objects.filter(
                    project=project, parent=parent, name=name
                ).first()

                if existing:
                    if conflict_strategy == "skip":
                        stats["test_suite_groups"]["skipped"] += 1
                    elif conflict_strategy == "overwrite":
                        stats["test_suite_groups"]["skipped"] += 1
                    else:
                        new_name = name
                        suffix = 1
                        while TestSuiteGroup.objects.filter(
                            project=project, parent=parent, name=new_name
                        ).exists():
                            suffix += 1
                            new_name = f"{name} ({suffix})"
                        TestSuiteGroup.objects.create(
                            project=project, parent=parent,
                            name=new_name, created_by=user,
                        )
                        stats["test_suite_groups"]["created"] += 1
                else:
                    TestSuiteGroup.objects.create(
                        project=project, parent=parent,
                        name=name, created_by=user,
                    )
                    stats["test_suite_groups"]["created"] += 1

            # 2. 导入用例分组
            case_groups_sorted = sorted(
                import_data.get("test_case_groups", []),
                key=lambda g: len(g.get("parent_path", [])),
            )
            for g in case_groups_sorted:
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
                        stats["test_case_groups"]["skipped"] += 1
                    else:
                        new_name = name
                        suffix = 1
                        while TestCaseGroup.objects.filter(
                            project=project, parent=parent, name=new_name
                        ).exists():
                            suffix += 1
                            new_name = f"{name} ({suffix})"
                        TestCaseGroup.objects.create(
                            project=project, parent=parent,
                            name=new_name, created_by=user,
                        )
                        stats["test_case_groups"]["created"] += 1
                else:
                    TestCaseGroup.objects.create(
                        project=project, parent=parent,
                        name=name, created_by=user,
                    )
                    stats["test_case_groups"]["created"] += 1

            # 3. 导入环境
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

            # 4. 导入测试用例（维护 case_name_map 用于套件引用）
            case_name_map = {}
            for c in import_data.get("test_cases", []):
                group = _resolve_case_group(
                    project, c.get("group_path", [])
                )
                original_name = c["name"]
                existing = TestCase.objects.filter(
                    project=project, name=original_name
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

                file_base64 = c.get("upload_file_base64")
                file_name = c.get("upload_file_name", "upload.bin")

                if existing:
                    if conflict_strategy == "skip":
                        case_name_map[original_name] = existing.name
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
                        case_name_map[original_name] = existing.name
                        stats["test_cases"]["updated"] += 1
                    else:
                        new_name = original_name
                        suffix = 1
                        while TestCase.objects.filter(
                            project=project, name=new_name
                        ).exists():
                            suffix += 1
                            new_name = f"{original_name} ({suffix})"
                        new_case = TestCase.objects.create(
                            project=project, name=new_name,
                            created_by=user, **case_fields,
                        )
                        if file_base64:
                            decoded = base64.b64decode(file_base64)
                            new_case.upload_file.save(
                                file_name, ContentFile(decoded), save=True
                            )
                        case_name_map[original_name] = new_name
                        stats["test_cases"]["created"] += 1
                else:
                    new_case = TestCase.objects.create(
                        project=project, name=original_name,
                        created_by=user, **case_fields,
                    )
                    if file_base64:
                        decoded = base64.b64decode(file_base64)
                        new_case.upload_file.save(
                            file_name, ContentFile(decoded), save=True
                        )
                    case_name_map[original_name] = original_name
                    stats["test_cases"]["created"] += 1

            # 5. 导入测试套件 + 关联
            for s in import_data.get("test_suites", []):
                suite_group = _resolve_suite_group(
                    project, s.get("group_path", [])
                )
                existing_suite = TestSuite.objects.filter(
                    project=project, name=s["name"]
                ).first()

                if existing_suite:
                    if conflict_strategy == "skip":
                        stats["test_suites"]["skipped"] += 1
                        continue
                    elif conflict_strategy == "overwrite":
                        existing_suite.description = s.get("description", "")
                        existing_suite.group = suite_group
                        existing_suite.save()
                        existing_suite.test_cases.through.objects.filter(
                            test_suite=existing_suite
                        ).delete()
                        suite_obj = existing_suite
                        stats["test_suites"]["updated"] += 1
                    else:
                        new_name = s["name"]
                        suffix = 1
                        while TestSuite.objects.filter(
                            project=project, name=new_name
                        ).exists():
                            suffix += 1
                            new_name = f"{s['name']} ({suffix})"
                        suite_obj = TestSuite.objects.create(
                            project=project, name=new_name,
                            description=s.get("description", ""),
                            group=suite_group, created_by=user,
                        )
                        stats["test_suites"]["created"] += 1
                else:
                    suite_obj = TestSuite.objects.create(
                        project=project, name=s["name"],
                        description=s.get("description", ""),
                        group=suite_group, created_by=user,
                    )
                    stats["test_suites"]["created"] += 1

                # 创建 TestSuiteCase 关联
                for tc in s.get("test_cases", []):
                    tc_name = tc.get("test_case_name", "")
                    actual_name = case_name_map.get(tc_name, tc_name)
                    case = TestCase.objects.filter(
                        project=project, name=actual_name
                    ).first()
                    if not case:
                        continue

                    env = None
                    env_name = tc.get("environment_name")
                    if env_name:
                        env = Environment.objects.filter(
                            project=project, name=env_name
                        ).first()

                    TestSuiteCase.objects.create(
                        test_suite=suite_obj,
                        test_case=case,
                        environment=env,
                        order=tc.get("order", 0),
                    )
                    stats["suite_cases"]["created"] += 1

        return Response(stats)
