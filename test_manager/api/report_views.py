"""
测试报告 CRUD ViewSet + 文件下载。

GET    /api/v1/reports/          → 列表（支持 project / report_type / q 筛选、分页）
GET    /api/v1/reports/{id}/     → 详情（含 content 大字段）
POST   /api/v1/reports/          → 新建
PUT    /api/v1/reports/{id}/     → 编辑
DELETE /api/v1/reports/{id}/     → 删除
GET    /api/v1/reports/{id}/download/  → 下载报告为 HTML 文件
"""

import re

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q

from test_manager.models import TestReport

from .pagination import StandardResultsSetPagination
from .serializers import (
    TestReportListSerializer,
    TestReportDetailSerializer,
    TestReportCreateSerializer,
)


class TestReportViewSet(viewsets.ModelViewSet):
    """
    测试报告 CRUD。
    列表返回轻量数据（不含 content），详情返回完整数据。
    """
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return TestReportListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return TestReportCreateSerializer
        return TestReportDetailSerializer

    def get_queryset(self):
        qs = TestReport.objects.select_related(
            'project', 'created_by', 'scene_execution__scene'
        ).all()

        # 筛选
        project_id = self.request.query_params.get('project')
        report_type = self.request.query_params.get('report_type')
        search_query = self.request.query_params.get('q', '')

        if project_id:
            qs = qs.filter(project_id=project_id)
        if report_type:
            qs = qs.filter(report_type=report_type)
        if search_query:
            qs = qs.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        return qs.order_by('-created_at')


class ReportDownloadView(APIView):
    """
    GET /api/v1/reports/<id>/download/

    将报告内容作为 HTML 文件返回下载。
    仅支持 report_format='html' 的报告。
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        report = get_object_or_404(
            TestReport.objects.select_related('project'),
            pk=pk,
        )

        if report.report_format != 'html':
            return Response(
                {"detail": "仅 HTML 格式的报告支持下载"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        content = report.content or ""
        safe_name = re.sub(r'[\\/:*?\"<>|]', '_', report.name) or "report"
        filename = f"{safe_name}.html"

        response = HttpResponse(content, content_type='text/html; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(content.encode('utf-8'))
        return response
