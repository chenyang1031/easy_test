import uuid
from django.db import models
from django.contrib.auth.models import User
from test_manager.models.project import Project


class Environment(models.Model):
    CATEGORY_DEFAULT = "default"
    CATEGORY_THIRD_PARTY = "third_party"
    CATEGORY_CHOICES = [
        (CATEGORY_DEFAULT, "默认环境"),
        (CATEGORY_THIRD_PARTY, "第三方环境"),
    ]

    name = models.CharField(max_length=100, verbose_name="环境名称", db_comment="环境名称")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='environments', verbose_name="所属项目",
                                db_comment="所属环境")
    base_url = models.URLField(verbose_name="环境URL", db_comment="环境URL")
    variables = models.JSONField(default=dict, blank=True, verbose_name="环境变量", db_comment="环境变量")
    request_headers = models.JSONField(
        default=list,
        blank=True,
        verbose_name="请求头预设",
        db_comment="请求头预设，用于API资产编辑时一键填充",
        help_text="格式为 [{key, value, required, type, ...}] 的列表",
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_DEFAULT,
        verbose_name="环境分类",
        db_comment="环境分类",
    )
    is_global_visible = models.BooleanField(default=False, verbose_name="全局可见", db_comment="全局可见")
    pre_request_script = models.TextField(
        default="",
        blank=True,
        verbose_name="前置脚本",
        db_comment="JS前置脚本，为当前环境下所有接口提供统一请求预处理",
    )
    script_timeout = models.IntegerField(
        default=1000,
        verbose_name="脚本超时(ms)",
        db_comment="脚本执行超时时间，单位毫秒",
        help_text="超时时间≤1000ms",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_comment="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间", db_comment="更新时间")

    def __str__(self):
        return f"{self.project.name} - {self.name}"

    class Meta:
        verbose_name = "环境"
        verbose_name_plural = verbose_name
