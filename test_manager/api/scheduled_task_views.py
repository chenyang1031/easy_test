"""
定时任务 API（DRF ViewSet）
===================================
- ScheduledTaskViewSet    — CRUD + toggle_status + run_now
- TaskExecutionLogViewSet — 只读，按 scheduled_task 过滤
- TaskMonitorView         — DB / Celery 状态监控看板
"""

import logging
import traceback

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django_celery_beat.models import PeriodicTask

from rest_framework import permissions, status, viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from test_manager.models import ScheduledTask, TaskExecutionLog
from test_manager.scheduler import TaskScheduler

from .serializers import ScheduledTaskSerializer, TaskExecutionLogSerializer
from .pagination import StandardResultsSetPagination

logger = logging.getLogger(__name__)


class ScheduledTaskViewSet(viewsets.ModelViewSet):
    """定时任务 CRUD"""

    queryset = ScheduledTask.objects.all()
    serializer_class = ScheduledTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ScheduledTask.objects.filter(created_by=self.request.user)
        qs = qs.select_related("test_suite", "test_scene", "environment", "created_by")

        # 搜索
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(test_suite__name__icontains=search)
                | Q(test_scene__name__icontains=search)
            )

        # 状态筛选
        status_filter = self.request.query_params.get("status", "").strip()
        if status_filter:
            qs = qs.filter(status=status_filter)

        # 测试套件筛选
        test_suite_id = self.request.query_params.get("test_suite", "").strip()
        if test_suite_id:
            qs = qs.filter(test_suite_id=test_suite_id)

        # 测试场景筛选
        test_scene_id = self.request.query_params.get("test_scene", "").strip()
        if test_scene_id:
            qs = qs.filter(test_scene_id=test_scene_id)

        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        task = serializer.save()
        self._sync_celery(task)

    def perform_update(self, serializer):
        old_instance = serializer.instance
        old_celery_id = old_instance.celery_task_id
        old_schedule_type = old_instance.schedule_type

        task = serializer.save()

        # 删除旧 Celery 任务（用完整的 instance 信息来 revocation）
        if old_celery_id:
            try:
                # 构造一个临时的 task 对象，携带旧状态信息
                class _OldTask:
                    celery_task_id = old_celery_id
                    schedule_type = old_schedule_type
                TaskScheduler.delete_celery_task(_OldTask())
            except Exception:
                pass

        self._sync_celery(task)

    def perform_destroy(self, instance):
        # 先记录需要清理的信息再删除
        old_celery_id = instance.celery_task_id
        old_schedule_type = instance.schedule_type
        instance.delete()
        # 同步删除 Celery 任务
        if old_celery_id:
            try:
                class _OldTask:
                    celery_task_id = old_celery_id
                    schedule_type = old_schedule_type
                TaskScheduler.delete_celery_task(_OldTask())
            except Exception as e:
                logger.warning(f"删除 Celery 任务失败: {e}")

    # ── 自定义动作 ──

    @action(detail=True, methods=["post"])
    def toggle_status(self, request, pk=None):
        """切换 active / paused 状态"""
        task = self.get_object()
        old_status = task.status

        try:
            if task.status == "active":
                task.status = "paused"
                message = f"定时任务「{task.name}」已暂停"
                TaskScheduler.delete_celery_task(task)
            else:
                task.status = "active"
                task.update_next_run_time()
                message = f"定时任务「{task.name}」已激活"
                TaskScheduler.create_or_update_celery_task(task)

            task.save(update_fields=["status", "next_run_time"])

            return Response({
                "success": True,
                "status": task.status,
                "message": message,
                "next_run_time": (
                    task.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
                    if task.next_run_time else None
                ),
            })
        except Exception as e:
            logger.error(f"切换任务状态失败: {e}")
            return Response(
                {"success": False, "message": f"操作失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"])
    def run_now(self, request, pk=None):
        """立即执行定时任务"""
        task = self.get_object()

        if not task.is_enabled:
            return Response(
                {"success": False, "message": "该任务已禁用，无法执行"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from test_manager.tasks import execute_scheduled_test_suite

            result = execute_scheduled_test_suite.delay(task.id)
            return Response({
                "success": True,
                "message": f"任务「{task.name}」已开始执行",
                "task_id": result.id,
            })
        except Exception as e:
            logger.error(f"执行任务失败: {e}\n{traceback.format_exc()}")
            # 降级：同步执行
            try:
                import threading

                def run_sync():
                    try:
                        from test_manager.tasks import execute_scheduled_test_suite
                        execute_scheduled_test_suite(task.id)
                    except Exception:
                        pass

                threading.Thread(target=run_sync, daemon=True).start()
                return Response({
                    "success": True,
                    "message": f"任务「{task.name}」已在后台开始执行（同步模式）",
                })
            except Exception as e2:
                return Response(
                    {"success": False, "message": f"执行失败: {str(e2)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

    # ── 辅助方法 ──

    def _sync_celery(self, task):
        """创建 / 更新 Celery Beat 任务"""
        try:
            task.update_next_run_time()
            TaskScheduler.create_or_update_celery_task(task)
        except Exception as e:
            logger.warning(f"同步 Celery Beat 失败: {e}")


class TaskExecutionLogViewSet(mixins.RetrieveModelMixin,
                               mixins.ListModelMixin,
                               mixins.DestroyModelMixin,
                               viewsets.GenericViewSet):
    """任务执行日志（读+删，支持分页与筛选）"""

    queryset = TaskExecutionLog.objects.all()
    serializer_class = TaskExecutionLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = TaskExecutionLog.objects.select_related(
            "scheduled_task", "test_run", "scene_execution", "scene_execution__scene"
        )

        # 按定时任务 ID 筛选
        task_id = self.request.query_params.get("scheduled_task", "").strip()
        if task_id:
            qs = qs.filter(scheduled_task_id=task_id)

        # 按状态筛选
        status = self.request.query_params.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)

        # 按任务名称搜索（关联 scheduled_task.name）
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(scheduled_task__name__icontains=search)

        # 按开始时间范围筛选
        date_from = self.request.query_params.get("date_from", "").strip()
        if date_from:
            qs = qs.filter(start_time__gte=date_from)

        date_to = self.request.query_params.get("date_to", "").strip()
        if date_to:
            qs = qs.filter(start_time__lte=date_to)

        return qs.order_by("-start_time")


class TaskMonitorView(APIView):
    """定时任务监控状态 API — GET"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """获取监控状态：DB 任务数 / Celery 任务数 / Beat 状态 / 任务列表"""
        try:
            db_tasks = ScheduledTask.objects.filter(is_enabled=True, status="active")
            celery_tasks = PeriodicTask.objects.filter(
                enabled=True, name__startswith="scheduled_task_"
            )
            beat_status = TaskScheduler.get_celery_beat_status()

            tasks_data = []
            for task in db_tasks:
                tasks_data.append({
                    "id": task.id,
                    "name": task.name,
                    "test_suite_name": task.test_suite.name if task.test_suite else None,
                    "test_scene_name": task.test_scene.name if task.test_scene else None,
                    "schedule_type": task.schedule_type,
                    "schedule_type_display": task.get_schedule_type_display(),
                    "next_run_time": (
                        task.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
                        if task.next_run_time else None
                    ),
                    "last_run_time": (
                        task.last_run_time.strftime("%Y-%m-%d %H:%M:%S")
                        if task.last_run_time else None
                    ),
                    "success_rate": task.success_rate,
                    "celery_synced": bool(task.celery_task_id),
                    "celery_task_id": task.celery_task_id,
                })

            return Response({
                "success": True,
                "db_tasks_count": db_tasks.count(),
                "celery_tasks_count": celery_tasks.count(),
                "beat_status": beat_status,
                "tasks": tasks_data,
            })
        except Exception as e:
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TaskSyncView(APIView):
    """同步所有任务到 Celery Beat — POST"""

    permission_classes = [permissions.IsAuthenticated]

    @method_decorator(csrf_protect)
    def post(self, request):
        try:
            success_count = TaskScheduler.sync_all_tasks()
            return Response({
                "success": True,
                "message": f"成功同步 {success_count} 个任务",
            })
        except Exception as e:
            return Response(
                {"success": False, "message": f"同步失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TaskCleanupView(APIView):
    """清理孤立 Celery 任务 — POST"""

    permission_classes = [permissions.IsAuthenticated]

    @method_decorator(csrf_protect)
    def post(self, request):
        try:
            cleaned_count = TaskScheduler.cleanup_orphaned_celery_tasks()
            return Response({
                "success": True,
                "message": f"清理了 {cleaned_count} 个孤立任务",
            })
        except Exception as e:
            return Response(
                {"success": False, "message": f"清理失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
