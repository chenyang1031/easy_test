import uuid
from django.db import models
from django.contrib.auth.models import User
from test_manager.models.project import Project
from test_manager.models.test_case import TestCaseGroup, TestCase


class AICaseDraftGroup(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PARTIAL = "partial_imported"
    STATUS_IMPORTED = "imported"
    STATUS_CHOICES = [
        (STATUS_PENDING, "待导入"),
        (STATUS_PARTIAL, "部分导入"),
        (STATUS_IMPORTED, "全部导入"),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="ai_case_draft_groups",
        verbose_name="所属项目",
        db_comment="所属项目",
    )
    group = models.ForeignKey(
        TestCaseGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_case_draft_groups",
        verbose_name="用例分组",
        db_comment="用例分组",
    )
    interface_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="接口ID",
        db_comment="接口ID",
    )
    case_type = models.CharField(max_length=50, verbose_name="用例类型", db_comment="用例类型")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name="导入状态",
        db_comment="导入状态",
    )
    base_info = models.JSONField(default=dict, blank=True, verbose_name="基础信息", db_comment="基础信息")
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_ai_case_draft_groups",
        verbose_name="创建人",
        db_comment="创建人",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_comment="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间", db_comment="更新时间")

    class Meta:
        verbose_name = "AI用例草稿组"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"AI草稿组-{self.id}"


class AICaseDraft(models.Model):
    IMPORT_PENDING = "pending"
    IMPORT_IMPORTED = "imported"
    IMPORT_FAILED = "failed"
    IMPORT_STATUS_CHOICES = [
        (IMPORT_PENDING, "待导入"),
        (IMPORT_IMPORTED, "导入成功"),
        (IMPORT_FAILED, "导入失败"),
    ]

    draft_group = models.ForeignKey(
        AICaseDraftGroup,
        on_delete=models.CASCADE,
        related_name="drafts",
        verbose_name="草稿组",
        db_comment="草稿组",
    )
    case_data = models.JSONField(default=dict, blank=True, verbose_name="用例数据", db_comment="用例数据")
    is_valid = models.BooleanField(default=True, verbose_name="是否校验通过", db_comment="是否校验通过")
    validation_errors = models.JSONField(
        default=dict, blank=True, verbose_name="校验错误", db_comment="校验错误"
    )
    import_status = models.CharField(
        max_length=20,
        choices=IMPORT_STATUS_CHOICES,
        default=IMPORT_PENDING,
        verbose_name="导入状态",
        db_comment="导入状态",
    )
    imported_case = models.ForeignKey(
        TestCase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_imported_drafts",
        verbose_name="导入后用例",
        db_comment="导入后用例",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_comment="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间", db_comment="更新时间")

    class Meta:
        verbose_name = "AI用例草稿"
        verbose_name_plural = verbose_name
        ordering = ["id"]

    def __str__(self):
        return f"AI草稿-{self.id}"
