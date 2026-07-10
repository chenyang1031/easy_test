"""
场景执行报告生成 API（DRF）。
POST /api/v1/scene-executions/<execution_id>/generate-report/
    → 调用 save_scene_execution_test_report() 生成报告并返回 TestReport 详情。
"""

from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from test_manager.models import TestSceneExecution
from test_manager.report.services import save_scene_execution_test_report
from test_manager.report.permissions import user_can_access_scene_execution_report

from .serializers import TestReportDetailSerializer


class SceneExecutionGenerateReportView(APIView):
    """
    POST /api/v1/scene-executions/<execution_id>/generate-report/

    请求体: {name, description?, report_format, is_public?}
    返回: 201 + 新创建的 TestReport 详情
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, execution_id):
        execution = get_object_or_404(
            TestSceneExecution.objects.select_related(
                "scene", "environment", "environment__project"
            ),
            pk=execution_id,
        )

        # 权限检查（复用 report 模块的权限函数）
        if not user_can_access_scene_execution_report(request.user, execution):
            return Response(
                {"detail": "无权为该场景执行生成报告（需为项目创建人或管理员）。"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # 校验请求参数
        name = request.data.get("name", "").strip()
        if not name:
            return Response(
                {"name": ["报告名称不能为空。"]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        report_format = request.data.get("report_format", "html")
        if report_format not in ("html", "json"):
            return Response(
                {"report_format": ["报告格式仅支持 html 或 json。"]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        description = request.data.get("description", "").strip()
        is_public = request.data.get("is_public", False)

        try:
            report = save_scene_execution_test_report(
                execution,
                request.user,
                name=name,
                description=description,
                report_format=report_format,
                is_public=bool(is_public),
            )
        except Exception as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TestReportDetailSerializer(report, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
