"""
邮件配置 API ViewSet

- EmailConfigViewSet — CRUD + test_email + activate
"""
import logging

from django.shortcuts import get_object_or_404

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from test_manager.models import EmailConfig

from .serializers import EmailConfigSerializer

logger = logging.getLogger(__name__)


class EmailConfigViewSet(viewsets.ModelViewSet):
    """邮件配置 CRUD"""

    queryset = EmailConfig.objects.all()
    serializer_class = EmailConfigSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return EmailConfig.objects.all().order_by("-updated_at")

    @action(detail=True, methods=["post"])
    def test_email(self, request, pk=None):
        """发送测试邮件"""
        config = self.get_object()
        email = request.data.get("email", "").strip()

        if not email:
            return Response(
                {"detail": "请填写测试邮箱地址"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        success, message = config.send_test_email(email)
        if success:
            return Response({"success": True, "detail": message})
        return Response(
            {"success": False, "detail": message},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=["post"])
    def test_connection(self, request, pk=None):
        """测试邮件服务器连接"""
        config = self.get_object()
        success, message = config.test_connection()
        if success:
            return Response({"success": True, "detail": message})
        return Response(
            {"success": False, "detail": message},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        """激活邮件配置"""
        config = self.get_object()
        config.is_active = True
        config.save()
        return Response({
            "success": True,
            "detail": f"邮件配置「{config.name}」已激活",
        })
