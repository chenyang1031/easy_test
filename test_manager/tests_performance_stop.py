"""
性能测试任务「停止」接口单元测试：幂等、状态校验、URL 别名。
"""
from django.contrib.auth.models import User
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from test_manager.utils.performance_stop import _stderr_means_process_already_gone

from test_manager.models import (
    ApiGroup,
    ApiProject,
    ApiAsset,
    Environment,
    PerformanceTestTask,
    Project,
)


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class PerformanceStopAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="perf_stop_user", password="pw")
        self.client.force_authenticate(user=self.user)
        self.platform = Project.objects.create(name="平台P", description="", created_by=self.user)
        self.api_project = ApiProject.objects.create(
            platform_project=self.platform,
            name="API项目",
            description="",
            created_by=self.user,
        )
        self.group = ApiGroup.objects.create(project=self.api_project, name="G1", sort_order=1)
        self.asset = ApiAsset.objects.create(
            project=self.api_project,
            group=self.group,
            name="接口A",
            method="GET",
            url="/api/ping",
            status=ApiAsset.STATUS_ACTIVE,
            source=ApiAsset.SOURCE_MANUAL,
            created_by=self.user,
        )
        self.env = Environment.objects.create(
            name="环境1",
            project=self.platform,
            base_url="http://127.0.0.1:8080",
        )

    def _make_task(self, **kwargs):
        defaults = {
            "name": "压测任务",
            "project": self.platform,
            "environment": self.env,
            "interface": self.asset,
            "total_users": 1,
            "spawn_rate": 1,
            "run_time": 10,
            "status": PerformanceTestTask.STATUS_DRAFT,
            "creator": self.user,
        }
        defaults.update(kwargs)
        return PerformanceTestTask.objects.create(**defaults)

    def test_stop_idempotent_when_already_stopped(self):
        t = self._make_task(status=PerformanceTestTask.STATUS_STOPPED)
        r = self.client.post(f"/api/v1/performance/tasks/{t.id}/stop/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.data.get("already_stopped"))

    def test_stop_running_without_runner_info_succeeds(self):
        t = self._make_task(status=PerformanceTestTask.STATUS_RUNNING, runner_pid=None)
        r = self.client.post(
            f"/api/v1/performance/tasks/{t.id}/stop/",
            {"reason": "单元测试停止"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        t.refresh_from_db()
        self.assertEqual(t.status, PerformanceTestTask.STATUS_STOPPED)
        self.assertIn("单元测试", t.stop_reason)

    def test_stop_draft_returns_400(self):
        t = self._make_task(status=PerformanceTestTask.STATUS_DRAFT)
        r = self.client.post(f"/api/v1/performance/tasks/{t.id}/stop/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_singular_url_alias_matches_router(self):
        t = self._make_task(status=PerformanceTestTask.STATUS_RUNNING)
        r = self.client.post(f"/api/v1/performance/task/{t.id}/stop/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data.get("task", {}).get("status"), PerformanceTestTask.STATUS_STOPPED)

    def test_taskkill_stderr_cn_not_found_recognized(self):
        """Windows 中文：没有找到进程（与「找不到进程」措辞不同）应视为已退出。"""
        msg = '错误: 没有找到进程 "11700"。'
        self.assertTrue(_stderr_means_process_already_gone(msg))
