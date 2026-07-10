import uuid
from django.db import models
from django.contrib.auth.models import User
from test_manager.models.project import ApiProject


class AIGenerationRecord(models.Model):
    """AI 生成测试用例的记录（请求/响应存档）"""
    CASE_TYPE_CHOICES = [
        ("api", "接口测试"),
        ("biz_logic", "业务逻辑"),
        ("error_handle", "异常处理"),
        ("param_validate", "参数校验"),
        ("boundary", "边界值"),
        ("performance", "性能测试"),
        ("security", "安全测试"),
    ]
    model_provider = models.ForeignKey("test_manager.AIModelProvider", on_delete=models.SET_NULL, null=True, blank=True)
    request_prompt = models.TextField()
    response_raw = models.TextField(blank=True)
    case_type = models.CharField(max_length=30, choices=CASE_TYPE_CHOICES, default="param_validate")
    interface_info = models.JSONField(default=dict, blank=True)
    case_count = models.IntegerField(default=0)
    duration_ms = models.IntegerField(null=True, blank=True, verbose_name="耗时(毫秒)", db_comment="AI 调用耗时，单位毫秒")
    success = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("generating", "生成中"),
            ("success", "成功"),
            ("failed", "失败"),
        ],
        default="success",
        verbose_name="状态",
        db_comment="生成状态：generating-生成中 success-成功 failed-失败",
    )
    error_message = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_generation_records")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        provider = self.model_provider.name if self.model_provider else "未知"
        return f"{provider} — {self.case_type} ({self.created_at:%Y-%m-%d %H:%M})"

    class Meta:
        verbose_name = "AI生成记录"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]


class DocumentGenRecord(models.Model):
    """文档AI生成记录 — 上传文档→转md→调用大模型→提取API定义"""

    STATUS_CHOICES = [
        ("uploading",   "上传中"),
        ("converting",  "转换中"),
        ("generating",  "AI生成中"),
        ("success",     "生成成功"),
        ("failed",      "生成失败"),
    ]
    IMPORT_STATUS_CHOICES = [
        ("pending",          "待导入"),
        ("partial_imported", "部分导入"),
        ("imported",         "全部导入"),
    ]

    task_name           = models.CharField(max_length=200, verbose_name="任务名称", db_comment="用户自定义任务名")
    project             = models.ForeignKey(ApiProject, on_delete=models.CASCADE, related_name="document_gen_records", verbose_name="所属项目")
    original_file       = models.FileField(upload_to="document_gen/original/%Y/%m/", verbose_name="原始文件", db_comment="上传的原始文件")
    original_filename   = models.CharField(max_length=500, verbose_name="原始文件名", db_comment="原始文件名")
    file_type           = models.CharField(max_length=10, verbose_name="文件类型", db_comment="文件类型: docx/md")
    converted_md_path   = models.CharField(max_length=500, blank=True, verbose_name="转换后md路径", db_comment="转换后md文件相对路径")
    md_content          = models.TextField(blank=True, verbose_name="Markdown内容", db_comment="md文本内容")
    model_provider      = models.ForeignKey("test_manager.AIModelProvider", on_delete=models.SET_NULL, null=True, blank=True)
    prompt_template     = models.ForeignKey("test_manager.PromptTemplate", on_delete=models.SET_NULL, null=True, blank=True)
    model_name          = models.CharField(max_length=100, blank=True, verbose_name="模型名称", db_comment="AI 模型名称（如 gpt-4o, deepseek-chat），创建任务时从模型供应商记录的快照")
    template_name       = models.CharField(max_length=200, blank=True, verbose_name="提示词模板名称", db_comment="提示词模板名称，创建任务时从模板记录的快照")
    prompt_full_text    = models.TextField(blank=True, verbose_name="完整Prompt", db_comment="实际发送给AI的完整prompt快照")
    status              = models.CharField(max_length=20, choices=STATUS_CHOICES, default="uploading", verbose_name="状态")
    extracted_apis      = models.JSONField(default=list, blank=True, verbose_name="提取的API列表", db_comment="AI提取的API列表")
    response_raw        = models.TextField(blank=True, verbose_name="AI原始响应", db_comment="AI原始响应内容")
    error_message       = models.TextField(blank=True, verbose_name="错误信息")
    duration_ms         = models.IntegerField(null=True, blank=True, verbose_name="耗时(毫秒)")
    api_count           = models.IntegerField(default=0, verbose_name="API数量", db_comment="提取到的API数量")
    import_status       = models.CharField(max_length=20, choices=IMPORT_STATUS_CHOICES, default="pending", verbose_name="导入状态")
    imported_asset_ids  = models.JSONField(default=list, blank=True, verbose_name="已导入资产ID列表")
    created_by          = models.ForeignKey(User, on_delete=models.CASCADE, related_name="document_gen_records", verbose_name="创建人")
    created_at          = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at          = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def __str__(self):
        return f"{self.task_name} ({self.original_filename})"

    class Meta:
        verbose_name = "文档AI生成记录"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
