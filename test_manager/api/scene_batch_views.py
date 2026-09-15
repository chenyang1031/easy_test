"""
场景批量执行 API - 批次 CRUD、触发、停止，以及批次+单次执行的统一混合列表
"""
from django.db import transaction
from django.db.models import Prefetch, Q
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from test_manager.models import (
    SceneBatchExecution,
    TestScene,
    TestSceneExecution,
    Environment,
)
from test_manager.utils.scene_batch_schedule import start_scene_batch
from .pagination import StandardResultsSetPagination
from .scene_views import _can_access_project, _project_queryset_for_user
from .serializers import TestSceneExecutionListSerializer


# --- 序列化器 ---

class SceneBatchChildSerializer(serializers.ModelSerializer):
    """批次内子执行记录（行内展开用的轻量字段 + 错误信息）"""

    scene_name = serializers.CharField(source="scene.name", read_only=True)

    class Meta:
        model = TestSceneExecution
        fields = [
            "id", "scene", "scene_name", "status",
            "total_nodes", "passed_nodes", "failed_nodes",
            "duration_ms", "started_at", "finished_at", "error_message",
        ]


class SceneBatchExecutionListSerializer(serializers.ModelSerializer):
    """批次列表序列化器（不含子记录）"""

    project_name = serializers.CharField(source="project.platform_project.name", read_only=True, default=None)
    environment_name = serializers.CharField(source="environment.name", read_only=True, default=None)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True, default=None)
    success_rate = serializers.SerializerMethodField()

    class Meta:
        model = SceneBatchExecution
        fields = [
            "id", "name", "project", "project_name", "environment", "environment_name",
            "execute_mode", "total_scenes", "completed_scenes",
            "success_scenes", "failed_scenes", "partial_scenes",
            "status", "error_message", "started_at", "finished_at",
            "created_by_name", "success_rate", "created_at",
        ]

    def get_success_rate(self, obj):
        total = obj.success_scenes + obj.failed_scenes + obj.partial_scenes
        if not total:
            return None
        return round(obj.success_scenes / total * 100, 1)


class SceneBatchExecutionDetailSerializer(SceneBatchExecutionListSerializer):
    """批次详情：嵌套子执行记录"""

    executions = SceneBatchChildSerializer(many=True, read_only=True)

    class Meta(SceneBatchExecutionListSerializer.Meta):
        fields = SceneBatchExecutionListSerializer.Meta.fields + ["executions"]


# --- ViewSet ---

class SceneBatchExecutionViewSet(viewsets.ModelViewSet):
    """
    场景批量执行批次：
    - POST 创建即触发批量执行（后台线程串行/并发跑所有场景）
    - GET 列表/详情；详情含每个场景的子执行记录
    - POST {id}/stop 停止；DELETE 级联删除子执行
    """
    http_method_names = ["get", "post", "delete", "head", "options"]
    queryset = SceneBatchExecution.objects.select_related(
        "project", "project__platform_project", "environment", "created_by",
    ).all()
    serializer_class = SceneBatchExecutionDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action == "list":
            return SceneBatchExecutionListSerializer
        return SceneBatchExecutionDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related(
            # 详情序列化嵌套子执行；defer 掉 MB 级的节点结果 JSON，避免拖慢查询
            Prefetch("executions", queryset=TestSceneExecution.objects.defer("node_results", "summary")),
        ).order_by("-created_at")
        if not self.request.user.is_staff:
            queryset = queryset.filter(project__in=_project_queryset_for_user(self.request.user))
        project = self.request.query_params.get("project")
        if project:
            queryset = queryset.filter(project__platform_project_id=project)
        status_value = self.request.query_params.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset

    def create(self, request):
        """创建批次并立即开始执行：{scene_ids: [..], environment_id: int, mode: serial|parallel}"""
        scene_ids = request.data.get("scene_ids") or []
        if not isinstance(scene_ids, list) or not scene_ids:
            raise ValidationError({"detail": "scene_ids 不能为空"})
        try:
            scene_ids = [int(x) for x in scene_ids]
        except (TypeError, ValueError):
            raise ValidationError({"detail": "scene_ids 必须是场景 ID 列表"})
        # 去重且保序
        seen = set()
        scene_ids = [x for x in scene_ids if not (x in seen or seen.add(x))]

        environment_id = request.data.get("environment_id")
        if not environment_id:
            return Response(
                {"detail": "请先选择运行环境", "error_code": "environment_required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        env_obj = Environment.objects.filter(id=environment_id).first()
        if not env_obj:
            raise ValidationError({"detail": "运行环境不存在"})

        mode = str(request.data.get("mode") or SceneBatchExecution.EXECUTE_MODE_SERIAL).lower()
        if mode not in (SceneBatchExecution.EXECUTE_MODE_SERIAL, SceneBatchExecution.EXECUTE_MODE_PARALLEL):
            raise ValidationError({"detail": "mode 仅支持 serial/parallel"})

        scenes = list(
            TestScene.objects.filter(id__in=scene_ids, is_deleted=False).select_related("project")
        )
        if len(scenes) != len(scene_ids):
            raise ValidationError({"detail": "部分场景不存在或已删除"})
        for scene in scenes:
            if not _can_access_project(request.user, scene.project):
                raise PermissionDenied(f"无权限执行场景【{scene.name}】")
            platform_project_id = getattr(scene.project, "platform_project_id", None)
            if platform_project_id and env_obj.project_id != platform_project_id:
                raise ValidationError({"detail": f"运行环境不属于场景【{scene.name}】绑定的项目"})

        with transaction.atomic():
            batch = SceneBatchExecution.objects.create(
                name=f"批量执行 ({len(scenes)} 个场景)",
                project=scenes[0].project,
                environment=env_obj,
                execute_mode=mode,
                total_scenes=len(scenes),
                status=SceneBatchExecution.STATUS_RUNNING,
                created_by=request.user,
            )
            batch_id = batch.id
            transaction.on_commit(lambda bid=batch_id, sids=scene_ids: start_scene_batch(bid, sids))

        batch.refresh_from_db()
        serializer = SceneBatchExecutionDetailSerializer(batch)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="stop")
    def stop(self, request, pk=None):
        """停止批次：阻止未启动的场景开跑，并对执行中的子执行发出协作式取消信号。"""
        batch = self.get_object()
        if batch.status != SceneBatchExecution.STATUS_RUNNING:
            raise ValidationError({"detail": "只有执行中的批次才能停止"})
        batch.cancel_requested = True
        batch.save(update_fields=["cancel_requested", "updated_at"])
        TestSceneExecution.objects.filter(
            batch=batch, status=TestSceneExecution.STATUS_RUNNING
        ).update(cancel_requested=True)
        return Response({"detail": "已发送停止信号", "batch_id": batch.id})

    def perform_destroy(self, instance):
        """删除批次时级联删除其子执行记录。"""
        instance.executions.all().delete()
        instance.delete()


# --- 统一混合列表（批次 + 单次执行） ---

class SceneExecutionUnifiedView(APIView):
    """
    GET /api/v1/scene-executions-unified/
    按 created_at 倒序合并返回「批量批次」与「单次执行」，
    条目带 type: 'batch' | 'single'，供场景执行列表混合展示。
    过滤参数与原列表一致：project / status / scene_name。
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        paginator = StandardResultsSetPagination()
        try:
            page_size = paginator.get_page_size(request)
        except Exception:
            page_size = 10
        try:
            page_number = max(1, int(request.query_params.get("page", 1)))
        except (TypeError, ValueError):
            page_number = 1
        offset = (page_number - 1) * page_size

        project = request.query_params.get("project")
        status_value = request.query_params.get("status")
        scene_name = (request.query_params.get("scene_name") or "").strip()

        batches = SceneBatchExecution.objects.select_related(
            "project", "project__platform_project", "environment", "created_by",
        ).order_by("-created_at")
        singles = TestSceneExecution.objects.select_related(
            "scene", "scene__project", "scene__project__platform_project",
            "target_node", "created_by", "environment",
        ).defer("node_results", "summary", "error_message").filter(batch__isnull=True).order_by("-created_at")
        if not request.user.is_staff:
            project_filter = _project_queryset_for_user(request.user)
            batches = batches.filter(project__in=project_filter)
            singles = singles.filter(scene__project__in=project_filter)

        if project:
            batches = batches.filter(project__platform_project_id=project)
            singles = singles.filter(scene__project__platform_project_id=project)
        if status_value:
            batches = batches.filter(status=status_value)
            singles = singles.filter(status=status_value)
        if scene_name:
            batches = batches.filter(
                Q(name__icontains=scene_name) | Q(executions__scene__name__icontains=scene_name)
            ).distinct()
            singles = singles.filter(scene__name__icontains=scene_name)

        batch_count = batches.count()
        single_count = singles.count()
        total = batch_count + single_count

        # 合并分页：每侧各取前 offset+page_size 条再归并切片即可覆盖当前页
        window = offset + page_size
        batch_items = [
            {"type": "batch", "key": f"b-{b.id}", "data": SceneBatchExecutionListSerializer(b).data}
            for b in batches[0:window]
        ]
        single_items = [
            {"type": "single", "key": f"e-{s.id}", "data": _single_light_dict(s)}
            for s in singles[0:window]
        ]
        merged = sorted(
            batch_items + single_items,
            key=lambda x: x["data"]["created_at"],
            reverse=True,
        )[offset:offset + page_size]

        return Response({
            "count": total,
            "results": [item["data"] | {"type": item["type"], "key": item["key"]} for item in merged],
        })


def _single_light_dict(execution):
    """单次执行条目（与 TestSceneExecutionListSerializer 字段一致，type/key 由调用方附加）。"""
    return dict(TestSceneExecutionListSerializer(execution).data)
