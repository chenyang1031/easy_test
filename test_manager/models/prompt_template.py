from django.db import models
from django.contrib.auth.models import User


class PromptTemplate(models.Model):
    """
    提示词模板模型
    用于存储AI生成测试用例时的提示词模板
    模板中可包含变量占位符：{method}, {url}, {headers}, {body_schema}, {rules}

    分类说明：
    - test_case_gen: 用例生成（默认），用于 AIGenerateModal 生成测试用例
    - api_gen: API 生成，用于文档转 API 资产
    """
    CATEGORY_API_GEN = "api_gen"
    CATEGORY_TEST_CASE_GEN = "test_case_gen"
    CATEGORY_CHOICES = [
        (CATEGORY_API_GEN, "API生成"),
        (CATEGORY_TEST_CASE_GEN, "用例生成"),
    ]

    name = models.CharField(max_length=100, verbose_name="模板名称", db_comment="模板名称")
    description = models.TextField(blank=True, verbose_name="模板描述", db_comment="模板描述")
    template_text = models.TextField(verbose_name="模板内容", db_comment="模板内容，支持变量占位符")
    is_default = models.BooleanField(default=False, verbose_name="是否默认", db_comment="是否默认模板")
    is_enabled = models.BooleanField(default=True, verbose_name="是否启用", db_comment="是否启用")
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_TEST_CASE_GEN,
        verbose_name="分类",
        db_comment="模板分类：api_gen=API生成, test_case_gen=用例生成",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='created_prompt_templates',
        verbose_name="创建人",
        db_comment="创建人（null 表示系统内置模板）",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_comment="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间", db_comment="更新时间")

    def __str__(self):
        return self.name

    def to_rendered_prompt(self, context: dict) -> str:
        """
        将模板中的变量占位符替换为实际值
        context 应包含: method, url, headers, body_schema, rules
        """
        text = self.template_text
        for key, value in context.items():
            placeholder = "{" + key + "}"
            text = text.replace(placeholder, str(value))
        return text

    class Meta:
        verbose_name = "提示词模板"
        verbose_name_plural = verbose_name
        ordering = ['-updated_at']
