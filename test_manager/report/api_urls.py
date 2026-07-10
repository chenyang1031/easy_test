"""API v1 路由：场景执行报告异步导出（与 Web 版 report/urls 区分）。"""

from django.urls import path

from .api_views import SceneExecutionExportReportTaskView, SceneExecutionExportReportView

urlpatterns = [
    path(
        "scene-executions/<int:execution_id>/export-report/",
        SceneExecutionExportReportView.as_view(),
        name="api_v1_scene_execution_export_report",
    ),
    path(
        "export-report-tasks/<str:task_id>/",
        SceneExecutionExportReportTaskView.as_view(),
        name="api_v1_export_report_task",
    ),
]
