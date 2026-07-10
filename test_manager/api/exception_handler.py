"""
统一 DRF 异常处理器

标准化所有 API 错误响应格式为 {"detail": "..."}，
避免部分接口返回 {"error": "..."} 的不一致问题。
"""
import logging
import traceback

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def unified_exception_handler(exc, context):
    """
    统一 DRF 异常处理器。

    确保所有错误响应格式一致：
    {"detail": "...", "code": "..."}
    """
    # 先调用 DRF 默认处理器
    response = drf_exception_handler(exc, context)

    if response is not None:
        # 标准化响应格式
        data = response.data

        # 如果 data 已经是 dict，确保含有 'detail' 字段
        if isinstance(data, dict):
            # 如果有 'error' 字段但没有 'detail'，统一为 'detail'
            if 'error' in data and 'detail' not in data:
                data['detail'] = data.pop('error')
        elif isinstance(data, list):
            # 列表格式转为 detail
            data = {'detail': '; '.join(str(item) for item in data)}
            response.data = data

        # validation error 的 detail 可能是 dict，保持原样（DRF 标准行为）
        return response

    # 处理 DRF 默认处理器未覆盖的异常
    if isinstance(exc, Http404):
        return Response({'detail': '资源未找到'}, status=404)
    if isinstance(exc, PermissionDenied):
        return Response({'detail': '权限不足'}, status=403)
    if isinstance(exc, DjangoValidationError):
        return Response({'detail': str(exc)}, status=400)

    # 非 DRF 异常：开发环境返回详细信息，生产环境返回通用信息
    if not settings.DEBUG:
        logger.error(
            '未捕获异常: %s: %s\n%s',
            type(exc).__name__, exc,
            traceback.format_exc(),
        )
        return Response(
            {'detail': '服务器内部错误'},
            status=500,
        )

    # 开发环境透传异常
    return Response(
        {'detail': f'{type(exc).__name__}: {str(exc)}'},
        status=500,
    )
