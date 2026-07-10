"""场景执行报告 Web 视图（生成入口）。"""

import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from test_manager.forms import GenerateReportForm
from test_manager.models import TestSceneExecution

from .permissions import user_can_access_scene_execution_report
from .services import SceneExecutionReportValidationError, save_scene_execution_test_report


@login_required
def generate_scene_execution_report(request, execution_id):
    """
    GET: 展示生成表单；POST: 调用 build_scene_execution_report_content 写入 TestReport 并跳转详情。
    权限：同项目（Environment.project.created_by）或 staff。
    """
    execution = get_object_or_404(
        TestSceneExecution.objects.select_related("scene", "environment", "environment__project"),
        pk=execution_id,
    )
    if not user_can_access_scene_execution_report(request.user, execution):
        return HttpResponseForbidden("无权为该场景执行生成或查看报告（需为项目创建人或管理员）。")

    if request.method == "POST":
        form = GenerateReportForm(request.POST)
        if form.is_valid():
            try:
                report = save_scene_execution_test_report(
                    execution,
                    request.user,
                    name=form.cleaned_data["name"],
                    description=form.cleaned_data.get("description"),
                    report_format=form.cleaned_data["report_format"],
                    is_public=form.cleaned_data["is_public"],
                )
            except SceneExecutionReportValidationError as exc:
                messages.error(request, str(exc))
                return redirect("scene_execution_detail", pk=execution.pk)

            messages.success(request, f'测试报告 "{report.name}" 已生成')
            return redirect("test_report_detail", pk=report.pk)
    else:
        default_name = (
            f"{execution.scene.name} - 场景执行报告 - "
            f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        form = GenerateReportForm(initial={"name": default_name, "report_format": "html"})

    return render(
        request,
        "test_manager/generate_test_report.html",
        {
            "form": form,
            "scene_execution": execution,
        },
    )
