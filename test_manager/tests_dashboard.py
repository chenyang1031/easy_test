"""
仪表盘（模块 A）单元测试：场景统计、时序、可选 project_id 筛选、耗时展示等。
"""
from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse, resolve
from django.utils import timezone

from test_manager.models import (
    ApiGroup,
    ApiProject,
    Environment,
    Project,
    TestScene,
    TestSceneExecution,
)
from test_manager.views import (
    dashboard_scene_querysets,
    format_scene_execution_duration,
    generate_time_series_data,
    get_test_scene_execution_timeseries,
    get_test_scene_timeseries,
    growth_chart_has_any_data,
    parse_dashboard_project_id,
)


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class DashboardSceneTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="dash_tester", password="pw")
        self.client = Client()
        self.client.force_login(self.user)

        self.platform = Project.objects.create(
            name="平台P1",
            description="desc",
            created_by=self.user,
        )
        self.api_project = ApiProject.objects.create(
            platform_project=self.platform,
            name="API项目1",
            description="desc",
            created_by=self.user,
        )
        ApiGroup.objects.create(project=self.api_project, name="默认分组", sort_order=1)
        self.env = Environment.objects.create(
            name="测试环境",
            project=self.platform,
            base_url="https://example.com",
        )

    def _make_scene(self, name="场景A", deleted=False):
        return TestScene.objects.create(
            project=self.api_project,
            name=name,
            description="",
            created_by=self.user,
            is_deleted=deleted,
        )

    def _make_execution(self, scene, status=TestSceneExecution.STATUS_SUCCESS, finished=True):
        now = timezone.now()
        ex = TestSceneExecution.objects.create(
            scene=scene,
            status=status,
            environment=self.env,
            created_by=self.user,
        )
        if finished:
            TestSceneExecution.objects.filter(pk=ex.pk).update(
                finished_at=now,
            )
        ex.refresh_from_db()
        return ex

    # ── parse_dashboard_project_id ──

    def test_parse_dashboard_project_id_valid(self):
        req = self.client.get(reverse("dashboard"), {"project_id": str(self.platform.pk)}).wsgi_request
        self.assertEqual(parse_dashboard_project_id(req), self.platform.pk)

    def test_parse_dashboard_project_id_missing(self):
        req = self.client.get(reverse("dashboard")).wsgi_request
        self.assertIsNone(parse_dashboard_project_id(req))

    def test_parse_dashboard_project_id_invalid(self):
        req = self.client.get(reverse("dashboard"), {"project_id": "abc"}).wsgi_request
        self.assertIsNone(parse_dashboard_project_id(req))

    def test_parse_dashboard_project_id_nonexistent(self):
        req = self.client.get(reverse("dashboard"), {"project_id": "999999"}).wsgi_request
        self.assertIsNone(parse_dashboard_project_id(req))

    def test_parse_dashboard_project_id_negative(self):
        req = self.client.get(reverse("dashboard"), {"project_id": "-1"}).wsgi_request
        self.assertIsNone(parse_dashboard_project_id(req))

    # ── Dashboard API 端点测试 ──

    def _get_stats(self, params=None):
        """Helper: call dashboard stats API and return JSON."""
        url = reverse("dashboard-stats")
        if params:
            return self.client.get(url, params)
        return self.client.get(url)

    def test_dashboard_api_counts_and_scene_rows(self):
        s1 = self._make_scene("S1")
        s2 = self._make_scene("S2", deleted=True)
        self._make_execution(s1, TestSceneExecution.STATUS_SUCCESS)
        self._make_execution(s1, TestSceneExecution.STATUS_RUNNING, finished=False)

        r = self._get_stats()
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["stats"]["testScenes"], 1)
        self.assertEqual(data["stats"]["sceneExecutions"], 2)
        dist = data["executionStatusDist"]
        self.assertEqual(dist["running"], 1)
        self.assertEqual(dist["success"], 1)
        self.assertEqual(dist["failed"], 0)
        self.assertEqual(dist.get("partialSuccess", 0), 0)
        self.assertLessEqual(len(data["recentSceneExecutions"]), 5)
        self.assertTrue(any(ex["sceneName"] == "S1" for ex in data["recentSceneExecutions"]))

    def test_deleted_scene_excluded_from_count(self):
        self._make_scene("Del", deleted=True)
        r = self._get_stats()
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["stats"]["testScenes"], 0)

    def test_project_filter_optional(self):
        other = Project.objects.create(name="P2", description="d", created_by=self.user)
        other_api = ApiProject.objects.create(
            platform_project=other,
            name="API2",
            description="d",
            created_by=self.user,
        )
        ApiGroup.objects.create(project=other_api, name="g", sort_order=1)
        scene_a = self._make_scene("OnlyA")
        self._make_execution(scene_a)

        r = self._get_stats({"project_id": str(other.pk)})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["stats"]["testScenes"], 0)
        self.assertEqual(data["stats"]["sceneExecutions"], 0)

    def test_scene_execution_status_failed_counted(self):
        scene = self._make_scene()
        self._make_execution(scene, TestSceneExecution.STATUS_FAILED)
        r = self._get_stats()
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["executionStatusDist"]["failed"], 1)

    # ── 前端 Dashboard 页面渲染测试 ──

    def test_dashboard_page_renders(self):
        """Vue 挂载模板能正常渲染（200）"""
        r = self.client.get(reverse("dashboard"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "dashboard-mount")

    # ── 单元测试：helper 函数 ──

    def test_format_scene_execution_duration(self):
        scene = self._make_scene()
        ex = self._make_execution(scene)
        text = format_scene_execution_duration(ex)
        self.assertNotEqual(text, "执行中")
        ex2 = TestSceneExecution.objects.create(
            scene=scene,
            status=TestSceneExecution.STATUS_RUNNING,
            environment=self.env,
            created_by=self.user,
        )
        self.assertEqual(format_scene_execution_duration(ex2), "执行中")

    def test_growth_chart_has_any_data(self):
        empty = {"datasets": {"projects": [0, 0], "test_scenes": []}}
        self.assertFalse(growth_chart_has_any_data(empty))
        self.assertTrue(growth_chart_has_any_data({"datasets": {"projects": [0, 1]}}))

    def test_generate_time_series_includes_scene_keys(self):
        import pytz

        tz = pytz.timezone("UTC")
        payload = generate_time_series_data(mode="daily", tz=tz, project_id=None)
        self.assertIn("labels", payload)
        ds = payload["datasets"]
        self.assertIn("test_scenes", ds)
        self.assertIn("test_scene_executions", ds)
        self.assertEqual(len(ds["test_scenes"]), 7)

    def test_time_series_filters_and_buckets(self):
        import pytz

        tz = pytz.UTC
        scene = self._make_scene()
        ex = self._make_execution(scene)
        now = timezone.now().astimezone(tz)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        counts_exec = get_test_scene_execution_timeseries(
            start_date=start,
            count=7,
            period="day",
            tz=tz,
            project_id=None,
        )
        self.assertEqual(len(counts_exec), 7)
        self.assertGreaterEqual(sum(counts_exec), 1)

        counts_scene = get_test_scene_timeseries(
            start_date=start,
            count=7,
            period="day",
            tz=tz,
            project_id=None,
        )
        self.assertEqual(len(counts_scene), 7)

    def test_dashboard_scene_querysets(self):
        scene = self._make_scene()
        self._make_execution(scene)
        s_q, e_q = dashboard_scene_querysets(None)
        self.assertEqual(s_q.count(), 1)
        self.assertEqual(e_q.count(), 1)
        s_q2, e_q2 = dashboard_scene_querysets(self.platform.pk)
        self.assertEqual(s_q2.count(), 1)
        self.assertEqual(e_q2.count(), 1)

    def test_generate_time_series_monthly_yearly_modes(self):
        import pytz

        tz = pytz.UTC
        m = generate_time_series_data(mode="monthly", tz=tz)
        y = generate_time_series_data(mode="yearly", tz=tz)
        self.assertEqual(len(m["labels"]), 12)
        self.assertEqual(len(y["labels"]), 5)
        self.assertEqual(len(m["datasets"]["test_scenes"]), 12)

    def test_scene_execution_list_and_detail_urls(self):
        self.assertEqual(resolve("/scene-executions/").url_name, "scene_execution_list")
        scene = self._make_scene()
        ex = self._make_execution(scene)
        r = self.client.get(reverse("scene_execution_list"))
        self.assertEqual(r.status_code, 200)
        r2 = self.client.get(reverse("scene_execution_detail", kwargs={"pk": ex.pk}))
        self.assertEqual(r2.status_code, 200)
        self.assertContains(r2, ex.scene.name)
