"""
Dashboard API — 提供仪表盘各面板所需聚合数据。
"""
import pytz
from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Q
from django.utils import timezone
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from test_manager.models import (
    Project, TestCase, TestSuite, TestRun,
    TestReport, TestScene, TestSceneExecution,
)


def _parse_dashboard_project_id(request):
    """从 GET 参数解析可选的 project_id 筛选。"""
    raw = request.GET.get("project_id")
    if raw is not None:
        try:
            return int(raw)
        except (ValueError, TypeError):
            return None
    return None


def _dashboard_scene_querysets(project_id):
    """
    返回 (scene_qs, execution_qs)，均已按项目口径筛选。
    TestScene 仅包含 is_deleted=False。
    """
    scene_qs = TestScene.objects.filter(is_deleted=False)
    execution_qs = TestSceneExecution.objects.all()
    if project_id is not None:
        scene_qs = scene_qs.filter(project__platform_project_id=project_id)
        execution_qs = execution_qs.filter(scene__project__platform_project_id=project_id)
    return scene_qs, execution_qs


def _format_scene_execution_duration(execution):
    """耗时展示：finished_at - started_at；未完成则「执行中」。"""
    if execution.finished_at is None or execution.started_at is None:
        return "执行中"
    delta = execution.finished_at - execution.started_at
    total = int(delta.total_seconds())
    if total < 0:
        return "执行中"
    if total < 60:
        return f"{total}秒"
    m, s = divmod(total, 60)
    if m < 60:
        return f"{m}分{s}秒"
    h, m = divmod(m, 60)
    return f"{h}小时{m}分{s}秒"


def _generate_date_labels(start_date, period, count):
    """生成时间轴标签。"""
    labels = []
    current = start_date
    if period == "day":
        for _ in range(count):
            labels.append(current.strftime("%b %d").lstrip("0").replace(" 0", " "))
            current += timedelta(days=1)
    elif period == "month":
        for i in range(count):
            labels.append(f"{i + 1}月")
    elif period == "year":
        for i in range(count):
            labels.append(str(start_date.year + i))
    return labels


def _get_queryset_timeseries(queryset, start_date, count, period, tz, date_field="created_at"):
    """对任意 QuerySet 按时间桶聚合。"""
    now = timezone.now().astimezone(tz)
    utc_start = start_date.astimezone(pytz.utc)
    utc_end = now.astimezone(pytz.utc)
    range_kw = {f"{date_field}__range": (utc_start, utc_end)}
    results = queryset.filter(**range_kw).values_list(date_field, flat=True)
    counts = [0] * count
    for dt in results:
        local_dt = dt.astimezone(tz)
        if period == "day":
            diff = (local_dt.date() - start_date.date()).days
        elif period == "month":
            diff = local_dt.month - 1
        elif period == "year":
            diff = local_dt.year - start_date.year
        else:
            continue
        if 0 <= diff < count:
            counts[diff] += 1
    return counts


def _get_model_timeseries(model, start_date, count, period, tz):
    return _get_queryset_timeseries(model.objects.all(), start_date, count, period, tz, "created_at")


def _get_test_scene_timeseries(start_date, count, period, tz, project_id=None):
    qs = TestScene.objects.filter(is_deleted=False)
    if project_id is not None:
        qs = qs.filter(project__platform_project_id=project_id)
    return _get_queryset_timeseries(qs, start_date, count, period, tz, "created_at")


def _get_test_scene_execution_timeseries(start_date, count, period, tz, project_id=None):
    qs = TestSceneExecution.objects.all()
    if project_id is not None:
        qs = qs.filter(scene__project__platform_project_id=project_id)
    return _get_queryset_timeseries(qs, start_date, count, period, tz, "created_at")


def _generate_time_series_data(mode, tz, project_id=None):
    """生成指定模式（daily/monthly/yearly）的时序数据。"""
    now = timezone.now().astimezone(tz)
    if mode == "daily":
        count = 7
        start_date = now - timedelta(days=count - 1)
        period = "day"
    elif mode == "monthly":
        start_date = now.replace(month=1, day=1)
        count = 12
        period = "month"
    elif mode == "yearly":
        current_year = now.year
        start_date = now.replace(year=current_year - 4, month=1, day=1)
        count = 5
        period = "year"
    else:
        raise ValueError("Invalid mode")

    labels = _generate_date_labels(start_date, period, count)
    data = {
        "projects": _get_model_timeseries(Project, start_date, count, period, tz),
        "test_cases": _get_model_timeseries(TestCase, start_date, count, period, tz),
        "test_suites": _get_model_timeseries(TestSuite, start_date, count, period, tz),
        "test_runs": _get_model_timeseries(TestRun, start_date, count, period, tz),
        "test_reports": _get_model_timeseries(TestReport, start_date, count, period, tz),
        "test_scenes": _get_test_scene_timeseries(start_date, count, period, tz, project_id=project_id),
        "test_scene_executions": _get_test_scene_execution_timeseries(
            start_date, count, period, tz, project_id=project_id
        ),
    }
    return {"labels": labels, "datasets": data}


class DashboardStatsView(APIView):
    """仪表盘聚合数据 API。

    GET /api/v1/dashboard/stats/?page=1&project_id=<id>
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tz = pytz.timezone(settings.TIME_ZONE)
        project_id = _parse_dashboard_project_id(request)
        scene_qs, execution_qs = _dashboard_scene_querysets(project_id)

        # ── 统计卡片 ──
        stats = {
            "projects": Project.objects.count(),
            "testCases": TestCase.objects.count(),
            "testSuites": TestSuite.objects.count(),
            "testRuns": TestRun.objects.count(),
            "reports": TestReport.objects.count(),
            "testScenes": scene_qs.count(),
            "sceneExecutions": execution_qs.count(),
        }

        # ── 场景执行状态分布 ──
        status_dist = execution_qs.aggregate(
            running=Count("id", filter=Q(status=TestSceneExecution.STATUS_RUNNING)),
            success=Count("id", filter=Q(status=TestSceneExecution.STATUS_SUCCESS)),
            failed=Count("id", filter=Q(status=TestSceneExecution.STATUS_FAILED)),
            partial_success=Count("id", filter=Q(status=TestSceneExecution.STATUS_PARTIAL_SUCCESS)),
        )
        execution_status_dist = {
            "running": status_dist.get("running") or 0,
            "success": status_dist.get("success") or 0,
            "failed": status_dist.get("failed") or 0,
            "partialSuccess": status_dist.get("partial_success") or 0,
        }

        # ── 增长趋势 ──
        daily = _generate_time_series_data("daily", tz, project_id=project_id)
        monthly = _generate_time_series_data("monthly", tz, project_id=project_id)
        yearly = _generate_time_series_data("yearly", tz, project_id=project_id)

        # ── 最近测试运行（分页） ──
        page = request.GET.get("page", 1)
        try:
            page = int(page)
        except (ValueError, TypeError):
            page = 1
        all_runs = TestRun.objects.select_related("project", "environment").order_by("-created_at")
        paginator = Paginator(all_runs, 5)
        try:
            runs_page = paginator.page(page)
        except (PageNotAnInteger, EmptyPage):
            runs_page = paginator.page(1)

        recent_test_runs = []
        for run in runs_page.object_list:
            recent_test_runs.append({
                "id": run.pk,
                "name": run.name,
                "projectName": run.project.name if run.project else "",
                "environmentName": run.environment.name if run.environment else "",
                "status": run.status,
                "createdAt": run.created_at.astimezone(tz).strftime("%Y-%m-%d %H:%M") if run.created_at else "",
                "detailUrl": f"/test-suites-vue/#/test-runs/{run.pk}",
            })

        # ── 最近场景执行 ──
        recent_scene_execs = list(
            execution_qs.select_related("scene", "environment")
            .order_by("-created_at")[:5]
        )
        recent_scene_executions = []
        for ex in recent_scene_execs:
            recent_scene_executions.append({
                "executionId": ex.id,
                "sceneId": ex.scene_id,
                "sceneName": ex.scene.name,
                "environmentName": ex.environment.name if ex.environment else "—",
                "status": ex.status,
                "durationDisplay": _format_scene_execution_duration(ex),
                "createdAt": ex.created_at.astimezone(tz).strftime("%Y-%m-%d %H:%M") if ex.created_at else "",
                "startedAt": ex.started_at.astimezone(tz).strftime("%Y-%m-%d %H:%M") if ex.started_at else "",
            })

        # ── 活动时间线 ──
        activities = []
        for run in TestRun.objects.all().order_by("-created_at")[:10]:
            activities.append({
                "action": run.name.split(":")[0] if ":" in run.name else run.name,
                "timestamp": run.created_at.astimezone(tz).strftime("%Y-%m-%d %H:%M") if run.created_at else "",
                "description": f"{run.name} 执行结果为：{run.status}",
                "status": run.status,
            })

        return Response({
            "stats": stats,
            "executionStatusDist": execution_status_dist,
            "trends": {
                "week": daily,
                "month": monthly,
                "year": yearly,
            },
            "recentTestRuns": {
                "results": recent_test_runs,
                "total": paginator.count,
                "totalPages": paginator.num_pages,
                "currentPage": runs_page.number,
            },
            "recentSceneExecutions": recent_scene_executions,
            "activities": activities,
        })
