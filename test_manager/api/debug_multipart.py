"""
临时调试端点：捕获 multipart 请求内容，排查文件上传问题。
使用后请删除此文件和 urls.py 中的路由。
"""
import json
import os
import tempfile
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


@csrf_exempt
@require_POST
def debug_multipart(request):
    """接收 multipart 请求，返回收到的字段和文件信息。"""
    result = {
        "content_type": request.content_type,
        "content_length": request.META.get("CONTENT_LENGTH"),
        "POST_fields": {},
        "FILES": {},
        "raw_body_snippet": "",
    }

    # 普通字段
    for key, value in request.POST.items():
        result["POST_fields"][key] = value[:200] if isinstance(value, str) else str(value)[:200]

    # 文件字段
    for key, uploaded_file in request.FILES.items():
        result["FILES"][key] = {
            "name": uploaded_file.name,
            "size": uploaded_file.size,
            "content_type": uploaded_file.content_type,
            "charset": getattr(uploaded_file, "charset", None),
        }

    return JsonResponse(result, json_dumps_params={"ensure_ascii": False, "indent": 2})
