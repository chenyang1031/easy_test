"""
模块 B-8：场景执行报告异步导出 API（DRF）。

POST /api/v1/scene-executions/<id>/export-report/ 投递 Celery 任务，返回 task_id；
GET /api/v1/export-report-tasks/<task_id>/ 查询结果（report_id 或错误）。
参数经 queryset 过滤，避免跨项目 ID 遍历。
"""

from celery.result import AsyncResult
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from test_manager.models import TestSceneExecution
from test_manager.tasks import export_scene_execution_report_async


def _execution_queryset_for_user(user):
    qs = TestSceneExecution.objects.select_related("scene", "environment", "environment__project")
    if user.is_staff:
        return qs
    return qs.filter(environment__project__created_by=user)


class SceneExecutionExportReportView(APIView):
    """POST：异步导出场景执行报告。"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, execution_id):
        execution = get_object_or_404(_execution_queryset_for_user(request.user), pk=execution_id)
        async_result = export_scene_execution_report_async.delay(execution.id, request.user.id)
        return Response(
            {"task_id": async_result.id, "detail": "任务已提交，请使用 task_id 查询 export-report-tasks 获取 report_id"},
            status=status.HTTP_202_ACCEPTED,
        )


class SceneExecutionExportReportTaskView(APIView):
    """GET：查询异步导出任务结果。"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, task_id):
        r = AsyncResult(task_id)
        if r.state in ("PENDING", "STARTED", "RETRY"):
            return Response({"state": r.state}, status=status.HTTP_200_OK)
        if r.failed():
            return Response(
                {"state": "FAILURE", "error": str(r.result)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        payload = r.result
        if isinstance(payload, dict):
            err = payload.get("error")
            rid = payload.get("report_id")
            if err and err != "forbidden":
                return Response({"state": "FAILURE", "error": err}, status=status.HTTP_400_BAD_REQUEST)
            if err == "forbidden":
                return Response({"detail": "无权限"}, status=status.HTTP_403_FORBIDDEN)
            return Response({"state": "SUCCESS", "report_id": rid}, status=status.HTTP_200_OK)
        return Response({"state": "SUCCESS", "report_id": payload}, status=status.HTTP_200_OK)
