import uuid
from django.db import models
from django.contrib.auth.models import User
from test_manager.models.project import ApiProject
from test_manager.models.api_asset import ApiAsset, ApiGroup
from test_manager.models.environment import Environment
from django.core.files.storage import default_storage


class TestScene(models.Model):
    """测试场景主表。"""

    project = models.ForeignKey(
        ApiProject,
        on_delete=models.CASCADE,
        related_name="test_scenes",
        verbose_name="所属API项目",
        db_comment="所属API项目",
    )
    group = models.ForeignKey(
        ApiGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="test_scenes",
        verbose_name="场景分组（复用API分组）",
        db_comment="场景分组（复用API分组）",
    )
    name = models.CharField(max_length=150, verbose_name="场景名称", db_comment="场景名称")
    description = models.TextField(blank=True, default="", verbose_name="场景描述", db_comment="场景描述")
    variables = models.JSONField(default=dict, blank=True, verbose_name="场景变量池", db_comment="场景变量池")
    runtime_config = models.JSONField(default=dict, blank=True, verbose_name="运行配置", db_comment="运行配置")
    is_active = models.BooleanField(default=True, verbose_name="是否启用", db_comment="是否启用")
    is_deleted = models.BooleanField(default=False, verbose_name="是否删除", db_comment="是否删除")
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_test_scenes",
        verbose_name="创建人",
        db_comment="创建人",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_comment="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间", db_comment="更新时间")

    class Meta:
        db_table = "test_scene"
        verbose_name = "测试场景"
        verbose_name_plural = verbose_name
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["project", "is_active"], name="test_scene_proj_active_idx"),
            models.Index(fields=["project", "updated_at"], name="test_scene_proj_update_idx"),
        ]

    def __str__(self):
        return self.name


class TestSceneNode(models.Model):
    """测试场景节点表。"""

    ON_FAILED_STOP = "stop"
    ON_FAILED_CONTINUE = "continue"
    ON_FAILED_CHOICES = [
        (ON_FAILED_STOP, "失败终止"),
        (ON_FAILED_CONTINUE, "失败继续"),
    ]

    scene = models.ForeignKey(
        TestScene,
        on_delete=models.CASCADE,
        related_name="nodes",
        verbose_name="所属场景",
        db_comment="所属场景",
    )
    api_asset = models.ForeignKey(
        ApiAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scene_nodes",
        verbose_name="关联API资产",
        db_comment="关联API资产",
    )
    node_key = models.CharField(max_length=80, verbose_name="节点标识", db_comment="节点标识")
    name = models.CharField(max_length=150, verbose_name="节点名称", db_comment="节点名称")
    description = models.TextField(blank=True, default="", verbose_name="节点描述", db_comment="节点描述")
    request_headers = models.JSONField(default=dict, blank=True, verbose_name="请求头覆盖", db_comment="请求头覆盖")
    request_params = models.JSONField(default=dict, blank=True, verbose_name="请求参数覆盖", db_comment="请求参数覆盖")
    request_body = models.JSONField(default=dict, blank=True, verbose_name="请求体覆盖", db_comment="请求体覆盖")
    param_type = models.CharField(
        max_length=20,
        choices=[("json", "JSON"), ("form-data", "Form Data")],
        default="json",
        verbose_name="参数格式",
        db_comment="参数格式",
    )
    body_type = models.CharField(
        max_length=20,
        choices=[("json", "JSON"), ("form-data", "Form Data")],
        default="json",
        verbose_name="请求体格式",
        db_comment="请求体格式",
    )
    assert_rules = models.JSONField(default=list, blank=True, verbose_name="断言规则", db_comment="断言规则")
    extract_rules = models.JSONField(default=list, blank=True, verbose_name="提取规则", db_comment="提取规则")
    expected_status_code = models.PositiveIntegerField(default=200, verbose_name="预期状态码", db_comment="预期状态码")
    expected_response_headers = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="预期响应头",
        db_comment="从回放导入的预期响应头，用于断言基线",
    )
    expected_response_body = models.JSONField(
        default=None,
        null=True,
        blank=True,
        verbose_name="预期响应体",
        db_comment="从回放导入的预期响应体，用于断言基线",
    )
    timeout = models.PositiveIntegerField(null=True, blank=True, verbose_name="超时时间(秒)", db_comment="超时时间(秒)")
    on_failed = models.CharField(
        max_length=20,
        choices=ON_FAILED_CHOICES,
        default=ON_FAILED_STOP,
        verbose_name="失败策略",
        db_comment="失败策略",
    )
    sort = models.IntegerField(default=0, verbose_name="排序", db_comment="排序")
    is_enabled = models.BooleanField(default=True, verbose_name="是否启用", db_comment="是否启用")
    is_deleted = models.BooleanField(default=False, verbose_name="是否删除", db_comment="是否删除")
    environment = models.ForeignKey(
        Environment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scene_nodes",
        verbose_name="接口专属环境",
        db_comment="接口专属环境",
    )
    custom_base_url = models.CharField(
        max_length=512,
        blank=True,
        default="",
        verbose_name="接口自定义域名",
        db_comment="接口自定义域名",
    )
    request_url = models.CharField(
        max_length=1024,
        blank=True,
        default="",
        verbose_name="覆盖URL路径",
        db_comment="覆盖 api_asset.url，支持 {{变量}} 模板，留空则使用资产URL",
    )
    api_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="API最后同步时间",
        db_comment="上次从API资产同步基础信息的时间",
    )
    api_sync_snapshot = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="同步时API快照",
        db_comment="用于回滚时恢复",
    )
    pre_request_script = models.TextField(
        default="",
        blank=True,
        verbose_name="节点前置脚本",
        db_comment="节点级前置脚本（覆盖环境和接口资产），支持 ES5.1 JavaScript",
    )
    script_timeout = models.IntegerField(
        default=1000,
        verbose_name="脚本超时(ms)",
        db_comment="前置脚本执行超时（毫秒），0 表示使用默认值 1000ms",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_comment="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间", db_comment="更新时间")

    class Meta:
        db_table = "test_scene_node"
        verbose_name = "测试场景节点"
        verbose_name_plural = verbose_name
        ordering = ["sort", "id"]
        unique_together = ("scene", "node_key")
        indexes = [
            models.Index(fields=["scene"], name="test_scene_node_scene_idx"),
            models.Index(fields=["scene", "sort"], name="test_scene_node_sort_idx"),
            models.Index(fields=["scene", "is_enabled"], name="test_scene_node_enable_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["scene", "sort"],
                condition=models.Q(is_deleted=False),
                name="uniq_scene_sort_active_node",
            ),
        ]

    def __str__(self):
        return f"{self.scene_id}-{self.node_key}"

    # 兼容字段别名：用于前后端按 scene/api/headers/params/body/assertions 命名读写。
    @property
    def api(self):
        return self.api_asset_id

    @api.setter
    def api(self, value):
        self.api_asset_id = value

    @property
    def enabled(self):
        return self.is_enabled

    @enabled.setter
    def enabled(self, value):
        self.is_enabled = bool(value)

    @property
    def headers(self):
        return self.request_headers

    @headers.setter
    def headers(self, value):
        self.request_headers = value or {}

    @property
    def params(self):
        return self.request_params

    @params.setter
    def params(self, value):
        self.request_params = value or {}

    @property
    def body(self):
        return self.request_body

    @body.setter
    def body(self, value):
        self.request_body = value or {}

    @property
    def assertions(self):
        return self.assert_rules

    @assertions.setter
    def assertions(self, value):
        self.assert_rules = value or []

    @property
    def sort_order(self):
        return self.sort

    @sort_order.setter
    def sort_order(self, value):
        self.sort = int(value or 0)


class TestSceneNodeSyncLog(models.Model):
    """场景节点同步日志，用于追溯与回滚。"""
    SYNC_BASIC = "basic"
    SYNC_PARAMS_ADD = "params_add"
    SYNC_ROLLBACK = "rollback"
    SYNC_TYPE_CHOICES = [
        (SYNC_BASIC, "基础信息"),
        (SYNC_PARAMS_ADD, "新增参数"),
        (SYNC_ROLLBACK, "回滚"),
    ]

    node = models.ForeignKey(
        TestSceneNode,
        on_delete=models.CASCADE,
        related_name="sync_logs",
        verbose_name="场景节点",
        db_comment="场景节点",
    )
    sync_type = models.CharField(
        max_length=30,
        choices=SYNC_TYPE_CHOICES,
        verbose_name="同步类型",
        db_comment="同步类型",
    )
    before_snapshot = models.JSONField(default=dict, blank=True, verbose_name="同步前节点快照", db_comment="同步前节点快照")
    after_snapshot = models.JSONField(default=dict, blank=True, verbose_name="同步后节点快照", db_comment="同步后节点快照")
    node_snapshot_before = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="同步前节点完整配置快照",
        db_comment="同步前节点完整配置快照，回滚时优先使用",
    )
    node_snapshot_after = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="同步后节点完整配置快照",
        db_comment="同步后节点完整配置快照",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="node_sync_logs",
        verbose_name="操作人",
        db_comment="操作人",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_comment="创建时间")

    class Meta:
        db_table = "test_scene_node_sync_log"
        verbose_name = "场景节点同步日志"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["node", "created_at"], name="node_sync_log_node_time_i"),
        ]

    def __str__(self):
        return f"NodeSync-{self.node_id}-{self.sync_type}"


class TestSceneExecution(models.Model):
    """测试场景执行记录。"""

    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    # 全部节点均执行完且无硬失败，但存在「失败继续」策略下仍未通过的断言
    STATUS_PARTIAL_SUCCESS = "partial_success"
    STATUS_CHOICES = [
        (STATUS_RUNNING, "执行中"),
        (STATUS_SUCCESS, "成功"),
        (STATUS_FAILED, "失败"),
        (STATUS_PARTIAL_SUCCESS, "部分成功"),
    ]

    RUN_MODE_ALL = "all"
    RUN_MODE_SINGLE = "single"
    RUN_MODE_CHOICES = [
        (RUN_MODE_ALL, "全流程"),
        (RUN_MODE_SINGLE, "单步"),
    ]

    scene = models.ForeignKey(
        TestScene,
        on_delete=models.CASCADE,
        related_name="executions",
        verbose_name="场景",
        db_comment="场景",
    )
    target_node = models.ForeignKey(
        TestSceneNode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="executions",
        verbose_name="目标节点",
        db_comment="目标节点",
    )
    run_mode = models.CharField(
        max_length=20,
        choices=RUN_MODE_CHOICES,
        default=RUN_MODE_ALL,
        verbose_name="执行模式",
        db_comment="执行模式",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_RUNNING,
        verbose_name="执行状态",
        db_comment="执行状态",
    )
    total_nodes = models.PositiveIntegerField(default=0, verbose_name="总节点数", db_comment="总节点数")
    passed_nodes = models.PositiveIntegerField(default=0, verbose_name="成功节点数", db_comment="成功节点数")
    failed_nodes = models.PositiveIntegerField(default=0, verbose_name="失败节点数", db_comment="失败节点数")
    skipped_nodes = models.PositiveIntegerField(default=0, verbose_name="跳过节点数", db_comment="跳过节点数")
    duration_ms = models.PositiveIntegerField(default=0, verbose_name="执行耗时毫秒", db_comment="执行耗时毫秒")
    summary = models.JSONField(default=dict, blank=True, verbose_name="执行汇总", db_comment="执行汇总")
    node_results = models.JSONField(default=list, blank=True, verbose_name="节点执行结果", db_comment="节点执行结果")
    error_message = models.TextField(blank=True, default="", verbose_name="错误信息", db_comment="错误信息")
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="开始时间", db_comment="开始时间")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="结束时间", db_comment="结束时间")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="test_scene_executions",
        verbose_name="执行人",
        db_comment="执行人",
    )
    environment = models.ForeignKey(
        Environment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scene_executions",
        verbose_name="运行环境",
        db_comment="运行环境",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_comment="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间", db_comment="更新时间")

    class Meta:
        db_table = "test_scene_execution"
        verbose_name = "场景执行记录"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["scene", "created_at"], name="test_scene_exec_scene_idx"),
            models.Index(fields=["status", "created_at"], name="test_scene_exec_status_idx"),
            models.Index(fields=["-created_at"], name="test_scene_exec_created_idx"),
        ]

    def __str__(self):
        return f"SceneExec-{self.scene_id}-{self.id}"


class SceneDownloadedFile(models.Model):
    """场景执行中下载的文件（文件下载 API 的响应落盘记录）。"""

    execution = models.ForeignKey(
        TestSceneExecution,
        on_delete=models.CASCADE,
        related_name="downloaded_files",
        verbose_name="所属执行",
        db_comment="所属执行记录",
    )
    node = models.ForeignKey(
        TestSceneNode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="downloaded_files",
        verbose_name="所属节点",
        db_comment="所属场景节点",
    )
    scene = models.ForeignKey(
        TestScene,
        on_delete=models.CASCADE,
        related_name="downloaded_files",
        verbose_name="所属场景",
        db_comment="所属场景",
    )
    project = models.ForeignKey(
        ApiProject,
        on_delete=models.CASCADE,
        related_name="downloaded_files",
        verbose_name="所属项目",
        db_comment="所属API项目",
    )
    filename = models.CharField(max_length=512, verbose_name="文件名", db_comment="原始文件名")
    file_path = models.CharField(max_length=1024, verbose_name="存储路径", db_comment="文件在存储中的相对路径")
    file_size = models.BigIntegerField(verbose_name="文件大小", db_comment="文件大小（字节）")
    md5 = models.CharField(max_length=32, verbose_name="文件MD5", db_comment="文件MD5校验值")
    content_type = models.CharField(max_length=256, blank=True, default="", verbose_name="Content-Type", db_comment="响应Content-Type")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="downloaded_files",
        verbose_name="创建人",
        db_comment="执行人",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_comment="创建时间")

    class Meta:
        db_table = "scene_downloaded_file"
        verbose_name = "下载文件"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["execution", "created_at"], name="dl_file_exec_time_idx"),
            models.Index(fields=["scene", "created_at"], name="dl_file_scene_time_idx"),
            models.Index(fields=["project", "created_at"], name="dl_file_project_time_idx"),
        ]

    def __str__(self):
        return self.filename

    def delete(self, using=None, keep_parents=False):
        """删除 DB 记录同时删除磁盘文件。"""
        if self.file_path and default_storage.exists(self.file_path):
            default_storage.delete(self.file_path)
        super().delete(using=using, keep_parents=keep_parents)
