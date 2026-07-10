import uuid
from django.db import models
from django.contrib.auth.models import User


class ParameterConfig(models.Model):
    key = models.CharField(max_length=100, unique=True, verbose_name="参数键", db_comment="参数键")
    value = models.TextField(blank=True, default="", verbose_name="参数值", db_comment="参数值")
    description = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="参数说明",
        db_comment="参数说明",
    )
    category = models.CharField(
        max_length=50,
        blank=True,
        default="general",
        verbose_name="参数分类",
        db_comment="参数分类",
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间", db_comment="更新时间")

    class Meta:
        verbose_name = "参数配置"
        verbose_name_plural = verbose_name
        ordering = ["category", "key"]

    def __str__(self):
        return self.key

    @classmethod
    def get_value(cls, key, default=None):
        obj = cls.objects.filter(key=key).first()
        if not obj:
            return default
        return obj.value
