"""
测试用例 & 测试套件导入/导出 — 自测脚本。
使用 DRF APIClient + force_authenticate 测试所有端点。
"""
import base64
import json
import tempfile
import os

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

from rest_framework.test import APIClient

from test_manager.models.project import Project
from test_manager.models.test_case import (
    TestCase as TC, TestCaseGroup, TestSuite, TestSuiteCase, TestSuiteGroup,
)
from test_manager.models.environment import Environment


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class TestCaseSuiteImportExportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="pw")
        self.client = APIClient(SERVER_NAME='127.0.0.1')
        self.client.force_authenticate(user=self.user)

        self.project = Project.objects.create(
            name="TestProject", description="desc", created_by=self.user
        )

        # 用例分组层级
        self.case_group_root = TestCaseGroup.objects.create(
            name="Root", project=self.project, created_by=self.user
        )
        self.case_group_child = TestCaseGroup.objects.create(
            name="Child", project=self.project,
            parent=self.case_group_root, created_by=self.user
        )

        # 测试用例
        self.case1 = TC.objects.create(
            name="Case1", project=self.project, group=self.case_group_child,
            request_method="GET", request_url="/api/users",
            request_headers={"X-Token": "abc"},
            expected_status_code=200,
            validation_rules=[{"field": "status", "op": "eq", "value": 200}],
            extract_params=[{"name": "user_id", "source": "body", "path": "$.id"}],
            created_by=self.user,
        )
        self.case2 = TC.objects.create(
            name="Case2", project=self.project,
            request_method="POST", request_url="/api/users",
            request_body={"name": "test"},
            request_body_format="json",
            expected_status_code=201,
            created_by=self.user,
        )

        # 套件分组
        self.suite_group = TestSuiteGroup.objects.create(
            name="SuiteGroup", project=self.project, created_by=self.user
        )

        # 环境
        self.env = Environment.objects.create(
            name="DevEnv", project=self.project,
            base_url="https://dev.example.com",
            variables={"token": ""},
        )

        # 套件
        self.suite = TestSuite.objects.create(
            name="MySuite", project=self.project,
            group=self.suite_group, description="A test suite",
            created_by=self.user,
        )
        TestSuiteCase.objects.create(
            test_suite=self.suite, test_case=self.case1,
            environment=self.env, order=0,
        )
        TestSuiteCase.objects.create(
            test_suite=self.suite, test_case=self.case2,
            order=1,
        )

    # ==================================================================
    # 测试用例导出
    # ==================================================================

    def test_1_export_test_cases_json(self):
        resp = self.client.post("/api/v1/test-cases/export/", {
            "project_id": self.project.id,
            "format": "json",
        }, format="json")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["format"], "json")
        content = data["content"]
        self.assertEqual(content["export_type"], "test-cases")
        self.assertEqual(content["version"], "1.0")
        self.assertEqual(content["project_name"], "TestProject")
        # 分组: Root + Child = 2
        self.assertEqual(len(content["test_case_groups"]), 2)
        # 用例: Case1 + Case2 = 2
        self.assertEqual(len(content["test_cases"]), 2)

        # 验证字段
        c1 = next(c for c in content["test_cases"] if c["name"] == "Case1")
        self.assertEqual(c1["request_method"], "GET")
        self.assertEqual(c1["request_url"], "/api/users")
        self.assertEqual(c1["expected_status_code"], 200)
        self.assertEqual(c1["group_path"], ["Root", "Child"])
        self.assertEqual(len(c1["validation_rules"]), 1)
        self.assertEqual(len(c1["extract_params"]), 1)

        c2 = next(c for c in content["test_cases"] if c["name"] == "Case2")
        self.assertIsNone(c2["group_path"])

    def test_2_export_test_cases_with_file_base64(self):
        # 给 case1 添加一个上传文件
        test_content = b"hello world test file content"
        self.case1.upload_file.save(
            "test_upload.txt", ContentFile(test_content), save=True
        )
        self.case1.upload_field_name = "file"
        self.case1.save()

        resp = self.client.post("/api/v1/test-cases/export/", {
            "project_id": self.project.id,
            "format": "json",
        }, format="json")
        self.assertEqual(resp.status_code, 200)
        content = resp.json()["content"]
        c1 = next(c for c in content["test_cases"] if c["name"] == "Case1")
        self.assertIn("upload_file_base64", c1)
        self.assertIn("upload_file_name", c1)
        # 验证 Base64 解码正确
        decoded = base64.b64decode(c1["upload_file_base64"])
        self.assertEqual(decoded, test_content)
        self.assertEqual(c1["upload_field_name"], "file")

    # ==================================================================
    # 测试用例导入
    # ==================================================================

    def test_3_import_test_cases_preview_conflicts(self):
        # 先导出
        resp = self.client.post("/api/v1/test-cases/export/", {
            "project_id": self.project.id,
            "format": "json",
        }, format="json")
        export_content = resp.json()["content"]

        # 将导出内容作为文件上传预览
        from io import BytesIO
        from django.core.files.uploadedfile import SimpleUploadedFile

        file_bytes = json.dumps(export_content).encode("utf-8")
        upload = SimpleUploadedFile(
            "test_cases.json", file_bytes, content_type="application/json"
        )
        resp = self.client.post(
            "/api/v1/test-cases/import/preview",
            {"file": upload, "project_id": str(self.project.id)},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 200)
        preview = resp.json()
        self.assertEqual(preview["source_project"], "TestProject")
        self.assertEqual(preview["summary"]["test_cases"], 2)
        self.assertEqual(preview["summary"]["test_case_groups"], 2)

        # 同项目导入，所有用例和分组应都有冲突
        self.assertEqual(len(preview["conflicts"]["test_case_groups"]), 2)
        self.assertEqual(len(preview["conflicts"]["test_cases"]), 2)

    def test_4_import_test_cases_skip(self):
        resp = self.client.post("/api/v1/test-cases/export/", {
            "project_id": self.project.id,
            "format": "json",
        }, format="json")
        export_content = resp.json()["content"]
        preview_data = export_content

        resp = self.client.post("/api/v1/test-cases/import/confirm", {
            "project_id": self.project.id,
            "data": preview_data,
            "default_conflict_strategy": "skip",
        }, format="json")
        self.assertEqual(resp.status_code, 200)
        stats = resp.json()
        # 全部跳过
        self.assertEqual(stats["test_cases"]["skipped"], 2)
        self.assertEqual(stats["test_cases"]["created"], 0)
        self.assertEqual(stats["test_case_groups"]["skipped"], 2)

    def test_5_import_test_cases_overwrite(self):
        resp = self.client.post("/api/v1/test-cases/export/", {
            "project_id": self.project.id,
            "format": "json",
        }, format="json")
        export_content = resp.json()["content"]

        # 修改导出数据中的 URL
        for c in export_content["test_cases"]:
            if c["name"] == "Case1":
                c["request_url"] = "/api/users/v2"

        resp = self.client.post("/api/v1/test-cases/import/confirm", {
            "project_id": self.project.id,
            "data": export_content,
            "default_conflict_strategy": "overwrite",
        }, format="json")
        self.assertEqual(resp.status_code, 200)
        stats = resp.json()
        self.assertEqual(stats["test_cases"]["updated"], 2)
        self.assertEqual(stats["test_cases"]["created"], 0)

        # 验证 URL 被覆盖
        self.case1.refresh_from_db()
        self.assertEqual(self.case1.request_url, "/api/users/v2")

    def test_6_import_test_cases_keep_both(self):
        resp = self.client.post("/api/v1/test-cases/export/", {
            "project_id": self.project.id,
            "format": "json",
        }, format="json")
        export_content = resp.json()["content"]

        resp = self.client.post("/api/v1/test-cases/import/confirm", {
            "project_id": self.project.id,
            "data": export_content,
            "default_conflict_strategy": "keep_both",
        }, format="json")
        self.assertEqual(resp.status_code, 200)
        stats = resp.json()
        self.assertEqual(stats["test_cases"]["created"], 2)
        self.assertEqual(stats["test_case_groups"]["created"], 2)

        # 验证新名称
        self.assertTrue(
            TC.objects.filter(project=self.project, name="Case1 (2)").exists()
        )
        self.assertTrue(
            TC.objects.filter(project=self.project, name="Case2 (2)").exists()
        )

    # ==================================================================
    # 测试套件导出
    # ==================================================================

    def test_7_export_test_suites_json(self):
        resp = self.client.post("/api/v1/test-suites/export/", {
            "project_id": self.project.id,
            "format": "json",
        }, format="json")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["format"], "json")
        content = data["content"]
        self.assertEqual(content["export_type"], "test-suites")
        self.assertEqual(content["project_name"], "TestProject")

        # 套件分组 1
        self.assertEqual(len(content["test_suite_groups"]), 1)
        # 环境 1
        self.assertEqual(len(content["environments"]), 1)
        # 用例 2
        self.assertEqual(len(content["test_cases"]), 2)
        # 套件 1
        self.assertEqual(len(content["test_suites"]), 1)

        suite = content["test_suites"][0]
        self.assertEqual(suite["name"], "MySuite")
        self.assertEqual(suite["group_path"], ["SuiteGroup"])
        self.assertEqual(len(suite["test_cases"]), 2)
        self.assertEqual(suite["test_cases"][0]["test_case_name"], "Case1")
        self.assertEqual(suite["test_cases"][0]["environment_name"], "DevEnv")
        self.assertEqual(suite["test_cases"][0]["order"], 0)
        self.assertEqual(suite["test_cases"][1]["test_case_name"], "Case2")
        self.assertIsNone(suite["test_cases"][1]["environment_name"])
        self.assertEqual(suite["test_cases"][1]["order"], 1)

    # ==================================================================
    # 测试套件导入
    # ==================================================================

    def test_8_import_test_suites_full_cycle(self):
        # 导出
        resp = self.client.post("/api/v1/test-suites/export/", {
            "project_id": self.project.id,
            "format": "json",
        }, format="json")
        export_content = resp.json()["content"]

        # 创建新项目
        new_project = Project.objects.create(
            name="NewProject", description="", created_by=self.user
        )

        # 导入到新项目
        resp = self.client.post("/api/v1/test-suites/import/confirm", {
            "project_id": new_project.id,
            "data": export_content,
            "default_conflict_strategy": "skip",
        }, format="json")
        self.assertEqual(resp.status_code, 200)
        stats = resp.json()

        # 全部创建
        self.assertEqual(stats["test_suite_groups"]["created"], 1)
        self.assertEqual(stats["test_case_groups"]["created"], 2)
        self.assertEqual(stats["environments"]["created"], 1)
        self.assertEqual(stats["test_cases"]["created"], 2)
        self.assertEqual(stats["test_suites"]["created"], 1)
        self.assertEqual(stats["suite_cases"]["created"], 2)

        # 验证新项目中数据
        self.assertEqual(
            TestSuite.objects.filter(project=new_project).count(), 1
        )
        new_suite = TestSuite.objects.get(project=new_project, name="MySuite")
        self.assertEqual(new_suite.test_cases.count(), 2)

        # 验证顺序
        tscs = TestSuiteCase.objects.filter(test_suite=new_suite).order_by("order")
        self.assertEqual(tscs[0].test_case.name, "Case1")
        self.assertEqual(tscs[0].order, 0)
        self.assertIsNotNone(tscs[0].environment)
        self.assertEqual(tscs[1].test_case.name, "Case2")
        self.assertEqual(tscs[1].order, 1)

    def test_9_import_suites_with_file_base64(self):
        # 给 case1 添加文件
        test_content = b"file data for suite test"
        self.case1.upload_file.save(
            "suite_test.bin", ContentFile(test_content), save=True
        )
        self.case1.upload_field_name = "doc"
        self.case1.save()

        # 导出
        resp = self.client.post("/api/v1/test-suites/export/", {
            "project_id": self.project.id,
            "format": "json",
        }, format="json")
        export_content = resp.json()["content"]

        # 验证导出中包含 Base64
        c1 = next(c for c in export_content["test_cases"] if c["name"] == "Case1")
        self.assertIn("upload_file_base64", c1)

        # 导入到新项目
        new_project = Project.objects.create(
            name="FileProject", description="", created_by=self.user
        )
        resp = self.client.post("/api/v1/test-suites/import/confirm", {
            "project_id": new_project.id,
            "data": export_content,
            "default_conflict_strategy": "skip",
        }, format="json")
        self.assertEqual(resp.status_code, 200)

        # 验证文件被还原
        imported_case = TC.objects.get(project=new_project, name="Case1")
        self.assertTrue(imported_case.upload_file)
        imported_case.upload_file.open("rb")
        self.assertEqual(imported_case.upload_file.read(), test_content)
        imported_case.upload_file.close()
        self.assertEqual(imported_case.upload_field_name, "doc")
