"""
日志查询 API - 读取服务器日志、SSE 流式推送、执行命令
"""
import os
import time
import subprocess

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse, JsonResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

LOG_DIR = settings.LOGS_DIR
ALLOWED_LOG_FILES = ['django.log']
COMMAND_TIMEOUT = 30
MAX_OUTPUT_SIZE = 1024 * 512


def _resolve_log_path(filename):
    """安全解析日志文件路径，防止目录穿越"""
    if filename not in ALLOWED_LOG_FILES:
        return None
    path = os.path.normpath(os.path.join(str(LOG_DIR), filename))
    if not path.startswith(os.path.normpath(str(LOG_DIR))):
        return None
    return path


class LogListView(APIView):
    """列出可用的日志文件"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        files = []
        for name in ALLOWED_LOG_FILES:
            path = os.path.join(str(LOG_DIR), name)
            if os.path.exists(path):
                files.append({
                    'name': name,
                    'size': os.path.getsize(path),
                    'modified': os.path.getmtime(path),
                })
        return Response(files)


class LogReadView(APIView):
    """读取日志文件内容（返回最后 N 行）"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        filename = request.query_params.get('file', 'django.log')
        try:
            lines = int(request.query_params.get('lines', 500))
        except (ValueError, TypeError):
            lines = 500
        lines = min(lines, 5000)

        filepath = _resolve_log_path(filename)
        if not filepath or not os.path.exists(filepath):
            return Response({'error': '日志文件不存在'}, status=status.HTTP_404_NOT_FOUND)

        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                all_lines = f.readlines()
            result_lines = all_lines[-lines:]
            return Response({
                'file': filename,
                'total_lines': len(all_lines),
                'content': ''.join(result_lines),
                'returned_lines': len(result_lines),
            })
        except Exception as e:
            return Response({'error': f'读取日志失败: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@login_required
def log_stream_view(request):
    """SSE 流式推送日志（原生 Django 视图，避免 DRF 内容协商干扰 EventSource）"""
    filename = request.GET.get('file', 'django.log')
    filepath = _resolve_log_path(filename)
    if not filepath or not os.path.exists(filepath):
        return JsonResponse({'error': '日志文件不存在'}, status=404)

    def event_stream():
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                f.seek(0, 2)  # 跳到文件末尾
                while True:
                    line = f.readline()
                    if line:
                        yield f"data: {line.rstrip()}\n\n"
                    else:
                        time.sleep(0.5)
        except GeneratorExit:
            pass
        except Exception as e:
            yield f"data: [ERROR] {e}\n\n"

    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


class CommandExecuteView(APIView):
    """执行 Shell 命令（仅管理员）"""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        command = request.data.get('command', '').strip()
        if not command:
            return Response({'error': '命令不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        # 禁止危险命令
        dangerous = ['rm -rf /', 'mkfs', 'dd if=', ':(){', 'fork bomb']
        cmd_lower = command.lower()
        for d in dangerous:
            if d in cmd_lower:
                return Response({'error': '命令被安全策略拦截'}, status=status.HTTP_403_FORBIDDEN)

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT,
                cwd=str(settings.BASE_DIR),
            )
            return Response({
                'returncode': result.returncode,
                'stdout': result.stdout[:MAX_OUTPUT_SIZE],
                'stderr': result.stderr[:MAX_OUTPUT_SIZE],
                'command': command,
            })
        except subprocess.TimeoutExpired:
            return Response({
                'returncode': -1,
                'stdout': '',
                'stderr': f'命令执行超时（{COMMAND_TIMEOUT}秒）',
                'command': command,
            })
        except Exception as e:
            return Response({
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'command': command,
            })
