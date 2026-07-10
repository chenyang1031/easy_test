"""
模块 B：场景执行与测试报告结合 — 单测（SET_NULL、project 校验、服务、权限、列表筛选）。
"""

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from test_manager.models import (
    ApiGroup,
    ApiProject,
    Environment,
    Project,
    TestReport,
    TestScene,
    TestSceneExecution,
)
from test_manager.report.services import (
    SceneExecutionReportValidationError,
    build_scene_execution_report_content,
    save_scene_execution_test_report,
)


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class SceneExecutionReportTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner1", password="pw")
        self.other = User.objects.create_user(username="other1", password="pw")

        self.platform = Project.objects.create(name="P1", description="", created_by=self.owner)
        self.api_project = ApiProject.objects.create(
            platform_project=self.platform,
            name="API1",
            description="",
            created_by=self.owner,
        )
        ApiGroup.objects.create(project=self.api_project, name="默认", sort_order=0)
        self.env = Environment.objects.create(
            name="E1",
            project=self.platform,
            base_url="https://example.com",
        )
        self.scene = TestScene.objects.create(
            project=self.api_project,
            name="场景一",
            description="desc",
            created_by=self.owner,
        )

    def _execution(self, **kwargs):
        defaults = {
            "scene": self.scene,
            "status": TestSceneExecution.STATUS_SUCCESS,
            "environment": self.env,
            "created_by": self.owner,
            "node_results": [
                {
                    "node_id": 1,
                    "node_name": "N1",
                    "status": "passed",
                    "response": {"body": {"ok": True}},
                },
                {
                    "node_id": 2,
                    "node_name": "N2",
                    "status": "failed",
                    "reason": "断言失败",
                    "response": {"body": "x" * 5000},
                },
            ],
        }
        defaults.update(kwargs)
        return TestSceneExecution.objects.create(**defaults)

    def test_build_content_running_state(self):
        ex = self._execution(status=TestSceneExecution.STATUS_RUNNING, node_results=[])
        out = build_scene_execution_report_content(ex)
        self.assertIn("html", out)
        self.assertIn("json", out)
        self.assertEqual(out["json"]["execution"]["status"], "running")
        self.assertEqual(out["json"]["nodes"], [])

    def test_build_content_empty_nodes(self):
        ex = self._execution(node_results=[])
        self.assertEqual(build_scene_execution_report_content(ex)["json"]["nodes"], [])

    def test_validation_no_environment(self):
        ex = TestSceneExecution.objects.create(
            scene=self.scene,
            status=TestSceneExecution.STATUS_RUNNING,
            environment=None,
            created_by=self.owner,
        )
        with self.assertRaises(SceneExecutionReportValidationError):
            build_scene_execution_report_content(ex)

    def test_delete_execution_nullifies_report_fk(self):
        ex = self._execution()
        report = save_scene_execution_test_report(
            ex,
            self.owner,
            name="R1",
            description="",
            report_format="json",
            is_public=False,
        )
        self.assertEqual(report.scene_execution_id, ex.id)
        ex.delete()
        report.refresh_from_db()
        self.assertIsNone(report.scene_execution_id)
        self.assertTrue(TestReport.objects.filter(pk=report.pk).exists())

    def test_get_summary_scene_json_report(self):
        ex = self._execution()
        report = save_scene_execution_test_report(
            ex,
            self.owner,
            name="R2",
            description="",
            report_format="json",
            is_public=False,
        )
        s = report.get_summary()
        self.assertEqual(s.get("_source"), "scene_execution_report")
        self.assertEqual(s.get("scene_name"), "场景一")
        self.assertGreaterEqual(s.get("failed_nodes", 0), 1)

    def test_generate_report_permission_denied(self):
        ex = self._execution()
        url = reverse("generate_scene_execution_report", kwargs={"execution_id": ex.pk})
        self.client.force_login(self.other)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 403)

    def test_generate_report_owner_ok(self):
        ex = self._execution()
        url = reverse("generate_scene_execution_report", kwargs={"execution_id": ex.pk})
        self.client.force_login(self.owner)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

    def test_report_list_filter_scene_execution(self):
        ex = self._execution()
        save_scene_execution_test_report(
            ex,
            self.owner,
            name="SR",
            description="",
            report_format="html",
            is_public=False,
        )
        self.client.force_login(self.owner)
        url = reverse("test_report_list")
        r = self.client.get(url, {"report_type": "scene_execution"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "SR")
