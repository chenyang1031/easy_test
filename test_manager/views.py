import datetime
import json
import ast
import logging
import os
import time
import time
import traceback
import pytz

logger = logging.getLogger(__name__)
from datetime import timedelta
from urllib.parse import urljoin

from django.urls import reverse

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.middleware.csrf import get_token
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.files.storage import default_storage
from django.views.decorators.http import require_POST,require_GET

from .async_executor import execute_test_suite_async, execute_test_case_async
from .gen_data import auto_gen_data
from .models import (
    Project, Environment, TestCase, TestSuite,
    TestSuiteCase, TestRun, TestResult, EmailConfig, TestSuiteGroup, TestCaseGroup, TestReport, TestSuiteRun, MockData,
    TaskExecutionLog, ScheduledTask, ParameterConfig, ApiAsset, ApiProject, ApiGroup, ApiHistory, TestScene,
    TestSceneExecution,
)
from .forms import (
    ProjectForm, EnvironmentForm, TestCaseForm, TestSuiteForm,
    TestRunForm, EmailConfigForm, TestEmailForm, TestSuiteGroupForm, TestCaseGroupForm, GenerateReportForm,
    MockDataForm, ScheduledTaskForm, ParameterConfigForm, ApiAssetForm, ApiGroupForm
)
from .httprunner_executor import execute_test_case, execute_test_suite
from .scheduler import TaskScheduler
from .tasks import execute_scheduled_test_suite

# -----------------------------------------------------------------------------
# 仪表盘 - 测试场景编排（模块 A）
# 可选功能：GET project_id 为业务 Project 主键，通过 ApiProject.platform_project 关联筛选场景维度；
# 非法或缺失时不筛选（全局仪表盘）。参数经整型校验，避免 SQL 注入。
# 性能：最近场景执行列表固定 LIMIT，查询使用 select_related；执行表索引含 (scene, created_at)、(status, created_at)，
# 按 -created_at 取前 N 条时优化器可走 created_at 相关路径，避免无谓全表扫描（见模型 Meta.indexes）。
# -----------------------------------------------------------------------------


def parse_dashboard_project_id(request):
    """
    可选功能：解析 GET ?project_id= 为业务 Project.id。
    无参数、非正整数或项目不存在时返回 None，表示不筛选（全局仪表盘无项目上下文时的降级行为）。
    """
    raw = request.GET.get("project_id")
    if raw is None or raw == "":
        return None
    try:
        pid = int(raw)
    except (TypeError, ValueError):
        return None
    if pid <= 0:
        return None
    if not Project.objects.filter(pk=pid).exists():
        return None
    return pid


def dashboard_scene_querysets(project_id):
    """
    返回 (scene_qs, execution_qs)，均已按项目口径筛选（若 project_id 为 None 则全量）。
    TestScene 仅包含 is_deleted=False（与业务「未删除场景」一致）。
    """
    scene_qs = TestScene.objects.filter(is_deleted=False)
    execution_qs = TestSceneExecution.objects.all()
    if project_id is not None:
        scene_qs = scene_qs.filter(project__platform_project_id=project_id)
        execution_qs = execution_qs.filter(scene__project__platform_project_id=project_id)
    return scene_qs, execution_qs


def format_scene_execution_duration(execution):
    """耗时展示：finished_at - created_at；未完成或无结束时间则「执行中」。"""
    if execution.finished_at is None or execution.created_at is None:
        return "执行中"
    delta = execution.finished_at - execution.created_at
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


def growth_chart_has_any_data(daily_payload):
    """判断周视图时序中是否至少有一条序列含非零值，用于前端「暂无数据」提示。"""
    datasets = daily_payload.get("datasets") or {}
    for series in datasets.values():
        if series and any((x or 0) > 0 for x in series):
            return True
    return False


def paginate_queryset(request, queryset, per_page=10):
    if not queryset.ordered:
        queryset = queryset.order_by("id")
    page = request.GET.get('page', 1)
    paginator = Paginator(queryset, per_page)

    try:
        paginated_queryset = paginator.page(page)
    except PageNotAnInteger:
        paginated_queryset = paginator.page(1)
    except EmptyPage:
        paginated_queryset = paginator.page(paginator.num_pages)

    return paginated_queryset


def _environment_list_rows_for_vue(environments_page):
    """环境列表页 Vue 表格行（含操作链接，与 Django url 一致）。"""
    rows = []
    for e in environments_page.object_list:
        rows.append(
            {
                "id": e.pk,
                "name": e.name,
                "projectId": e.project_id,
                "projectName": e.project.name,
                "baseUrl": e.base_url,
                "createdAt": e.created_at.strftime("%Y-%m-%d %H:%M"),
                "urls": {
                    "detail": reverse("environment_detail", args=[e.pk]),
                    "edit": reverse("environment_edit", args=[e.pk]),
                    "delete": reverse("environment_delete", args=[e.pk]),
                    "project": reverse("project_detail", args=[e.project_id]),
                },
            }
        )
    return rows


def _environment_detail_vue_payload(environment, recent_scene_executions, test_runs_slice):
    """环境详情页 Vue 初始数据（接口路径使用相对 URL，由前端拼接）。"""
    env_vars = environment.variables or {}
    variables_rows = []
    for k, v in env_vars.items():
        if isinstance(v, (dict, list)):
            val_str = json.dumps(v, ensure_ascii=False)
        else:
            val_str = str(v)
        variables_rows.append({"key": k, "value": val_str})

    scene_rows = []
    orch = reverse("test_scene_orchestrator")
    for ex in recent_scene_executions:
        scene_rows.append(
            {
                "id": ex.id,
                "sceneId": ex.scene_id,
                "sceneName": ex.scene.name,
                "status": ex.status,
                "createdAt": ex.created_at.strftime("%Y-%m-%d %H:%M"),
                "durationMs": ex.duration_ms,
                "execUrl": f"{orch}#/scenes/{ex.scene_id}/executions/{ex.id}",
                "designerUrl": f"{orch}#/scenes/{ex.scene_id}/designer?env_id={environment.pk}",
            }
        )

    test_run_rows = []
    for tr in test_runs_slice:
        test_run_rows.append(
            {
                "id": tr.pk,
                "name": tr.name,
                "projectName": tr.project.name,
                "status": tr.status,
                "startTime": tr.start_time.strftime("%Y-%m-%d %H:%M") if tr.start_time else "-",
                "endTime": tr.end_time.strftime("%Y-%m-%d %H:%M") if tr.end_time else "-",
                "detailUrl": reverse("test_run_detail", args=[tr.pk]),
            }
        )

    st = getattr(environment, "script_timeout", 1000) or 1000
    return {
        "environment": {
            "id": environment.pk,
            "name": environment.name,
            "baseUrl": environment.base_url,
            "createdAt": environment.created_at.strftime("%Y-%m-%d %H:%M"),
            "updatedAt": environment.updated_at.strftime("%Y-%m-%d %H:%M"),
            "scriptTimeout": st,
            "preRequestScript": environment.pre_request_script or "",
        },
        "project": {
            "id": environment.project_id,
            "name": environment.project.name,
        },
        "variablesRows": variables_rows,
        "hasVariables": bool(env_vars),
        "envVarsForScriptTest": env_vars,
        "recentSceneExecutions": scene_rows,
        "recentTestRuns": test_run_rows,
        "urls": {
            "edit": reverse("environment_edit", args=[environment.pk]),
            "project": reverse("project_detail", args=[environment.project_id]),
            "testRunListFiltered": f"{reverse('test_run_list')}?environment={environment.pk}",
            "sceneExecutionListFiltered": f"{reverse('scene_execution_list')}?environment={environment.pk}",
        },
        "apiBase": "/api/environments",
    }


@login_required
def dashboard(request):
    """仪表盘 — 已迁移至统一 SPA"""
    return redirect('/app/#/dashboard')

def generate_time_series_data(mode, tz, project_id=None):
    now = timezone.now().astimezone(tz)


    if mode == 'daily':
        count = 7
        start_date = now - timedelta(days=count - 1)
        end_date = now
        period = 'day'

    elif mode == 'monthly':
        start_date = now.replace(month=1, day=1)
        end_date = now.replace(month=12, day=31)
        count = 12
        period = 'month'

    elif mode == 'yearly':
        current_year = now.year
        start_date = now.replace(year=current_year - 4, month=1, day=1)
        end_date = now.replace(month=12, day=31)
        count = 5
        period = 'year'

    else:
        raise ValueError("Invalid mode")

    labels = generate_date_labels(start_date, period, count)
    data = {
        'projects': get_model_timeseries(Project, start_date, count, period, tz),
        'test_cases': get_model_timeseries(TestCase, start_date, count, period, tz),
        'test_suites': get_model_timeseries(TestSuite, start_date, count, period, tz),
        'test_runs': get_model_timeseries(TestRun, start_date, count, period, tz),
        'test_reports': get_model_timeseries(TestReport, start_date, count, period, tz),
        # TestScene：按 created_at；仅 is_deleted=False（与总数统计口径一致）
        'test_scenes': get_test_scene_timeseries(start_date, count, period, tz, project_id=project_id),
        # TestSceneExecution：按 created_at 分桶（写死，见模块文档说明）。
        # 选用原因：与 TestRun 等「活动发起时间」口径一致；finished_at 在 running 时为空，无法纳入时间轴。
        'test_scene_executions': get_test_scene_execution_timeseries(
            start_date, count, period, tz, project_id=project_id
        ),
    }
    return {'labels': labels, 'datasets': data}


def generate_date_labels(start_date, period, count):
    labels = []
    current = start_date

    if period == 'day':
        for _ in range(count):
            labels.append(current.strftime('%b %d').lstrip('0').replace(' 0', ' '))
            current += timedelta(days=1)

    elif period == 'month':
        for i in range(count):
            labels.append(f'{i+1}月')

    elif period == 'year':
        for i in range(count):
            labels.append(str(start_date.year + i))

    return labels


def get_queryset_timeseries(queryset, start_date, count, period, tz, date_field="created_at"):
    """对任意 QuerySet 按时间桶聚合；date_field 为模型上的 DateTimeField 名。"""
    now = timezone.now().astimezone(tz)
    end_date = now

    utc_start = start_date.astimezone(pytz.utc)
    utc_end = end_date.astimezone(pytz.utc)

    range_kw = {f"{date_field}__range": (utc_start, utc_end)}
    results = queryset.filter(**range_kw).values_list(date_field, flat=True)

    counts = [0] * count

    for dt in results:
        local_dt = dt.astimezone(tz)

        if period == 'day':
            diff = (local_dt.date() - start_date.date()).days
        elif period == 'month':
            diff = local_dt.month - 1
        elif period == 'year':
            diff = local_dt.year - start_date.year
        else:
            continue

        if 0 <= diff < count:
            counts[diff] += 1

    return counts


def get_model_timeseries(model, start_date, count, period, tz):
    return get_queryset_timeseries(model.objects.all(), start_date, count, period, tz, "created_at")


def get_test_scene_timeseries(start_date, count, period, tz, project_id=None):
    """未删除场景创建趋势；可选按业务 Project 过滤（经 ApiProject.platform_project）。"""
    qs = TestScene.objects.filter(is_deleted=False)
    if project_id is not None:
        qs = qs.filter(project__platform_project_id=project_id)
    return get_queryset_timeseries(qs, start_date, count, period, tz, "created_at")


def get_test_scene_execution_timeseries(start_date, count, period, tz, project_id=None):
    """场景执行记录趋势；时间字段写死为 created_at（见 generate_time_series_data 注释）。"""
    qs = TestSceneExecution.objects.all()
    if project_id is not None:
        qs = qs.filter(scene__project__platform_project_id=project_id)
    return get_queryset_timeseries(qs, start_date, count, period, tz, "created_at")


# Project views
@login_required
def project_list(request):
    """项目列表 — 已迁移至 Vue SPA"""
    return redirect('/app/#/projects')


@login_required
def project_create(request):
    """新建项目 — 已迁移至 Vue SPA"""
    return redirect('/app/#/projects/create')


@login_required
def project_detail(request, pk):
    """项目详情 — 已迁移至 Vue SPA"""
    return redirect(f'/app/#/projects/{pk}')


@login_required
def project_edit(request, pk):
    """编辑项目 — 已迁移至 Vue SPA"""
    return redirect(f'/app/#/projects/{pk}/edit')


@login_required
def project_delete(request, pk):
    """删除项目 — 已迁移至 Vue SPA"""
    return redirect('/app/#/projects')


# Environment views
@login_required
def environment_list(request):
    """环境列表 — 已迁移至 Vue SPA"""
    return redirect('/app/#/environments')


def _environment_form_vue_context(request, form):
    """
    为环境编辑页 Vue 3 + Element Plus（scene-orchestrator 构建产物）提供安全的 JSON 初始状态。
    """
    pv = form["project"].value()
    try:
        project_val = int(pv) if pv is not None and str(pv).strip() != "" else None
    except (TypeError, ValueError):
        project_val = None
    st = form["script_timeout"].value()
    try:
        st_int = int(st) if st is not None and str(st).strip() != "" else 1000
    except (TypeError, ValueError):
        st_int = 1000
    return {
        "env_vue_initial_json": json.dumps(
            {
                "variablesJson": form["variables_json"].value() or "{}",
                "requestHeadersJson": form["request_headers_json"].value() or "[]",
                "name": form["name"].value() or "",
                "project": project_val,
                "baseUrl": form["base_url"].value() or "",
                "category": form["category"].value() or "default",
                "isGlobalVisible": bool(form["is_global_visible"].value()),
                "preRequestScript": form["pre_request_script"].value() or "",
                "scriptTimeout": st_int,
                "projects": list(Project.objects.order_by("name").values("id", "name")),
                "csrfToken": get_token(request),
                "preRequestScriptHelp": str(form["pre_request_script"].field.help_text or ""),
                "scriptTimeoutHelp": str(form["script_timeout"].field.help_text or ""),
            },
            ensure_ascii=False,
        ),
    }


@login_required
def environment_create(request):
    """新建环境 — 已迁移至 Vue SPA"""
    return redirect('/app/#/environments/create')


@login_required
def environment_detail(request, pk):
    """环境详情 — 已迁移至 Vue SPA"""
    return redirect(f'/app/#/environments/{pk}')


@login_required
def environment_edit(request, pk):
    """编辑环境 — 已迁移至 Vue SPA"""
    return redirect(f'/app/#/environments/{pk}/edit')


@login_required
def environment_delete(request, pk):
    """删除环境 — 已迁移至 Vue SPA"""
    return redirect('/app/#/environments')


# Test Case views
@login_required
def test_case_list(request):
    """测试用例列表 — 已迁移至 Vue SPA"""
    return redirect('/app/#/test-cases')


@login_required
def test_case_create(request):
    """新建测试用例 — 已迁移至 Vue SPA"""
    return redirect('/app/#/test-cases/create')


@login_required
def ai_case_draft_box(request):
    """AI草稿箱 — 已迁移至统一 SPA"""
    return redirect('/app/#/ai/draft-box')


@login_required
def ai_rule_management(request):
    """AI规则管理 — 已迁移至统一 SPA"""
    return redirect('/app/#/ai/rules')


@login_required
def ai_prompt_template_management(request):
    """AI提示词模板管理 — 已迁移至统一 SPA"""
    return redirect('/app/#/ai/prompt-templates')


@login_required
def api_asset_manager(request):
    """API资产管理 — 已迁移至统一 SPA"""
    return redirect('/app/#/api-assets')


@login_required
def test_scene_orchestrator(request):
    """测试场景编排 — 已迁移至统一 SPA"""
    return redirect('/app/#/scenes')


@login_required
def performance_test(request):
    """性能测试 — 已迁移至统一 SPA"""
    return redirect('/app/#/performance')


@login_required
@require_POST
def api_asset_upload(request):
    upload_file = request.FILES.get("file")
    if not upload_file:
        return JsonResponse({"success": False, "detail": "未接收到上传文件"}, status=400)

    date_path = timezone.now().strftime("%Y/%m/%d")
    ext = os.path.splitext(upload_file.name or "")[1]
    file_name = f"api_asset_{int(time.time() * 1000)}{ext}"
    storage_path = f"api_asset_files/{date_path}/{file_name}"
    saved_path = default_storage.save(storage_path, upload_file)
    return JsonResponse(
        {
            "success": True,
            "file_name": upload_file.name,
            "file_path": saved_path,
            "file_url": default_storage.url(saved_path),
        }
    )


def _resolve_api_project_for_platform(platform_project_id, user):
    platform_project = get_object_or_404(Project, id=platform_project_id)
    api_project, _ = ApiProject.objects.get_or_create(
        platform_project=platform_project,
        defaults={
            "name": platform_project.name,
            "description": platform_project.description or "",
            "created_by": user,
        },
    )
    return api_project


def _normalize_api_asset_compare_value(value):
    if isinstance(value, dict):
        return {
            str(k): _normalize_api_asset_compare_value(v)
            for k, v in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, list):
        return [_normalize_api_asset_compare_value(item) for item in value]
    if value is None:
        return {}
    return value


def _api_asset_compare_snapshot(asset):
    return {
        "project": asset.project_id,
        "group": asset.group_id,
        "name": asset.name,
        "method": asset.method,
        "url": asset.url,
        "interface_desc": asset.interface_desc or "",
        "request_headers": asset.request_headers or {},
        "request_params": asset.request_params or {},
        "request_body_format": asset.request_body_format,
        "request_body": asset.request_body or {},
        "response_schema": asset.response_schema or {},
        "error_code": asset.error_code or [],
        "auth_config": asset.auth_config or {},
        "status": asset.status,
        "source": asset.source,
        "external_id": asset.external_id,
        "required": asset.required,
        "param_type": asset.param_type,
        "sort": asset.sort,
        "param_status": asset.param_status,
    }


@login_required
def api_asset_create(request):
    """新建 API 资产 — 已迁移至统一 SPA"""
    return redirect('/app/#/api-assets/create')


@login_required
def api_asset_edit(request, pk):
    """编辑 API 资产 — 已迁移至统一 SPA"""
    return redirect(f'/app/#/api-assets/edit/{pk}')


# API 分组管理（与 API 资产管理中的分组数据共用）
def _get_api_group_and_descendant_ids(group):
    """获取分组及其所有子分组的 ID 列表。"""
    ids = [group.id]
    for child in ApiGroup.objects.filter(parent=group):
        ids.extend(_get_api_group_and_descendant_ids(child))
    return ids


@login_required
def api_group_list(request, pk):
    """API 分组列表 — 已迁移至统一 SPA"""
    return redirect('/app/#/api-assets')


@login_required
def api_group_create(request, pk):
    """新建 API 分组 — 已迁移至统一 SPA"""
    return redirect('/app/#/api-assets')


@login_required
def api_group_edit(request, pk):
    """编辑 API 分组 — 已迁移至统一 SPA"""
    return redirect('/app/#/api-assets')


def _api_group_has_assets(group):
    """检查分组及其子分组下是否存在未删除的接口。"""
    group_ids = _get_api_group_and_descendant_ids(group)
    return ApiAsset.objects.filter(group_id__in=group_ids, is_deleted=False).exists()


@login_required
def api_group_delete(request, pk):
    """删除 API 分组 — 已迁移至统一 SPA"""
    return redirect('/app/#/api-assets')


@login_required
def test_case_detail(request, pk):
    """测试用例详情 — 已迁移至 Vue SPA"""
    return redirect(f'/app/#/test-cases/{pk}')

@login_required
def test_case_edit(request, pk):
    """编辑测试用例 — 已迁移至 Vue SPA"""
    return redirect(f'/app/#/test-cases/{pk}/edit')

@login_required
def test_case_run(request, pk):
    """执行测试用例 — 已迁移至 Vue SPA"""
    return redirect(f'/app/#/test-cases/{pk}/run')


# Test Suite views
@login_required
def test_suite_list(request):
    """测试套件列表 — 已迁移至 Vue SPA"""
    return redirect('/app/#/test-suites')


@login_required
def test_suite_create(request):
    """新建测试套件 — 已迁移至 Vue SPA"""
    return redirect('/app/#/test-suites/create')


@login_required
def test_suite_detail(request, pk):
    """测试套件详情 — 已迁移至 Vue SPA"""
    return redirect(f'/app/#/test-suites/{pk}')


@login_required
def test_suite_edit(request, pk):
    """编辑测试套件 — 已迁移至 Vue SPA"""
    return redirect(f'/app/#/test-suites/{pk}/edit')


@login_required
def test_suite_run(request, pk):
    """执行测试套件 — 已迁移至 Vue SPA"""
    return redirect(f'/app/#/test-suites/{pk}/run')


# Test Run views
@login_required
def test_run_list(request):
    """测试运行列表 — 已迁移至 Vue SPA"""
    return redirect('/app/#/test-runs')


@login_required
def test_run_detail(request, pk):
    """测试运行详情 — 已迁移至 Vue SPA"""
    return redirect(f'/app/#/test-runs/{pk}')


@login_required
def test_run_delete(request, pk):
    """删除测试运行 — 已迁移至 Vue SPA"""
    return redirect('/app/#/test-runs')


# ----------------------------------------------------------------------------- 场景执行（列表/详情，对齐「测试运行」交互）
@login_required
def scene_execution_list(request):
    """场景执行列表 — 已迁移至 Vue SPA"""
    return redirect('/app/#/scene-executions')


@login_required
def scene_execution_detail(request, pk):
    """场景执行详情 — 已迁移至 Vue SPA"""
    return redirect(f'/app/#/scene-executions/{pk}')


@login_required
def scene_execution_delete(request, pk):
    """删除场景执行 — 已迁移至 Vue SPA"""
    return redirect('/app/#/scene-executions')


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
def is_admin(request, user):
    """检查用户是否是管理员"""
    if user.is_superuser:
        return user.is_superuser
    else:
        messages.error(request, '您不是管理员，无法访问此页面。')
    # return user.is_superuser


@login_required
# @user_passes_test(is_admin)
def email_config_list(request):
    """邮件配置列表视图"""
    configs = EmailConfig.objects.all().order_by('-is_active', '-updated_at')
    return render(request, 'admin/email_config_list.html', {'configs': configs})


@login_required
# @user_passes_test(is_admin)
def email_config_create(request):
    """创建邮件配置视图"""
    if request.method == 'POST':
        form = EmailConfigForm(request.POST)
        if form.is_valid():
            config = form.save()
            messages.success(request, f"邮件配置 '{config.name}' 创建成功")
            return redirect('email_config_list')
    else:
        form = EmailConfigForm()

    return render(request, 'admin/email_config_form.html', {
        'form': form,
        'title': '创建邮件配置',
        'submit_text': '创建',
    })


@login_required
# @user_passes_test(is_admin)
def email_config_edit(request, pk):
    """编辑邮件配置视图"""
    config = get_object_or_404(EmailConfig, pk=pk)

    if request.method == 'POST':
        form = EmailConfigForm(request.POST, instance=config)
        if form.is_valid():
            config = form.save()
            messages.success(request, f"邮件配置 '{config.name}' 更新成功")
            return redirect('email_config_list')
    else:
        form = EmailConfigForm(instance=config)

    return render(request, 'admin/email_config_form.html', {
        'form': form,
        'config': config,
        'title': f"编辑邮件配置: {config.name}",
        'submit_text': '保存',
    })


@login_required
# @user_passes_test(is_admin)
def email_config_delete(request, pk):
    """删除邮件配置视图"""
    config = get_object_or_404(EmailConfig, pk=pk)

    if request.method == 'POST':
        name = config.name
        config.delete()
        messages.success(request, f"邮件配置 '{name}' 已删除")
        return redirect('email_config_list')

    return render(request, 'admin/email_config_delete.html', {'config': config})


@login_required
# @user_passes_test(is_admin)
def email_config_test(request, pk):
    """测试邮件配置视图"""
    config = get_object_or_404(EmailConfig, pk=pk)

    if request.method == 'POST':
        form = TestEmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            success, message = config.send_test_email(email)

            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)

            return redirect('email_config_list')
    else:
        form = TestEmailForm()

    return render(request, 'admin/email_config_test.html', {
        'form': form,
        'config': config,
    })


@login_required
# @user_passes_test(is_admin)
def email_config_activate(request, pk):
    """激活邮件配置视图"""
    config = get_object_or_404(EmailConfig, pk=pk)

    # 测试连接
    success, message = config.test_connection()

    if success:
        config.is_active = True
        config.save()  # save 方法会自动将其他配置设置为非激活
        EmailConfig.apply_active_config()  # 应用配置到 Django 设置
        messages.success(request, f"邮件配置 '{config.name}' 已激活: {message}")
    else:
        messages.error(request, f"无法激活邮件配置: {message}")

    return redirect('email_config_list')


def ensure_ai_parameter_configs():
    ai_defaults = [
        {
            "key": "AI_API_BASE_URL",
            "value": "http://127.0.0.1:8001",
            "description": "AI服务基础地址(含IP和端口)",
            "category": "ai",
        },
        {
            "key": "AI_API_GENERATE_MULTI_CASES_PATH",
            "value": "/v1/ai/generate-multi-test-cases",
            "description": "AI生成多用例接口路径",
            "category": "ai",
        },
        {
            "key": "AI_API_METHOD",
            "value": "POST",
            "description": "AI生成接口请求方法",
            "category": "ai",
        },
        {
            "key": "AI_API_TIMEOUT_SECONDS",
            "value": "30",
            "description": "AI接口超时时间(秒)",
            "category": "ai",
        },
        {
            "key": "AI_API_AUTH_TOKEN",
            "value": "",
            "description": "AI接口Bearer Token(可空)",
            "category": "ai",
        },
        {
            "key": "AI_API_EXTRA_HEADERS_JSON",
            "value": "{}",
            "description": "AI接口额外请求头(JSON对象)",
            "category": "ai",
        },
        {
            "key": "AI_API_RESPONSE_CASES_PATH",
            "value": "data.cases",
            "description": "AI响应中用例列表路径(如 data.cases / cases)",
            "category": "ai",
        },
    ]

    for item in ai_defaults:
        ParameterConfig.objects.get_or_create(
            key=item["key"],
            defaults={
                "value": item["value"],
                "description": item["description"],
                "category": item["category"],
            },
        )


@login_required
def parameter_config_list(request):
    ensure_ai_parameter_configs()
    configs = ParameterConfig.objects.all().order_by("category", "key")
    return render(request, "admin/parameter_config_list.html", {"configs": configs})


@login_required
def parameter_config_edit(request, pk):
    config = get_object_or_404(ParameterConfig, pk=pk)

    if request.method == "POST":
        form = ParameterConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, f"参数配置 '{config.key}' 更新成功")
            return redirect("parameter_config_list")
    else:
        form = ParameterConfigForm(instance=config)

    return render(
        request,
        "admin/parameter_config_form.html",
        {
            "form": form,
            "config": config,
            "title": "编辑参数配置",
            "submit_text": "保存",
        },
    )


def _extract_json_by_path(data, path):
    if not path:
        return data
    current = data
    for segment in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(segment)
    return current


@login_required
@require_POST
def parameter_config_test_ai(request):
    ensure_ai_parameter_configs()

    base_url = (ParameterConfig.get_value("AI_API_BASE_URL", "") or "").strip()
    api_path = (ParameterConfig.get_value("AI_API_GENERATE_MULTI_CASES_PATH", "") or "").strip()
    api_method = (ParameterConfig.get_value("AI_API_METHOD", "POST") or "POST").upper().strip()
    auth_token = (ParameterConfig.get_value("AI_API_AUTH_TOKEN", "") or "").strip()
    timeout_text = (ParameterConfig.get_value("AI_API_TIMEOUT_SECONDS", "30") or "30").strip()
    extra_headers_text = (ParameterConfig.get_value("AI_API_EXTRA_HEADERS_JSON", "{}") or "{}").strip()
    response_cases_path = (
        ParameterConfig.get_value("AI_API_RESPONSE_CASES_PATH", "data.cases") or "data.cases"
    ).strip()

    if not base_url or not api_path:
        return JsonResponse(
            {"success": False, "message": "配置缺失：请先设置AI_API_BASE_URL和AI_API_GENERATE_MULTI_CASES_PATH"},
            status=400,
        )

    try:
        timeout_seconds = float(timeout_text)
    except (TypeError, ValueError):
        timeout_seconds = 30.0

    try:
        extra_headers = json.loads(extra_headers_text or "{}")
        if not isinstance(extra_headers, dict):
            return JsonResponse(
                {"success": False, "message": "AI_API_EXTRA_HEADERS_JSON 必须是JSON对象"},
                status=400,
            )
    except (TypeError, ValueError):
        return JsonResponse(
            {"success": False, "message": "AI_API_EXTRA_HEADERS_JSON 不是合法JSON"},
            status=400,
        )

    headers = {"Content-Type": "application/json"}
    headers.update(extra_headers)
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    payload = {
        "base_info": {
            "project_id": 1,
            "group_id": None,
            "interface_id": 1,
            "request_method": "GET",
            "request_url": "/health-check",
        },
        "case_type": "connectivity_check",
        "creator_id": request.user.id,
    }
    endpoint = urljoin(f"{base_url.rstrip('/')}/", api_path.lstrip("/"))

    started = time.perf_counter()
    try:
        resp = requests.request(
            method=api_method,
            url=endpoint,
            headers=headers,
            json=payload,
            timeout=timeout_seconds,
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        status_code = resp.status_code

        try:
            response_data = resp.json()
        except ValueError:
            response_data = {"raw_text": resp.text[:500]}

        cases = _extract_json_by_path(response_data, response_cases_path)
        if cases is None and isinstance(response_data, dict):
            cases = response_data.get("cases")
        case_count = len(cases) if isinstance(cases, list) else 0

        return JsonResponse(
            {
                "success": resp.ok,
                "message": "AI接口连通成功" if resp.ok else "AI接口返回非2xx状态",
                "summary": {
                    "endpoint": endpoint,
                    "method": api_method,
                    "status_code": status_code,
                    "elapsed_ms": elapsed_ms,
                    "case_count": case_count,
                    "response_preview": response_data,
                },
            },
            status=200 if resp.ok else 400,
        )
    except requests.RequestException as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return JsonResponse(
            {
                "success": False,
                "message": f"AI接口请求失败: {str(exc)}",
                "summary": {
                    "endpoint": endpoint,
                    "method": api_method,
                    "elapsed_ms": elapsed_ms,
                },
            },
            status=400,
        )


# 测试用例分组视图 — 已迁移至 Vue SPA
@login_required
def test_case_group_list(request):
    return redirect('/app/#/test-case-groups')


@login_required
def test_case_group_create(request):
    return redirect('/app/#/test-case-groups')


@login_required
def test_case_group_edit(request, pk):
    return redirect('/app/#/test-case-groups')


@login_required
def test_case_group_delete(request, pk):
    return redirect('/app/#/test-case-groups')


# 测试套件分组视图 — 已迁移至 Vue SPA
@login_required
def test_suite_group_list(request):
    return redirect('/app/#/test-suite-groups')


@login_required
def test_suite_group_create(request):
    return redirect('/app/#/test-suite-groups')


@login_required
def test_suite_group_edit(request, pk):
    return redirect('/app/#/test-suite-groups')


@login_required
def test_suite_group_delete(request, pk):
    return redirect('/app/#/test-suite-groups')


# 获取测试用例分组数据的API
@login_required
def get_test_case_groups_data(request, project_id):
    """获取项目的测试用例分组数据，用于前端展示"""
    project = get_object_or_404(Project, pk=project_id)

    # 获取所有分组
    groups = TestCaseGroup.objects.filter(project=project)

    # 构建分组树
    group_tree = []
    group_dict = {}

    # 先创建所有分组的字典
    for group in groups:
        group_data = {
            'id': group.id,
            'name': group.name,
            'parent_id': group.parent_id,
            'children': [],
            'test_cases': []
        }
        group_dict[group.id] = group_data

    # 构建分组树
    for group_id, group_data in group_dict.items():
        if group_data['parent_id'] is None:
            # 顶级分组
            group_tree.append(group_data)
        else:
            # 子分组
            parent_data = group_dict.get(group_data['parent_id'])
            if parent_data:
                parent_data['children'].append(group_data)

    # 获取每个分组下的测试用例
    for group in groups:
        test_cases = TestCase.objects.filter(project=project, group=group)
        group_data = group_dict.get(group.id)
        if group_data:
            for test_case in test_cases:
                group_data['test_cases'].append({
                    'id': test_case.id,
                    'name': test_case.name,
                    'method': test_case.request_method,
                    'url': test_case.request_url
                })

    # 获取未分组的测试用例
    ungrouped_test_cases = TestCase.objects.filter(project=project, group__isnull=True)
    ungrouped_data = {
        'id': 0,
        'name': 'Ungrouped',
        'parent_id': None,
        'children': [],
        'test_cases': []
    }

    for test_case in ungrouped_test_cases:
        ungrouped_data['test_cases'].append({
            'id': test_case.id,
            'name': test_case.name,
            'method': test_case.request_method,
            'url': test_case.request_url
        })

    # 如果有未分组的测试用例，添加到结果中
    if ungrouped_data['test_cases']:
        group_tree.append(ungrouped_data)

    return JsonResponse({
        'groups': group_tree
    })


@login_required
def test_report_list(request):
    """测试报告列表页面 — 已迁移至 Vue SPA"""
    return redirect('/app/#/reports')


@login_required
def test_report_detail(request, pk):
    """测试报告详情页面 — 已迁移至 Vue SPA"""
    return redirect(f'/app/#/reports/{pk}')


@login_required
def test_report_delete(request, pk):
    """删除测试报告 — 已迁移至 Vue SPA"""
    report = get_object_or_404(TestReport, pk=pk)

    if request.method == 'POST':
        report.delete()
        messages.success(request, f'测试报告已成功删除')
        return redirect('/app/#/reports')

    return redirect('/app/#/reports')


@login_required
def generate_test_run_report(request, pk):
    """从测试运行生成测试报告 — 已迁移至 Vue SPA"""
    if request.method == 'GET':
        return redirect(f'/app/#/test-runs/{pk}/generate-report')

    test_run = get_object_or_404(TestRun, pk=pk)

    if request.method == 'POST':
        form = GenerateReportForm(request.POST)
        if form.is_valid():
            # 创建测试报告
            report = TestReport(
                name=form.cleaned_data['name'],
                description=form.cleaned_data['description'],
                project=test_run.project,  # 直接使用test_run.project
                report_type='test_run',
                report_format=form.cleaned_data['report_format'],
                test_run=test_run,
                is_public=form.cleaned_data['is_public'],
                created_by=request.user
            )

            # 生成报告内容
            if form.cleaned_data['report_format'] == 'json':
                # 生成JSON格式的报告
                content = {
                    'id': str(test_run.id),
                    'name': test_run.name,
                    'project': {
                        'id': str(test_run.project.id),
                        'name': test_run.project.name,
                    },
                    'environment': {
                        'id': str(test_run.environment.id),
                        'name': test_run.environment.name,
                        'base_url': test_run.environment.base_url,
                    },
                    'status': test_run.status,
                    'start_time': test_run.start_time.isoformat() if test_run.start_time else None,
                    'end_time': test_run.end_time.isoformat() if test_run.end_time else None,
                    'duration': test_run.duration,
                    'results': []
                }

                # 添加测试套件信息（如果有）
                if test_run.test_suite:
                    content['test_suite'] = {
                        'id': str(test_run.test_suite.id),
                        'name': test_run.test_suite.name,
                    }

                # 添加测试结果
                for result in test_run.test_results.all():
                    result_data = {
                        'id': str(result.id),
                        'status': result.status,
                        'response_status_code': result.response_status_code,
                        'response_time': result.response_time,
                        'test_case': {
                            'id': str(result.test_case.id),
                            'name': result.test_case.name,
                            'request_method': result.test_case.request_method,
                            'request_url': result.test_case.request_url,
                        }
                    }

                    # 添加可选字段
                    if hasattr(result, 'response_headers') and result.response_headers:
                        result_data['response_headers'] = result.response_headers

                    if hasattr(result, 'response_body') and result.response_body:
                        result_data['response_body'] = result.response_body

                    if hasattr(result, 'request_headers') and result.request_headers:
                        result_data['request_headers'] = result.request_headers

                    if hasattr(result, 'request_body') and result.request_body:
                        result_data['request_body'] = result.request_body

                    if hasattr(result, 'error_message') and result.error_message:
                        result_data['error_message'] = result.error_message

                    content['results'].append(result_data)

                report.content = json.dumps(content, indent=2)
            else:
                # 生成HTML格式的报告
                html_content = f"""
                <div class="test-report">
                    <h1>{test_run.name} - 测试运行报告</h1>
                    <div class="report-meta">
                        <p><strong>项目:</strong> {test_run.project.name}</p>
                        <p><strong>环境:</strong> {test_run.environment.name}</p>
                        <p><strong>状态:</strong> <span class="status-{test_run.status.lower()}">{test_run.status}</span></p>
                        <p><strong>开始时间:</strong> {test_run.start_time}</p>
                        <p><strong>结束时间:</strong> {test_run.end_time}</p>
                        <p><strong>持续时间:</strong> {test_run.duration} 秒</p>
                """

                # 添加测试套件信息（如果有）
                if test_run.test_suite:
                    html_content += f"""
                        <p><strong>测试套件:</strong> {test_run.test_suite.name}</p>
                    """

                html_content += """
                    </div>

                    <h2>测试结果</h2>
                """

                # 添加测试结果
                for result in test_run.test_results.all():
                    html_content += f"""
                    <div class="test-result">
                        <h3>{result.test_case.name}</h3>
                        <p><strong>状态:</strong> <span class="status-{result.status.lower()}">{result.status}</span></p>
                        <p><strong>请求方法:</strong> {result.test_case.request_method}</p>
                        <p><strong>请求URL:</strong> {result.test_case.request_url}</p>
                        <p><strong>响应状态码:</strong> {result.response_status_code}</p>
                        <p><strong>响应时间:</strong> {result.response_time} 毫秒</p>

                        <div class="collapsible">
                            <h4>请求头</h4>
                            <pre>{json.dumps(result.request_headers, indent=2) if hasattr(result, 'request_headers') and result.request_headers else '无数据'}</pre>
                        </div>

                        <div class="collapsible">
                            <h4>请求体</h4>
                            <pre>{result.request_body if hasattr(result, 'request_body') and result.request_body else '无数据'}</pre>
                        </div>

                        <div class="collapsible">
                            <h4>响应头</h4>
                            <pre>{json.dumps(result.response_headers, indent=2) if hasattr(result, 'response_headers') and result.response_headers else '无数据'}</pre>
                        </div>

                        <div class="collapsible">
                            <h4>响应体</h4>
                            <pre>{result.response_body if hasattr(result, 'response_body') and result.response_body else '无数据'}</pre>
                        </div>

                        {f'<div class="error-message"><h4>错误信息</h4><pre>{result.error_message}</pre></div>' if hasattr(result, 'error_message') and result.error_message else ''}
                    </div>
                    """

                html_content += """
                </div>
                <style>
                    .test-report {
                        font-family: Arial, sans-serif;
                        max-width: 1200px;
                        margin: 0 auto;
                        padding: 20px;
                    }
                    .report-meta {
                        background-color: #f5f5f5;
                        padding: 15px;
                        border-radius: 5px;
                        margin-bottom: 20px;
                    }
                    .test-result {
                        background-color: #f9f9f9;
                        padding: 15px;
                        border-radius: 5px;
                        margin-bottom: 15px;
                        border-left: 5px solid #ddd;
                    }
                    .collapsible {
                        margin-top: 10px;
                    }
                    .collapsible h4 {
                        cursor: pointer;
                        background-color: #eee;
                        padding: 8px;
                        border-radius: 3px;
                    }
                    .collapsible pre {
                        background-color: #f5f5f5;
                        padding: 10px;
                        border-radius: 3px;
                        overflow-x: auto;
                        white-space: pre-wrap;
                    }
                    .status-pass, .status-success, .status-completed {
                        color: green;
                        font-weight: bold;
                    }
                    .status-fail, .status-failure, .status-error, .status-failed {
                        color: red;
                        font-weight: bold;
                    }
                    .error-message {
                        background-color: #ffeeee;
                        padding: 10px;
                        border-radius: 3px;
                        margin-top: 10px;
                    }
                    .error-message h4 {
                        color: red;
                    }
                </style>
                <script>
                    document.addEventListener('DOMContentLoaded', function() {
                        const collapsibles = document.querySelectorAll('.collapsible h4');
                        collapsibles.forEach(function(collapsible) {
                            collapsible.addEventListener('click', function() {
                                this.nextElementSibling.style.display = 
                                    this.nextElementSibling.style.display === 'none' ? 'block' : 'none';
                            });
                            // 初始隐藏
                            collapsible.nextElementSibling.style.display = 'none';
                        });
                    });
                </script>
                """

                report.content = html_content

            report.save()
            messages.success(request, f'测试报告 "{report.name}" 已成功生成')
            return redirect('test_report_detail', pk=report.pk)
    else:
        # 默认报告名称
        default_name = f"{test_run.name} - 测试报告 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        form = GenerateReportForm(initial={'name': default_name, 'report_format': 'html'})

    return render(request, 'test_manager/generate_test_report.html', {
        'form': form,
        'test_run': test_run,
    })


@login_required
def generate_test_suite_run_report(request, pk):
    """从测试套件运行生成测试报告"""
    test_suite_run = get_object_or_404(TestSuiteRun, pk=pk)

    if request.method == 'POST':
        form = GenerateReportForm(request.POST)
        if form.is_valid():
            # 创建测试报告
            report = TestReport(
                name=form.cleaned_data['name'],
                description=form.cleaned_data['description'],
                project=test_suite_run.project,
                report_type='test_suite_run',
                report_format=form.cleaned_data['report_format'],
                test_suite_run=test_suite_run,
                is_public=form.cleaned_data['is_public']
            )

            # 计算持续时间（如果可能）
            duration = None
            if test_suite_run.start_time and test_suite_run.end_time:
                duration = (test_suite_run.end_time - test_suite_run.start_time).total_seconds()

            # 生成报告内容
            if form.cleaned_data['report_format'] == 'json':
                # 生成JSON格式的报告
                content = {
                    'id': str(test_suite_run.id),
                    'test_suite': {
                        'id': str(test_suite_run.test_suite.id),
                        'name': test_suite_run.test_suite.name,
                    },
                    'environment': {
                        'id': str(test_suite_run.environment.id),
                        'name': test_suite_run.environment.name,
                        'base_url': test_suite_run.environment.base_url,
                    },
                    'status': test_suite_run.status,
                    'start_time': test_suite_run.start_time.isoformat() if test_suite_run.start_time else None,
                    'end_time': test_suite_run.end_time.isoformat() if test_suite_run.end_time else None,
                    'duration': duration,
                    'test_runs': []
                }

                # 添加测试运行
                for test_run in test_suite_run.test_runs.all():
                    # 计算测试运行的持续时间（如果可能）
                    run_duration = None
                    if test_run.start_time and test_run.end_time:
                        run_duration = (test_run.end_time - test_run.start_time).total_seconds()

                    run_data = {
                        'id': str(test_run.id),
                        'name': test_run.name,
                        'status': test_run.status,
                        'start_time': test_run.start_time.isoformat() if test_run.start_time else None,
                        'end_time': test_run.end_time.isoformat() if test_run.end_time else None,
                        'duration': run_duration,
                        'results': []
                    }

                    # 添加测试结果
                    for result in test_run.test_results.all():
                        result_data = {
                            'id': str(result.id),
                            'status': result.status,
                            'response_status_code': result.response_status_code,
                            'response_time': result.response_time,
                            'test_case': {
                                'id': str(result.test_case.id),
                                'name': result.test_case.name,
                                'request_method': result.test_case.request_method,
                                'request_url': result.test_case.request_url,
                            }
                        }

                        if hasattr(result, 'error_message') and result.error_message:
                            result_data['error_message'] = result.error_message

                        run_data['results'].append(result_data)

                    content['test_runs'].append(run_data)

                # 计算统计信息
                total_runs = len(content['test_runs'])
                passed_runs = sum(1 for run in content['test_runs'] if run['status'] == 'completed')
                failed_runs = sum(1 for run in content['test_runs'] if run['status'] == 'failed')
                error_runs = sum(1 for run in content['test_runs'] if
                                 run['status'] not in ['completed', 'failed', 'pending', 'running'])

                content['summary'] = {
                    'total': total_runs,
                    'passed': passed_runs,
                    'failed': failed_runs,
                    'error': error_runs,
                    'success_rate': f"{(passed_runs / total_runs * 100) if total_runs > 0 else 0:.2f}%"
                }

                report.content = json.dumps(content, indent=2)
            else:
                # 生成HTML格式的报告
                # 计算统计信息
                total_runs = test_suite_run.test_runs.count()
                passed_runs = test_suite_run.test_runs.filter(status='completed').count()
                failed_runs = test_suite_run.test_runs.filter(status='failed').count()
                error_runs = test_suite_run.test_runs.exclude(
                    status__in=['completed', 'failed', 'pending', 'running']).count()
                success_rate = (passed_runs / total_runs * 100) if total_runs > 0 else 0

                html_content = f"""
                <div class="test-report">
                    <h1>{test_suite_run.test_suite.name} - 测试套件运行报告</h1>
                    <div class="report-meta">
                        <p><strong>测试套件:</strong> {test_suite_run.test_suite.name}</p>
                        <p><strong>环境:</strong> {test_suite_run.environment.name}</p>
                        <p><strong>状态:</strong> <span class="status-{test_suite_run.status.lower()}">{test_suite_run.status}</span></p>
                        <p><strong>开始时间:</strong> {test_suite_run.start_time}</p>
                        <p><strong>结束时间:</strong> {test_suite_run.end_time}</p>
                """

                # 只有在有开始和结束时间时才显示持续时间
                if duration is not None:
                    html_content += f"""
                        <p><strong>持续时间:</strong> {duration} 秒</p>
                    """

                html_content += """
                    </div>

                    <div class="summary">
                        <h2>测试摘要</h2>
                        <div class="summary-stats">
                            <div class="stat">
                                <div class="stat-value">{total_runs}</div>
                                <div class="stat-label">总计</div>
                            </div>
                            <div class="stat stat-success">
                                <div class="stat-value">{passed_runs}</div>
                                <div class="stat-label">通过</div>
                            </div>
                            <div class="stat stat-failure">
                                <div class="stat-value">{failed_runs}</div>
                                <div class="stat-label">失败</div>
                            </div>
                            <div class="stat stat-error">
                                <div class="stat-value">{error_runs}</div>
                                <div class="stat-label">错误</div>
                            </div>
                            <div class="stat">
                                <div class="stat-value">{success_rate:.2f}%</div>
                                <div class="stat-label">成功率</div>
                            </div>
                        </div>
                    </div>

                    <h2>测试用例结果</h2>
                    <table class="test-cases-table">
                        <thead>
                            <tr>
                                <th>测试用例</th>
                                <th>方法</th>
                                <th>URL</th>
                                <th>状态</th>
                                <th>持续时间</th>
                            </tr>
                        </thead>
                        <tbody>
                """

                for test_run in test_suite_run.test_runs.all():
                    # 计算测试运行的持续时间（如果可能）
                    run_duration = None
                    if test_run.start_time and test_run.end_time:
                        run_duration = (test_run.end_time - test_run.start_time).total_seconds()

                    # 获取第一个测试结果（如果有）
                    first_result = test_run.test_results.first()

                    if first_result:
                        html_content += f"""
                        <tr class="test-case-row status-{test_run.status.lower()}">
                            <td>{first_result.test_case.name}</td>
                            <td>{first_result.test_case.request_method}</td>
                            <td>{first_result.test_case.request_url}</td>
                            <td><span class="status-badge status-{test_run.status.lower()}">{test_run.status}</span></td>
                            <td>{run_duration} 秒</td>
                        </tr>
                        <tr class="test-case-details">
                            <td colspan="5">
                                <div class="details-content">
                        """

                        for result in test_run.test_results.all():
                            html_content += f"""
                                    <div class="result-item">
                                        <h4>响应详情</h4>
                                        <p><strong>状态码:</strong> {result.response_status_code}</p>
                            """

                            # 只有在有响应时间时才显示
                            if result.response_time is not None:
                                html_content += f"""
                                        <p><strong>响应时间:</strong> {result.response_time} 毫秒</p>
                                """

                            html_content += f"""
                                        <div class="collapsible">
                                            <h5>请求头</h5>
                                            <pre>{json.dumps(result.request_headers, indent=2) if hasattr(result, 'request_headers') and result.request_headers else '无数据'}</pre>
                                        </div>

                                        <div class="collapsible">
                                            <h5>请求体</h5>
                                            <pre>{result.request_body if hasattr(result, 'request_body') and result.request_body else '无数据'}</pre>
                                        </div>

                                        <div class="collapsible">
                                            <h5>响应头</h5>
                                            <pre>{json.dumps(result.response_headers, indent=2) if hasattr(result, 'response_headers') and result.response_headers else '无数据'}</pre>
                                        </div>

                                        <div class="collapsible">
                                            <h5>响应体</h5>
                                            <pre>{result.response_body if hasattr(result, 'response_body') and result.response_body else '无数据'}</pre>
                                        </div>

                                        {f'<div class="error-message"><h5>错误信息</h5><pre>{result.error_message}</pre></div>' if hasattr(result, 'error_message') and result.error_message else ''}
                                    </div>
                            """

                        html_content += """
                                </div>
                            </td>
                        </tr>
                        """

                html_content += """
                        </tbody>
                    </table>
                </div>
                <style>
                    .test-report {
                        font-family: Arial, sans-serif;
                        max-width: 1200px;
                        margin: 0 auto;
                        padding: 20px;
                    }
                    .report-meta {
                        background-color: #f5f5f5;
                        padding: 15px;
                        border-radius: 5px;
                        margin-bottom: 20px;
                    }
                    .summary {
                        margin-bottom: 30px;
                    }
                    .summary-stats {
                        display: flex;
                        justify-content: space-between;
                        flex-wrap: wrap;
                        gap: 15px;
                        margin-top: 15px;
                    }
                    .stat {
                        background-color: #f5f5f5;
                        border-radius: 5px;
                        padding: 15px;
                        text-align: center;
                        flex: 1;
                        min-width: 100px;
                    }
                    .stat-value {
                        font-size: 24px;
                        font-weight: bold;
                        margin-bottom: 5px;
                    }
                    .stat-label {
                        font-size: 14px;
                        color: #666;
                    }
                    .stat-success {
                        background-color: #e6f7e6;
                    }
                    .stat-success .stat-value {
                        color: #2e7d32;
                    }
                    .stat-failure {
                        background-color: #fde9e8;
                    }
                    .stat-failure .stat-value {
                        color: #c62828;
                    }
                    .stat-error {
                        background-color: #fff3e0;
                    }
                    .stat-error .stat-value {
                        color: #e65100;
                    }
                    .test-cases-table {
                        width: 100%;
                        border-collapse: collapse;
                        margin-top: 20px;
                    }
                    .test-cases-table th, .test-cases-table td {
                        padding: 10px;
                        text-align: left;
                        border-bottom: 1px solid #ddd;
                    }
                    .test-cases-table th {
                        background-color: #f5f5f5;
                        font-weight: bold;
                    }
                    .test-case-row {
                        cursor: pointer;
                    }
                    .test-case-row:hover {
                        background-color: #f9f9f9;
                    }
                    .test-case-row.status-completed {
                        background-color: #f0fff0;
                    }
                    .test-case-row.status-failed {
                        background-color: #fff0f0;
                    }
                    .test-case-row.status-error {
                        background-color: #fffaf0;
                    }
                    .status-badge {
                        display: inline-block;
                        padding: 3px 8px;
                        border-radius: 3px;
                        font-size: 12px;
                        font-weight: bold;
                    }
                    .status-badge.status-completed {
                        background-color: #e6f7e6;
                        color: #2e7d32;
                    }
                    .status-badge.status-failed {
                        background-color: #fde9e8;
                        color: #c62828;
                    }
                    .status-badge.status-error {
                        background-color: #fff3e0;
                        color: #e65100;
                    }
                    .test-case-details {
                        display: none;
                    }
                    .details-content {
                        padding: 15px;
                        background-color: #f9f9f9;
                    }
                    .result-item {
                        margin-bottom: 15px;
                        padding-bottom: 15px;
                        border-bottom: 1px solid #eee;
                    }
                    .result-item:last-child {
                        margin-bottom: 0;
                        padding-bottom: 0;
                        border-bottom: none;
                    }
                    .collapsible {
                        margin-top: 10px;
                    }
                    .collapsible h5 {
                        cursor: pointer;
                        background-color: #eee;
                        padding: 8px;
                        border-radius: 3px;
                        margin: 0;
                    }
                    .collapsible pre {
                        background-color: #f5f5f5;
                        padding: 10px;
                        border-radius: 3px;
                        overflow-x: auto;
                        white-space: pre-wrap;
                        margin-top: 5px;
                    }
                    .status-pass, .status-success, .status-completed, .status-passed {
                        color: green;
                        font-weight: bold;
                    }
                    .status-fail, .status-failure, .status-error, .status-failed {
                        color: red;
                        font-weight: bold;
                    }
                    .error-message {
                        background-color: #ffeeee;
                        padding: 10px;
                        border-radius: 3px;
                        margin-top: 10px;
                    }
                    .error-message h5 {
                        color: red;
                        margin-top: 0;
                    }
                </style>
                <script>
                    document.addEventListener('DOMContentLoaded', function() {
                        // 折叠/展开详情
                        const testCaseRows = document.querySelectorAll('.test-case-row');
                        testCaseRows.forEach(function(row) {
                            row.addEventListener('click', function() {
                                const detailsRow = this.nextElementSibling;
                                detailsRow.style.display = 
                                    detailsRow.style.display === 'table-row' ? 'none' : 'table-row';
                            });
                        });

                        // 折叠/展开可折叠内容
                        const collapsibles = document.querySelectorAll('.collapsible h5');
                        collapsibles.forEach(function(collapsible) {
                            collapsible.addEventListener('click', function(e) {
                                e.stopPropagation();
                                this.nextElementSibling.style.display = 
                                    this.nextElementSibling.style.display === 'none' ? 'block' : 'none';
                            });
                            // 初始隐藏
                            collapsible.nextElementSibling.style.display = 'none';
                        });
                    });
                </script>
                """

                report.content = html_content

            report.save()
            messages.success(request, f'测试报告 "{report.name}" 已成功生成')
            return redirect('test_report_detail', pk=report.pk)
    else:
        # 默认报告名称
        default_name = f"{test_suite_run.test_suite.name} - 测试报告 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        form = GenerateReportForm(initial={'name': default_name, 'report_format': 'html'})

    return render(request, 'test_manager/generate_test_report.html', {
        'form': form,
        'test_suite_run': test_suite_run,
    })


@login_required
def mock_data_generator(request):
    """Mock 数据生成页面 — 重定向到 Vue 版的创建页面"""
    return redirect('mock-data-list')


@login_required
def mock_data_list(request):
    """Mock 数据管理 — 已迁移至统一 SPA"""
    return redirect('/app/#/mock-data')


def mock_data_delete(request, pk):
    """Mock 数据删除 — 已迁移至 Vue，仅保留 API 后端"""
    return redirect('mock-data-list')


def mock_data_export(request, pk):
    data = MockData.objects.get(pk=pk)
    data = json.loads(data.data)
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    # 创建响应对象
    response = HttpResponse(json_str, content_type='application/json')
    # 设置Content-Disposition为附件下载，并指定文件名
    response['Content-Disposition'] = 'attachment; filename="mock_data.json"'
    return response


@login_required
def scheduled_task_list(request):
    """定时任务列表"""
    test_suite_id = request.GET.get('test_suite')
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')

    tasks = ScheduledTask.objects.filter(created_by=request.user)

    if test_suite_id:
        tasks = tasks.filter(test_suite_id=test_suite_id)
        test_suite = get_object_or_404(TestSuite, pk=test_suite_id)
    else:
        test_suite = None

    if search_query:
        tasks = tasks.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(test_suite__name__icontains=search_query)
        )

    if status_filter:
        tasks = tasks.filter(status=status_filter)

    # 分页
    paginator = Paginator(tasks, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'test_suite': test_suite,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': ScheduledTask.STATUS_CHOICES,
    }

    return render(request, 'test_manager/scheduled_task_list.html', context)


@login_required
def scheduled_task_create(request):
    """创建定时任务 - 优化版本，确保立即同步到Celery Beat"""
    import logging
    logger = logging.getLogger(__name__)

    test_suite_id = request.GET.get('test_suite')

    if request.method == 'POST':
        form = ScheduledTaskForm(request.POST, test_suite_id=test_suite_id)
        if form.is_valid():
            try:
                # 保存定时任务
                task = form.save(commit=False)
                task.created_by = request.user
                task.save()

                logger.info(f"定时任务已保存到数据库: {task.name} (ID: {task.id})")

                # 立即同步到Celery Beat
                try:
                    # 计算下次执行时间
                    task.update_next_run_time()
                    logger.info(f"下次执行时间已计算: {task.next_run_time}")

                    # 创建Celery Beat任务
                    celery_task = TaskScheduler.create_or_update_celery_task(task)

                    if celery_task:
                        logger.info(f"Celery Beat任务创建成功: {task.celery_task_id}")
                        messages.success(
                            request,
                            f'定时任务 "{task.name}" 创建成功，已同步到调度器。下次执行时间: {task.next_run_time}'
                        )
                    else:
                        logger.warning(f"Celery Beat任务创建失败: {task.name}")
                        messages.warning(
                            request,
                            f'定时任务 "{task.name}" 创建成功，但同步到调度器失败。请检查Celery Beat服务状态。'
                        )

                    # 验证同步结果
                    from django_celery_beat.models import PeriodicTask
                    if task.celery_task_id and PeriodicTask.objects.filter(name=task.celery_task_id).exists():
                        logger.info(f"验证成功: Celery Beat任务已存在于数据库")
                        messages.info(request, f'调度器同步验证成功')
                    else:
                        logger.error(f"验证失败: Celery Beat任务不存在于数据库")
                        messages.error(request, f'调度器同步验证失败，任务可能无法按时执行')

                except Exception as sync_error:
                    logger.error(f"同步到Celery Beat失败: {str(sync_error)}")
                    logger.error(f"同步错误详情: {traceback.format_exc()}")
                    messages.error(
                        request,
                        f'定时任务创建成功，但同步到调度器失败: {str(sync_error)}'
                    )

                return redirect('scheduled_task_detail', pk=task.pk)

            except Exception as e:
                logger.error(f"创建定时任务失败: {str(e)}")
                logger.error(f"创建错误详情: {traceback.format_exc()}")
                messages.error(request, f'创建定时任务失败: {str(e)}')

    else:
        initial = {}
        if test_suite_id:
            initial['test_suite'] = test_suite_id
        form = ScheduledTaskForm(initial=initial, test_suite_id=test_suite_id)

    return render(request, 'test_manager/scheduled_task_form.html', {
        'form': form,
        'title': '创建定时任务'
    })


@login_required
def scheduled_task_detail(request, pk):
    """定时任务详情"""
    task = get_object_or_404(ScheduledTask, pk=pk, created_by=request.user)

    # 获取执行日志
    logs = TaskExecutionLog.objects.filter(scheduled_task=task).order_by('-start_time')

    # 分页
    paginator = Paginator(logs, 10)
    page_number = request.GET.get('page')
    logs_page = paginator.get_page(page_number)

    context = {
        'task': task,
        'logs_page': logs_page,
    }

    return render(request, 'test_manager/scheduled_task_detail.html', context)


@login_required
def scheduled_task_edit(request, pk):
    """编辑定时任务 - 优化版本，确保立即同步到Celery Beat"""
    import logging
    logger = logging.getLogger(__name__)

    task = get_object_or_404(ScheduledTask, pk=pk, created_by=request.user)

    if request.method == 'POST':
        form = ScheduledTaskForm(request.POST, instance=task, test_suite_id=task.test_suite.id)
        if form.is_valid():
            try:
                # 保存原始的celery_task_id，用于删除旧任务
                old_celery_task_id = task.celery_task_id

                # 保存定时任务
                task = form.save()
                logger.info(f"定时任务已更新到数据库: {task.name} (ID: {task.id})")

                # 立即同步到Celery Beat
                try:
                    # 如果有旧的Celery任务，先删除
                    if old_celery_task_id:
                        try:
                            from django_celery_beat.models import PeriodicTask
                            old_task = PeriodicTask.objects.get(name=old_celery_task_id)
                            old_task.delete()
                            logger.info(f"已删除旧的Celery Beat任务: {old_celery_task_id}")
                        except PeriodicTask.DoesNotExist:
                            logger.warning(f"旧的Celery Beat任务不存在: {old_celery_task_id}")

                    # 计算下次执行时间
                    task.update_next_run_time()
                    logger.info(f"下次执行时间已更新: {task.next_run_time}")

                    # 创建新的Celery Beat任务
                    celery_task = TaskScheduler.create_or_update_celery_task(task)

                    if celery_task:
                        logger.info(f"Celery Beat任务更新成功: {task.celery_task_id}")
                        messages.success(
                            request,
                            f'定时任务 "{task.name}" 更新成功，已同步到调度器。下次执行时间: {task.next_run_time}'
                        )
                    else:
                        logger.warning(f"Celery Beat任务更新失败: {task.name}")
                        messages.warning(
                            request,
                            f'定时任务 "{task.name}" 更新成功，但同步到调度器失败。请检查Celery Beat服务状态。'
                        )

                    # 验证同步结果
                    from django_celery_beat.models import PeriodicTask
                    if task.celery_task_id and PeriodicTask.objects.filter(name=task.celery_task_id).exists():
                        logger.info(f"验证成功: Celery Beat任务已存在于数据库")
                        messages.info(request, f'调度器同步验证成功')
                    else:
                        logger.error(f"验证失败: Celery Beat任务不存在于数据库")
                        messages.error(request, f'调度器同步验证失败，任务可能无法按时执行')

                except Exception as sync_error:
                    logger.error(f"同步到Celery Beat失败: {str(sync_error)}")
                    logger.error(f"同步错误详情: {traceback.format_exc()}")
                    messages.error(
                        request,
                        f'定时任务更新成功，但同步到调度器失败: {str(sync_error)}'
                    )

                return redirect('scheduled_task_detail', pk=task.pk)

            except Exception as e:
                logger.error(f"更新定时任务失败: {str(e)}")
                logger.error(f"更新错误详情: {traceback.format_exc()}")
                messages.error(request, f'更新定时任务失败: {str(e)}')

    else:
        form = ScheduledTaskForm(instance=task, test_suite_id=task.test_suite.id)

    return render(request, 'test_manager/scheduled_task_form.html', {
        'form': form,
        'task': task,
        'title': f'编辑定时任务: {task.name}'
    })


@login_required
def scheduled_task_delete(request, pk):
    """删除定时任务 - 优化版本，确保同步删除Celery Beat任务"""
    import logging
    logger = logging.getLogger(__name__)

    task = get_object_or_404(ScheduledTask, pk=pk, created_by=request.user)

    if request.method == 'POST':
        task_name = task.name
        celery_task_id = task.celery_task_id

        try:
            logger.info(f"开始删除定时任务: {task_name} (ID: {task.id})")

            # 先删除Celery Beat任务
            if celery_task_id:
                try:
                    from django_celery_beat.models import PeriodicTask
                    celery_task = PeriodicTask.objects.get(name=celery_task_id)
                    celery_task.delete()
                    logger.info(f"成功删除Celery Beat任务: {celery_task_id}")
                    messages.info(request, f'已删除调度器中的任务: {celery_task_id}')
                except PeriodicTask.DoesNotExist:
                    logger.warning(f"Celery Beat任务不存在: {celery_task_id}")
                    messages.warning(request, f'调度器中的任务不存在: {celery_task_id}')
                except Exception as celery_error:
                    logger.error(f"删除Celery Beat任务失败: {str(celery_error)}")
                    logger.error(f"Celery删除错误详情: {traceback.format_exc()}")
                    messages.error(request, f'删除调度器任务失败: {str(celery_error)}')
            else:
                logger.info(f"任务没有关联的Celery Beat任务: {task_name}")

            # 删除数据库中的定时任务
            task.delete()
            logger.info(f"成功删除数据库中的定时任务: {task_name}")

            # 验证删除结果
            try:
                if celery_task_id:
                    from django_celery_beat.models import PeriodicTask
                    if not PeriodicTask.objects.filter(name=celery_task_id).exists():
                        logger.info(f"验证成功: Celery Beat任务已从数据库中删除")
                        messages.success(request, f'定时任务 "{task_name}" 已完全删除（包括调度器任务）')
                    else:
                        logger.error(f"验证失败: Celery Beat任务仍存在于数据库中")
                        messages.warning(request, f'定时任务 "{task_name}" 已删除，但调度器任务可能仍然存在')
                else:
                    messages.success(request, f'定时任务 "{task_name}" 已删除')
            except Exception as verify_error:
                logger.error(f"验证删除结果失败: {str(verify_error)}")
                messages.success(request, f'定时任务 "{task_name}" 已删除')

            return redirect('scheduled_task_list')

        except Exception as e:
            logger.error(f"删除定时任务失败: {str(e)}")
            logger.error(f"删除错误详情: {traceback.format_exc()}")
            messages.error(request, f'删除定时任务失败: {str(e)}')
            return redirect('scheduled_task_detail', pk=pk)

    return render(request, 'test_manager/scheduled_task_confirm_delete.html', {'task': task})


@login_required
@require_POST
def scheduled_task_toggle_status(request, pk):
    """切换定时任务状态 - 优化版本，确保立即同步到Celery Beat"""
    import logging
    logger = logging.getLogger(__name__)

    task = get_object_or_404(ScheduledTask, pk=pk, created_by=request.user)
    old_status = task.status

    try:
        if task.status == 'active':
            task.status = 'paused'
            message = f'定时任务 "{task.name}" 已暂停'
        else:
            task.status = 'active'
            task.update_next_run_time()
            message = f'定时任务 "{task.name}" 已激活'

        task.save()
        logger.info(f"任务状态已更新: {task.name} - {old_status} -> {task.status}")

        # 立即同步到Celery Beat
        try:
            if task.status == 'active':
                # 激活任务 - 创建Celery Beat任务
                celery_task = TaskScheduler.create_or_update_celery_task(task)
                if celery_task:
                    logger.info(f"Celery Beat任务已激活: {task.celery_task_id}")
                    message += f"，下次执行时间: {task.next_run_time}"
                else:
                    logger.warning(f"Celery Beat任务激活失败: {task.name}")
                    message += "，但调度器同步失败"
            else:
                # 暂停任务 - 删除Celery Beat任务
                TaskScheduler.delete_celery_task(task)
                logger.info(f"Celery Beat任务已暂停: {task.name}")

        except Exception as sync_error:
            logger.error(f"状态切换同步失败: {str(sync_error)}")
            message += f"，但调度器同步失败: {str(sync_error)}"

        messages.success(request, message)

        return JsonResponse({
            'success': True,
            'status': task.status,
            'message': message,
            'next_run_time': task.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if task.next_run_time else None
        })

    except Exception as e:
        logger.error(f"切换任务状态失败: {str(e)}")
        logger.error(f"状态切换错误详情: {traceback.format_exc()}")

        return JsonResponse({
            'success': False,
            'message': f'切换任务状态失败: {str(e)}',
            'error': str(e)
        })


# @login_required
@require_POST
def scheduled_task_run_now(request, pk):
    """立即执行定时任务"""
    try:
        task = get_object_or_404(ScheduledTask, pk=pk)
        print(f'[DEBUG] scheduled_task_run_now - 找到任务: {task.name} (ID: {task.id})')

        # 检查任务状态
        if not task.is_enabled:
            messages.error(request, f'定时任务 "{task.name}" 已禁用，无法执行')
            return JsonResponse({
                'success': False,
                'message': f'定时任务 "{task.name}" 已禁用，无法执行'
            })

        # 检查Celery是否可用
        try:
            from celery import current_app
            i = current_app.control.inspect()
            active_workers = i.active()

            if not active_workers:
                print('[ERROR] 没有活动的Celery worker')
                messages.error(request, 'Celery服务未运行，无法执行定时任务')
                return JsonResponse({
                    'success': False,
                    'message': 'Celery服务未运行，无法执行定时任务'
                })

            print(f'[DEBUG] 找到活动的Celery worker: {list(active_workers.keys())}')

        except Exception as celery_check_error:
            print(f'[ERROR] Celery状态检查失败: {str(celery_check_error)}')
            # 继续执行，可能是检查方法的问题

        # 尝试异步执行任务
        try:
            from .tasks import execute_scheduled_test_suite
            print(f'[DEBUG] 准备异步执行任务: {task.id}')
            result = execute_scheduled_test_suite.delay(task.id)
            print(f'[DEBUG] 任务已提交到Celery队列，task_id: {result.id}')

            messages.success(request, f'定时任务 "{task.name}" 已开始执行')

            return JsonResponse({
                'success': True,
                'message': f'定时任务 "{task.name}" 已开始执行',
                'task_id': result.id
            })

        except Exception as celery_error:
            print(f'[ERROR] Celery任务提交失败: {str(celery_error)}')
            print(f'[ERROR] 错误详情: {traceback.format_exc()}')

            # 尝试直接执行任务（同步方式）
            try:
                print(f'[DEBUG] 尝试同步执行任务: {task.id}')
                from .tasks import execute_scheduled_test_suite

                # 在后台线程中执行，避免阻塞请求
                import threading

                def run_task_sync():
                    try:
                        result = execute_scheduled_test_suite(task.id)
                        print(f'[DEBUG] 同步任务执行完成: {result}')
                    except Exception as sync_error:
                        print(f'[ERROR] 同步任务执行失败: {str(sync_error)}')
                        print(f'[ERROR] 同步任务错误详情: {traceback.format_exc()}')

                threading.Thread(target=run_task_sync, daemon=True).start()
                messages.success(request, f'定时任务 "{task.name}" 已在后台开始执行')
                return JsonResponse({
                    'success': True,
                    'message': f'定时任务 "{task.name}" 已在后台开始执行',
                })
            except Exception as sync_error:
                print(f'[ERROR] 同步启动线程失败: {str(sync_error)}')
                return JsonResponse({
                    'success': False,
                    'message': f'任务提交失败: {str(celery_error)}',
                }, status=500)

    except Exception as e:
        print(f'[ERROR] scheduled_task_run_now 视图异常: {str(e)}')
        print(f'[ERROR] 视图异常详情: {traceback.format_exc()}')
        messages.error(request, f'执行定时任务时发生错误: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': f'执行定时任务时发生错误: {str(e)}',
            'error': str(e)
        })


# ---- 测试管理（Vue 3 统一入口）----

@login_required
def test_manager_vue(request):
    """测试管理页面 — 已迁移至统一 SPA"""
    path = request.path
    redirect_map = {
        "/test-case-groups-vue/": "/app/#/test-case-groups",
        "/test-cases-vue/": "/app/#/test-cases",
        "/test-suite-groups-vue/": "/app/#/test-suite-groups",
        "/test-suites-vue/": "/app/#/test-suites",
    }
    return redirect(redirect_map.get(path, '/app/#/test-cases'))


@login_required
def ai_document_import(request):
    """文档导入API资产 — 已迁移至统一 SPA"""
    return redirect('/app/#/ai/document-import')


@login_required
def ai_generation_record(request):
    """AI生成记录 — 已迁移至统一 SPA"""
    return redirect('/app/#/ai/records')


@login_required
def ai_model_provider_list(request):
    """AI大模型管理 — 已迁移至统一 SPA"""
    return redirect('/app/#/ai/model-providers')


# @login_required
def task_execution_log_detail(request, pk):
    """任务执行日志详情"""
    log = get_object_or_404(TaskExecutionLog, pk=pk)
    print(f'[DEBUG] 找到任务执行日志: ',log)

    context = {
        'log': log,
    }

    return render(request, 'test_manager/task_execution_log_detail.html', context)