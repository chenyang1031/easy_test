"""
性能测试批量执行 API - ViewSet 与序列化器

支持批量任务 CRUD、启动压测、获取进度与聚合报告。
"""
from django.conf import settings as django_settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from test_manager.models import PerformanceBatchTask, PerformanceBatchItem, PerformanceTestTask, Project
from test_manager.utils.performance_batch_schedule import start_performance_batch
from test_manager.utils.performance_batch_report import build_batch_report_dict, serialize_batch_report_response
from .serializers import UserSerializer
from .pagination import StandardResultsSetPagination


def _can_access_project(user, project):
    """项目成员：管理员或项目创建人"""
    if user.is_staff:
        return True
    return project.created_by_id == user.id


def _performance_batch_queryset_for_user(user):
    """返回当前用户有权限的批量任务 queryset"""
    if user.is_staff:
        return PerformanceBatchTask.objects.all()
    return PerformanceBatchTask.objects.filter(project__created_by=user)


# --- 序列化器 ---

class PerformanceBatchTaskSerializer(serializers.ModelSerializer):
    """批量任务序列化器 - 支持创建/更新/查询"""

    creator = UserSerializer(read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)
    success_rate_percent = serializers.ReadOnlyField(source="success_rate")
    progress_percent = serializers.ReadOnlyField(source="progress")
    # 写入时接收任务 ID 列表，只写不读
    performance_task_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        default=list,
    )

    class Meta:
        model = PerformanceBatchTask
        fields = [
            "id",
            "name",
            "project",
            "project_name",
            "execute_mode",
            "max_concurrent",
            "total_tasks",
            "completed_tasks",
            "successful_tasks",
            "failed_tasks",
            "running_tasks",
            "status",
            "creator",
            "created_at",
            "started_at",
            "finished_at",
            "description",
            "success_rate_percent",
            "progress_percent",
            "performance_task_ids",
        ]
        read_only_fields = [
            "creator",
            "created_at",
            "started_at",
            "finished_at",
            "total_tasks",
            "completed_tasks",
            "successful_tasks",
            "failed_tasks",
            "running_tasks",
            "status",
        ]

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user
        task_ids = validated_data.pop("performance_task_ids", [])
        batch = super().create(validated_data)
        # 创建批量任务项
        items = []
        for idx, task_id in enumerate(task_ids):
            items.append(PerformanceBatchItem(
                batch=batch,
                performance_task_id=task_id,
                order_index=idx,
                status=PerformanceBatchItem.STATUS_PENDING,
            ))
        if items:
            PerformanceBatchItem.objects.bulk_create(items)
            batch.total_tasks = len(items)
            batch.save(update_fields=["total_tasks"])
        return batch

    def update(self, instance, validated_data):
        task_ids = validated_data.pop("performance_task_ids", None)
        instance = super().update(instance, validated_data)
        # 仅在提供了 performance_task_ids 时更新任务项
        if task_ids is not None:
            # 只能在 pending 状态下修改任务项
            if instance.status != PerformanceBatchTask.STATUS_PENDING:
                raise ValidationError({"detail": "只有待执行状态下才能修改任务项"})
            PerformanceBatchItem.objects.filter(batch=instance).delete()
            items = [
                PerformanceBatchItem(
                    batch=instance,
                    performance_task_id=tid,
                    order_index=idx,
                    status=PerformanceBatchItem.STATUS_PENDING,
                )
                for idx, tid in enumerate(task_ids)
            ]
            if items:
                PerformanceBatchItem.objects.bulk_create(items)
            instance.total_tasks = len(items)
            instance.save(update_fields=["total_tasks"])
        return instance


class PerformanceBatchItemSerializer(serializers.ModelSerializer):
    """批量任务项序列化器"""

    task_name = serializers.CharField(source="performance_task.name", read_only=True)
    interface_url = serializers.CharField(source="performance_task.interface.url", read_only=True)
    method = serializers.CharField(source="performance_task.interface.method", read_only=True)
    environment_name = serializers.CharField(source="performance_task.environment.name", read_only=True)

    class Meta:
        model = PerformanceBatchItem
        fields = [
            "id",
            "batch",
            "performance_task",
            "task_name",
            "interface_url",
            "method",
            "environment_name",
            "status",
            "order_index",
            "started_at",
            "finished_at",
            "error_message",
            "result_summary",
        ]


class PerformanceBatchTaskViewSet(viewsets.ModelViewSet):
    """批量任务 ViewSet - CRUD + 启动压测 + 获取进度/报告"""

    serializer_class = PerformanceBatchTaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = (
            _performance_batch_queryset_for_user(self.request.user)
            .select_related("project", "creator")
            .order_by("-created_at")
        )
        project_id = self.request.query_params.get("project")
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

    def _ensure_project_permission(self, batch):
        if not _can_access_project(self.request.user, batch.project):
            raise PermissionDenied("无权限操作该项目下的批量任务")

    def perform_create(self, serializer):
        project = get_object_or_404(Project, id=serializer.validated_data["project"].id)
        if not _can_access_project(self.request.user, project):
            raise PermissionDenied("无权限在该项目下创建批量任务")
        serializer.save()

    def perform_update(self, serializer):
        batch = self.get_object()
        self._ensure_project_permission(batch)
        serializer.save()

    def perform_destroy(self, instance):
        self._ensure_project_permission(instance)
        if instance.status != PerformanceBatchTask.STATUS_PENDING:
            raise ValidationError({"detail": "只有待执行状态才能删除批量任务"})
        instance.delete()

    @action(detail=True, methods=["post"], url_path="start")
    def start_batch(self, request, pk=None):
        """
        启动批量压测：根据执行模式（串行/并行）依次/并发执行所有任务项。
        """
        pk = self.kwargs.get("pk") or pk
        with transaction.atomic():
            batch = get_object_or_404(self.get_queryset().select_for_update(), pk=pk)
            self._ensure_project_permission(batch)

            if batch.status == PerformanceBatchTask.STATUS_RUNNING:
                raise ValidationError({"detail": "批量任务正在执行中，请稍后再试"})

            if batch.status != PerformanceBatchTask.STATUS_PENDING:
                raise ValidationError({"detail": "该状态不能启动批量任务，只有「待执行」状态可以启动"})

            items = list(PerformanceBatchItem.objects.filter(batch=batch).select_related("performance_task"))
            if not items:
                raise ValidationError({"detail": "批量任务中没有可执行的任务项，请先添加性能测试任务"})

            # 检查所有子任务是否可用
            for item in items:
                task = item.performance_task
                if task.status == PerformanceTestTask.STATUS_RUNNING:
                    raise ValidationError({
                        "detail": f"任务【{task.name}】正在执行中，无法加入批量"
                    })

            batch_id = batch.id
            transaction.on_commit(lambda bid=batch_id: start_performance_batch(bid))

        batch.refresh_from_db()
        serializer = self.get_serializer(batch)
        payload = {
            "message": "批量任务已提交，正在执行中",
            "batch": serializer.data,
        }
        mode = str(getattr(django_settings, "PERFORMANCE_TEST_EXECUTOR", "process")).strip().lower() or "process"
        if mode == "celery":
            payload["hint"] = "使用 Celery 集群执行，请监控 Worker 状态"
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="stop")
    def stop_batch(self, request, pk=None):
        """
        停止批量执行中的所有运行中的任务。
        """
        batch = self.get_object()
        self._ensure_project_permission(batch)

        if batch.status not in [PerformanceBatchTask.STATUS_RUNNING, PerformanceBatchTask.STATUS_PARTIAL_SUCCESS]:
            raise ValidationError({"detail": "只有运行中的批量任务才能停止"})

        from test_manager.utils.performance_stop import stop_performance_task

        running_items = list(PerformanceBatchItem.objects.filter(
            batch=batch,
            status=PerformanceBatchItem.STATUS_RUNNING
        ).select_related("performance_task"))

        stopped_count = 0
        for item in running_items:
            task = item.performance_task
            try:
                stop_performance_task(task=task, user=request.user, reason="批量任务已手动停止")
                item.status = PerformanceBatchItem.STATUS_SKIPPED
                item.error_message = "批量任务已手动停止"
                item.finished_at = timezone.now()
                item.save(update_fields=["status", "error_message", "finished_at"])
                stopped_count += 1
            except Exception:
                pass

        batch.status = PerformanceBatchTask.STATUS_COMPLETED
        batch.finished_at = timezone.now()
        batch.save(update_fields=["status", "finished_at"])

        batch.refresh_from_db()
        serializer = self.get_serializer(batch)
        return Response(
            {
                "message": f"批量任务已停止，已停止 {stopped_count} 个运行中的任务",
                "batch": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="items")
    def get_items(self, request, pk=None):
        """
        获取批量任务中的所有任务项，支持分页和状态筛选
        """
        batch = self.get_object()
        self._ensure_project_permission(batch)

        status_filter = request.query_params.get("status")
        qs = PerformanceBatchItem.objects.filter(batch=batch).select_related(
            "performance_task__interface", "performance_task__environment"
        ).order_by("order_index")
        if status_filter:
            qs = qs.filter(status=status_filter)

        paginator = StandardResultsSetPagination()
        paginated = paginator.paginate_queryset(qs, request)
        serializer = PerformanceBatchItemSerializer(paginated, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(detail=True, methods=["get"], url_path="report")
    def get_batch_report(self, request, pk=None):
        """
        获取批量任务的聚合报告：所有子任务的汇总统计
        """
        batch = self.get_object()
        self._ensure_project_permission(batch)

        report = build_batch_report_dict(batch)
        payload = serialize_batch_report_response(batch, report)
        return Response(payload, status=status.HTTP_200_OK)
