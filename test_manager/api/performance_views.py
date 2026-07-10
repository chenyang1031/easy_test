"""
性能测试 API - ViewSet 与序列化器

支持任务 CRUD、启动压测、获取结果与报告。
"""
from django.conf import settings as django_settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from test_manager.models import PerformanceTestTask, PerformanceTestResult, Project
from test_manager.utils.performance_config import (
    PerformanceConfigError,
    validate_csv_file_size,
    validate_extra_config_for_task,
)
from test_manager.utils.performance_report import build_performance_report_dict, serialize_report_response
from test_manager.utils.performance_diagnostics import build_performance_diagnostics
from test_manager.utils.performance_schedule import check_celery_workers, schedule_performance_test
from test_manager.utils.performance_stop import stop_performance_task
from .serializers import UserSerializer


def _can_access_project(user, project):
    """项目成员：管理员或项目创建人"""
    if user.is_staff:
        return True
    return project.created_by_id == user.id


def _performance_task_queryset_for_user(user):
    """返回当前用户有权限的性能测试任务 queryset"""
    if user.is_staff:
        return PerformanceTestTask.objects.all()
    return PerformanceTestTask.objects.filter(project__created_by=user)


from .pagination import StandardResultsSetPagination


# --- 序列化器 ---


class _EmptyAsNullFloatField(serializers.FloatField):

    def to_internal_value(self, data):
        if data in (None, "", "null"):
            return None
        return super().to_internal_value(data)


class PerformanceTestTaskSerializer(serializers.ModelSerializer):
    """性能测试任务序列化器 - 支持创建/更新/查询"""

    creator = UserSerializer(read_only=True)
    stopped_by = UserSerializer(read_only=True, allow_null=True)
    project_name = serializers.CharField(source="project.name", read_only=True)
    environment_name = serializers.CharField(source="environment.name", read_only=True)
    interface_name = serializers.CharField(source="interface.name", read_only=True)
    csv_file = serializers.FileField(required=False, allow_null=True)
    target_rps = _EmptyAsNullFloatField(required=False, allow_null=True)

    class Meta:
        model = PerformanceTestTask
        fields = [
            "id",
            "name",
            "project",
            "project_name",
            "environment",
            "environment_name",
            "interface",
            "interface_name",
            "total_users",
            "spawn_rate",
            "run_time",
            "target_rps",
            "status",
            "creator",
            "created_at",
            "executed_at",
            "finished_at",
            "stopped_at",
            "stopped_by",
            "stop_reason",
            "extra_config",
            "csv_file",
        ]
        read_only_fields = [
            "creator",
            "created_at",
            "executed_at",
            "finished_at",
            "stopped_at",
            "stopped_by",
            "stop_reason",
            "status",
        ]

    def validate(self, attrs):
        run_time = attrs.get("run_time")
        if run_time is None and self.instance is not None:
            run_time = self.instance.run_time
        extra = attrs.get("extra_config")
        if extra is None and self.instance is not None:
            extra = self.instance.extra_config
        if run_time is not None:
            try:
                validate_extra_config_for_task(extra, int(run_time))
            except PerformanceConfigError as e:
                raise serializers.ValidationError({"extra_config": str(e)}) from e
        f = attrs.get("csv_file")
        if f:
            try:
                validate_csv_file_size(f)
            except PerformanceConfigError as e:
                raise serializers.ValidationError({"csv_file": str(e)}) from e
        if "target_rps" in attrs:
            tr = attrs["target_rps"]
        elif self.instance is not None:
            tr = self.instance.target_rps
        else:
            tr = None
        if tr is not None and float(tr) <= 0:
            raise serializers.ValidationError({"target_rps": "目标 RPS 须大于 0，或留空表示不限制"})
        return attrs

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user
        return super().create(validated_data)


class PerformanceTestResultSerializer(serializers.ModelSerializer):
    """性能测试结果序列化器"""

    class Meta:
        model = PerformanceTestResult
        fields = [
            "id",
            "task",
            "timestamp",
            "active_users",
            "requests_per_second",
            "response_time_50",
            "response_time_90",
            "failure_rate",
            "p95",
            "p99",
            "max_response_time",
            "error_classification",
        ]


class PerformanceTestTaskViewSet(viewsets.ModelViewSet):
    """性能测试任务 ViewSet - CRUD + 启动压测 + 获取结果/报告"""

    serializer_class = PerformanceTestTaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = (
            _performance_task_queryset_for_user(self.request.user)
            .select_related("project", "environment", "interface", "creator")
            .order_by("-created_at")
        )
        project_id = self.request.query_params.get("project")
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

    def _ensure_project_permission(self, task):
        if not _can_access_project(self.request.user, task.project):
            raise PermissionDenied("无权限操作该项目下的性能测试任务")

    def perform_create(self, serializer):
        project = get_object_or_404(Project, id=serializer.validated_data["project"].id)
        if not _can_access_project(self.request.user, project):
            raise PermissionDenied("无权限在该项目下创建性能测试任务")
        serializer.save()

    def perform_update(self, serializer):
        task = self.get_object()
        self._ensure_project_permission(task)
        serializer.save()

    def perform_destroy(self, instance):
        self._ensure_project_permission(instance)
        instance.delete()

    @action(detail=True, methods=["post"], url_path="start")
    def start_test(self, request, pk=None):
        """
        启动压测：草稿可直接执行；已完成/失败会先清空历史采样结果并重置为草稿再执行。
        执行中不可重复启动。

        调度在事务提交后执行（见 performance_schedule），避免子进程读不到未提交数据。
        默认使用本机独立进程，无需 Celery；生产可设置 PERFORMANCE_TEST_EXECUTOR=celery。
        """
        pk = self.kwargs.get("pk") or pk
        with transaction.atomic():
            task = get_object_or_404(self.get_queryset().select_for_update(), pk=pk)
            self._ensure_project_permission(task)

            st = task.status
            if st == PerformanceTestTask.STATUS_RUNNING:
                raise ValidationError({"detail": "任务正在执行中，请稍后再试"})

            allowed = (
                PerformanceTestTask.STATUS_DRAFT,
                PerformanceTestTask.STATUS_COMPLETED,
                PerformanceTestTask.STATUS_FAILED,
                PerformanceTestTask.STATUS_STOPPED,
            )
            if st not in allowed:
                status_label = dict(PerformanceTestTask.STATUS_CHOICES).get(st, st)
                raise ValidationError({"detail": f"当前状态不可启动: {status_label}"})

            if st in (
                PerformanceTestTask.STATUS_COMPLETED,
                PerformanceTestTask.STATUS_FAILED,
                PerformanceTestTask.STATUS_STOPPED,
            ):
                PerformanceTestResult.objects.filter(task=task).delete()
                task.status = PerformanceTestTask.STATUS_DRAFT
                task.executed_at = None
                task.finished_at = None
                task.stopped_at = None
                task.stopped_by = None
                task.stop_reason = ""
                task.runner_pid = None
                task.celery_task_id = None
                task.save(
                    update_fields=[
                        "status",
                        "executed_at",
                        "finished_at",
                        "stopped_at",
                        "stopped_by",
                        "stop_reason",
                        "runner_pid",
                        "celery_task_id",
                    ]
                )

            task_id = task.id
            transaction.on_commit(lambda tid=task_id: schedule_performance_test(tid))

        task.refresh_from_db()
        serializer = self.get_serializer(task)
        payload = {
            "message": "压测任务已提交，正在执行中",
            "task": serializer.data,
        }
        mode = str(getattr(django_settings, "PERFORMANCE_TEST_EXECUTOR", "process")).strip().lower() or "process"
        if mode == "celery":
            worker_ok, worker_hint = check_celery_workers()
            payload["celery_worker_ok"] = worker_ok
            if worker_hint:
                payload["hint"] = worker_hint
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="stop")
    def stop_test(self, request, pk=None):
        """
        手动停止执行中的压测（单机 Locust 子进程或 Celery Worker 内执行）。

        幂等：已处于 stopped 时返回成功。
        权限：同任务所属项目成员（与 _ensure_project_permission 一致）。
        """
        task = self.get_object()
        self._ensure_project_permission(task)
        reason = request.data.get("reason") or request.data.get("stop_reason") or ""
        result = stop_performance_task(task=task, user=request.user, reason=str(reason))
        task = result["task"]
        serializer = self.get_serializer(task)
        return Response(
            {
                "message": result["message"],
                "already_stopped": result.get("already_stopped", False),
                "task": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="diagnostics")
    def diagnostics(self, request, pk=None):
        """
        排查「执行中无数据 / 长时间不结束」：返回执行器模式、采样时间线、风险等级与建议文案。
        """
        task = self.get_object()
        self._ensure_project_permission(task)
        return Response(build_performance_diagnostics(task))

    @action(detail=True, methods=["get"], url_path="results")
    def get_results(self, request, pk=None):
        """
        获取该任务的所有 PerformanceTestResult，按 timestamp 排序
        """
        task = self.get_object()
        self._ensure_project_permission(task)

        results = PerformanceTestResult.objects.filter(task=task).order_by("timestamp")

        paginator = StandardResultsSetPagination()
        paginated = paginator.paginate_queryset(results, request)
        serializer = PerformanceTestResultSerializer(paginated, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(detail=True, methods=["get"], url_path="report")
    def get_report(self, request, pk=None):
        """
        聚合报告：QPS、分位数、失败率、错误分类（兼容旧结果：新指标为 0 / {}）
        """
        task = self.get_object()
        self._ensure_project_permission(task)

        report = build_performance_report_dict(task)
        payload = serialize_report_response(task, report)
        return Response(payload, status=status.HTTP_200_OK)
