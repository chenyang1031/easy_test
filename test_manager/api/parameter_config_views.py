"""
参数配置 API ViewSet

- ParameterConfigViewSet — list / update (read-write)
"""
import json
import logging

from django.shortcuts import get_object_or_404

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from test_manager.models import ParameterConfig
from test_manager.views import ensure_ai_parameter_configs

from .serializers import ParameterConfigSerializer

logger = logging.getLogger(__name__)


class ParameterConfigViewSet(viewsets.ModelViewSet):
    """参数配置 CRUD"""

    queryset = ParameterConfig.objects.all()
    serializer_class = ParameterConfigSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        ensure_ai_parameter_configs()
        category = self.request.query_params.get("category", "").strip()
        qs = ParameterConfig.objects.all().order_by("category", "key")
        if category:
            qs = qs.filter(category=category)
        return qs

    @action(detail=False, methods=["post"])
    def test_ai(self, request):
        """测试 AI 接口连通性"""
        return self._test_ai_connection()

    def _test_ai_connection(self):
        """执行 AI 接口测试逻辑（与原有 parameter_config_test_ai 对齐）"""
        ensure_ai_parameter_configs()

        base_url = (ParameterConfig.get_value("AI_API_BASE_URL", "") or "").strip()
        api_path = (
            ParameterConfig.get_value("AI_API_GENERATE_MULTI_CASES_PATH", "") or ""
        ).strip()
        api_method = (
            ParameterConfig.get_value("AI_API_METHOD", "POST") or "POST"
        ).upper().strip()
        auth_token = (
            ParameterConfig.get_value("AI_API_AUTH_TOKEN", "") or ""
        ).strip()
        timeout_text = (
            ParameterConfig.get_value("AI_API_TIMEOUT_SECONDS", "30") or "30"
        ).strip()
        extra_headers_text = (
            ParameterConfig.get_value("AI_API_EXTRA_HEADERS_JSON", "{}") or "{}"
        ).strip()
        response_cases_path = (
            ParameterConfig.get_value(
                "AI_API_RESPONSE_CASES_PATH", "data.cases"
            )
            or "data.cases"
        ).strip()

        if not base_url or not api_path:
            return Response(
                {
                    "success": False,
                    "message": "配置缺失：请先设置AI_API_BASE_URL和AI_API_GENERATE_MULTI_CASES_PATH",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            timeout_seconds = float(timeout_text)
        except (TypeError, ValueError):
            timeout_seconds = 30.0

        try:
            extra_headers = json.loads(extra_headers_text or "{}")
            if not isinstance(extra_headers, dict):
                return Response(
                    {
                        "success": False,
                        "message": "AI_API_EXTRA_HEADERS_JSON 必须是JSON对象",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except (TypeError, ValueError):
            return Response(
                {"success": False, "message": "AI_API_EXTRA_HEADERS_JSON 不是合法JSON"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        import requests as req_lib

        url = f"{base_url.rstrip('/')}/{api_path.lstrip('/')}"
        headers = {"Content-Type": "application/json"}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        headers.update(extra_headers)

        payload = {
            "prompt": "Hello",
            "test_case_count": 1,
            "language": "zh-CN",
        }

        try:
            method_fn = getattr(req_lib, api_method.lower(), req_lib.post)
            resp = method_fn(
                url,
                json=payload,
                headers=headers,
                timeout=timeout_seconds,
            )

            if resp.status_code < 200 or resp.status_code >= 300:
                return Response(
                    {
                        "success": False,
                        "message": f"请求失败 (HTTP {resp.status_code}): {resp.text[:500]}",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                resp_data = resp.json()
            except Exception:
                return Response(
                    {
                        "success": False,
                        "message": f"响应不是合法 JSON: {resp.text[:500]}",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            from test_manager.views import _extract_json_by_path

            cases = _extract_json_by_path(resp_data, response_cases_path)
            has_cases = isinstance(cases, list) and len(cases) > 0

            return Response({
                "success": True,
                "message": "AI 接口测试成功"
                if has_cases
                else "接口连通但未找到用例数据（可能路径配置有误）",
                "has_cases": has_cases,
            })

        except req_lib.exceptions.Timeout:
            return Response(
                {
                    "success": False,
                    "message": f"请求超时（{timeout_seconds}秒），请检查接口地址或延长超时时间",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"连接失败: {str(e)[:300]}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
