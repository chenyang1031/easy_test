import uuid
from django.db import models
from django.contrib.auth.models import User
from test_manager.models.project import ApiProject


class ApiGroup(models.Model):
    project = models.ForeignKey(
        ApiProject,
        on_delete=models.CASCADE,
        related_name="groups",
        verbose_name="所属项目",
        db_comment="所属项目",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="父分组",
        db_comment="父分组",
    )
    name = models.CharField(max_length=100, verbose_name="分组名称", db_comment="分组名称")
    sort_order = models.IntegerField(default=0, verbose_name="排序", db_comment="排序")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_comment="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间", db_comment="更新时间")

    class Meta:
        verbose_name = "API分组"
        verbose_name_plural = verbose_name
        ordering = ["sort_order", "id"]
        unique_together = ("project", "parent", "name")

    def __str__(self):
        return self.name


class ApiAsset(models.Model):
    REQUEST_BODY_FORMAT_CHOICES = [
        ("json", "JSON"),
        ("form-data", "Form Data"),
    ]
    METHOD_CHOICES = [
        ("GET", "GET"),
        ("POST", "POST"),
        ("PUT", "PUT"),
        ("DELETE", "DELETE"),
        ("PATCH", "PATCH"),
    ]
    STATUS_DRAFT = "draft"
    STATUS_ACTIVE = "active"
    STATUS_DEPRECATED = "deprecated"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "草稿"),
        (STATUS_ACTIVE, "可用"),
        (STATUS_DEPRECATED, "已废弃"),
    ]

    SOURCE_MANUAL = "manual"
    SOURCE_POSTMAN = "postman"
    SOURCE_APIFOX = "apifox"
    SOURCE_OPENAPI = "openapi"
    SOURCE_GOREPLAY = "goreplay"
    SOURCE_AI_DOCUMENT = "ai_document"
    SOURCE_CURL = "curl"
    SOURCE_CHOICES = [
        (SOURCE_MANUAL, "手工"),
        (SOURCE_POSTMAN, "Postman"),
        (SOURCE_APIFOX, "Apifox"),
        (SOURCE_OPENAPI, "OpenAPI"),
        (SOURCE_GOREPLAY, "GoReplay"),
        (SOURCE_AI_DOCUMENT, "AI文档"),
        (SOURCE_CURL, "cURL"),
    ]
    PARAM_STATUS_ENABLED = "enabled"
    PARAM_STATUS_DISABLED = "disabled"
    PARAM_STATUS_CHOICES = [
        (PARAM_STATUS_ENABLED, "启用"),
        (PARAM_STATUS_DISABLED, "禁用"),
    ]

    project = models.ForeignKey(
        ApiProject,
        on_delete=models.CASCADE,
        related_name="assets",
        verbose_name="所属项目",
        db_comment="所属项目",
    )
    group = models.ForeignKey(
        ApiGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assets",
        verbose_name="分组",
        db_comment="分组",
    )
    name = models.CharField(max_length=150, verbose_name="接口名称", db_comment="接口名称")
    method = models.CharField(
        max_length=10,
        choices=METHOD_CHOICES,
        verbose_name="请求方法",
        db_comment="请求方法",
    )
    url = models.CharField(max_length=500, verbose_name="请求URL", db_comment="请求URL")
    interface_desc = models.TextField(blank=True, default="", verbose_name="接口描述", db_comment="接口描述")
    request_headers = models.JSONField(default=dict, blank=True, verbose_name="请求头", db_comment="请求头")
    request_params = models.JSONField(default=list, blank=True, verbose_name="请求参数", db_comment="请求参数（结构化数组：[{key,type,value,required,default,desc,validation}]）")
    request_body_format = models.CharField(
        max_length=20,
        choices=REQUEST_BODY_FORMAT_CHOICES,
        default="json",
        verbose_name="请求体格式",
        db_comment="请求体格式",
    )
    request_body = models.JSONField(default=dict, blank=True, null=True, verbose_name="请求体", db_comment="请求体")
    response_schema = models.JSONField(default=dict, blank=True, verbose_name="响应Schema", db_comment="响应Schema")
    error_code = models.JSONField(default=list, blank=True, verbose_name="错误码", db_comment="错误码")
    auth_config = models.JSONField(default=dict, blank=True, verbose_name="鉴权配置", db_comment="鉴权配置")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        verbose_name="状态",
        db_comment="状态",
    )
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default=SOURCE_MANUAL,
        verbose_name="来源",
        db_comment="来源",
    )
    external_id = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="外部标识",
        db_comment="外部标识",
    )
    required = models.BooleanField(default=False, verbose_name="参数必填", db_comment="参数必填")
    param_type = models.CharField(max_length=30, default="string", verbose_name="参数类型", db_comment="参数类型")
    sort = models.IntegerField(default=0, verbose_name="参数排序", db_comment="参数排序")
    param_status = models.CharField(
        max_length=20,
        choices=PARAM_STATUS_CHOICES,
        default=PARAM_STATUS_ENABLED,
        verbose_name="参数启用状态",
        db_comment="参数启用状态",
    )
    is_deleted = models.BooleanField(default=False, verbose_name="是否删除", db_comment="是否删除")
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_api_assets",
        verbose_name="创建人",
        db_comment="创建人",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_comment="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间", db_comment="更新时间")

    class Meta:
        verbose_name = "API资产"
        verbose_name_plural = verbose_name
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["project", "group"], name="api_asset_proj_group_idx"),
            models.Index(fields=["project", "method"], name="api_asset_proj_method_idx"),
            models.Index(fields=["project", "status"], name="api_asset_proj_status_idx"),
            models.Index(fields=["project", "source"], name="api_asset_proj_source_idx"),
        ]

    def __str__(self):
        return f"{self.method} {self.url}"


class ApiHistory(models.Model):
    OP_CREATE = "create"
    OP_UPDATE = "update"
    OP_ROLLBACK = "rollback"
    OP_CHOICES = [
        (OP_CREATE, "创建"),
        (OP_UPDATE, "更新"),
        (OP_ROLLBACK, "回滚"),
    ]

    asset = models.ForeignKey(
        ApiAsset,
        on_delete=models.CASCADE,
        related_name="histories",
        verbose_name="接口资产",
        db_comment="接口资产",
    )
    operation = models.CharField(max_length=20, choices=OP_CHOICES, verbose_name="操作", db_comment="操作")
    content = models.JSONField(default=dict, blank=True, verbose_name="内容", db_comment="内容")
    operator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="api_asset_histories",
        verbose_name="操作人",
        db_comment="操作人",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_comment="创建时间")

    class Meta:
        verbose_name = "API历史"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.asset_id}-{self.operation}"


class ApiAssetChangeRecord(models.Model):
    """API 资产变更记录，用于场景节点同步提示。"""
    CHANGE_URL_METHOD = "url_method"
    CHANGE_REQUEST_PARAMS = "request_params"
    CHANGE_REQUEST_BODY = "request_body"
    CHANGE_RESPONSE_SCHEMA = "response_schema"
    CHANGE_ERROR_CODE = "error_code"
    CHANGE_TYPE_CHOICES = [
        (CHANGE_URL_METHOD, "URL/Method"),
        (CHANGE_REQUEST_PARAMS, "请求参数"),
        (CHANGE_REQUEST_BODY, "请求体"),
        (CHANGE_RESPONSE_SCHEMA, "响应结构"),
        (CHANGE_ERROR_CODE, "响应码"),
    ]

    asset = models.ForeignKey(
        ApiAsset,
        on_delete=models.CASCADE,
        related_name="change_records",
        verbose_name="接口资产",
        db_comment="接口资产",
    )
    change_type = models.CharField(
        max_length=30,
        choices=CHANGE_TYPE_CHOICES,
        verbose_name="变更类型",
        db_comment="变更类型",
    )
    before_snapshot = models.JSONField(default=dict, blank=True, verbose_name="变更前快照", db_comment="变更前快照")
    after_snapshot = models.JSONField(default=dict, blank=True, verbose_name="变更后快照", db_comment="变更后快照")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="api_asset_changes",
        verbose_name="操作人",
        db_comment="操作人",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_comment="创建时间")

    class Meta:
        db_table = "api_asset_change_record"
        verbose_name = "API资产变更记录"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["asset", "created_at"], name="api_asset_chg_asset_time_idx"),
        ]

    def __str__(self):
        return f"{self.asset_id}-{self.change_type}"


class ApiPreset(models.Model):
    PRESET_TYPE_HEADERS = "request_headers"
    PRESET_TYPE_PARAMS = "request_params"
    PRESET_TYPE_FORM_DATA = "form_data"
    PRESET_TYPE_CHOICES = [
        (PRESET_TYPE_HEADERS, "请求头"),
        (PRESET_TYPE_PARAMS, "请求参数"),
        (PRESET_TYPE_FORM_DATA, "Form Data"),
    ]

    project = models.ForeignKey(
        ApiProject,
        on_delete=models.CASCADE,
        related_name="presets",
        verbose_name="所属项目",
        db_comment="所属项目",
    )
    name = models.CharField(max_length=100, verbose_name="预设名称", db_comment="预设名称")
    preset_type = models.CharField(
        max_length=30,
        choices=PRESET_TYPE_CHOICES,
        verbose_name="预设类型",
        db_comment="预设类型",
    )
    data = models.JSONField(default=list, blank=True, verbose_name="预设数据", db_comment="预设数据")
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_api_presets",
        verbose_name="创建人",
        db_comment="创建人",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_comment="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间", db_comment="更新时间")

    class Meta:
        verbose_name = "API预设"
        verbose_name_plural = verbose_name
        ordering = ["-updated_at"]
        unique_together = ("project", "preset_type", "name", "created_by")

    def __str__(self):
        return f"{self.name}({self.preset_type})"


class ApiAssetDraft(models.Model):
    project = models.ForeignKey(
        ApiProject,
        on_delete=models.CASCADE,
        related_name="asset_drafts",
        verbose_name="所属项目",
        db_comment="所属项目",
    )
    asset = models.ForeignKey(
        ApiAsset,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="drafts",
        verbose_name="接口资产",
        db_comment="接口资产",
    )
    draft_key = models.CharField(
        max_length=120,
        blank=True,
        default="",
        verbose_name="草稿键",
        db_comment="草稿键",
    )
    draft_data = models.JSONField(default=dict, blank=True, verbose_name="草稿数据", db_comment="草稿数据")
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="api_asset_drafts",
        verbose_name="创建人",
        db_comment="创建人",
    )
    expires_at = models.DateTimeField(verbose_name="过期时间", db_comment="过期时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_comment="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间", db_comment="更新时间")

    class Meta:
        verbose_name = "API资产草稿"
        verbose_name_plural = verbose_name
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["created_by", "expires_at"], name="api_asset_draft_user_exp_idx"),
            models.Index(fields=["project", "asset"], name="api_asset_draft_proj_asset_idx"),
        ]

    def __str__(self):
        target = self.asset_id if self.asset_id else self.draft_key
        return f"Draft-{target}"
