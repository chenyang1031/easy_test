import uuid
from django.db import models
from django.contrib.auth.models import User


class Project(models.Model):
    name = models.CharField(max_length=100, verbose_name="项目名称", db_comment="项目名称")
    description = models.TextField(blank=True, verbose_name="项目描述", db_comment="项目描述")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_comment="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间", db_comment="更新时间")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_projects',
                                   verbose_name="创建人", db_comment="创建人")

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = "项目"
        verbose_name_plural = verbose_name


class ApiProject(models.Model):
    platform_project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="api_project_binding",
        verbose_name="平台项目",
        db_comment="平台项目",
    )
    name = models.CharField(max_length=100, verbose_name="项目名称", db_comment="项目名称")
    description = models.TextField(blank=True, verbose_name="项目描述", db_comment="项目描述")
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_api_projects",
        verbose_name="创建人",
        db_comment="创建人",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_comment="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间", db_comment="更新时间")

    class Meta:
        verbose_name = "API项目"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
