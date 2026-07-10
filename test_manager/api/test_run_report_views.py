"""
测试运行报告生成 API（DRF）。
POST /api/v1/test-runs/<test_run_id>/generate-report/
    → 调用 save_test_run_test_report() 生成报告并返回 TestReport 详情。
"""

from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from test_manager.models.test_case import TestRun
from test_manager.report.services import save_test_run_test_report

from .serializers import TestReportDetailSerializer


class TestRunGenerateReportView(APIView):
    """
    POST /api/v1/test-runs/<test_run_id>/generate-report/

    请求体: {name, description?, report_format, is_public?}
    返回: 201 + 新创建的 TestReport 详情
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, test_run_id):
        test_run = get_object_or_404(
            TestRun.objects.select_related("project", "environment", "test_suite"),
            pk=test_run_id,
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
            report = save_test_run_test_report(
                test_run,
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
