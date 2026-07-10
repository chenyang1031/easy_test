"""AI 测试用例生成规则模型。"""
from django.db import models
from django.contrib.auth.models import User


class TestCaseGenerationRule(models.Model):
    """AI 测试用例生成规则，支持分类管理，供 AI 生成测试用例时注入提示词。"""

    CATEGORY_CHOICES = [
        ("param_validate", "参数校验"),
        ("biz_logic", "业务逻辑"),
        ("error_handle", "异常处理"),
        ("boundary", "边界值"),
        ("security", "安全"),
        ("performance", "性能"),
        ("other", "其他"),
    ]
    PRIORITY_CHOICES = [
        ("high", "高"),
        ("medium", "中"),
        ("low", "低"),
    ]

    name = models.CharField(max_length=100, verbose_name="规则名称", db_comment="规则名称")
    description = models.TextField(blank=True, default="", verbose_name="规则描述", db_comment="规则描述")
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="other",
        verbose_name="规则分类",
        db_comment="规则分类",
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="medium",
        verbose_name="优先级",
        db_comment="优先级",
    )
    # 规则内容：一行一条规则，前端按换行分割展示/编辑
    rule_content = models.TextField(verbose_name="规则内容（每行一条）", db_comment="规则内容，每行一条规则")
    is_enabled = models.BooleanField(default=True, verbose_name="是否启用", db_comment="是否启用")
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_test_case_rules",
        verbose_name="创建人",
        db_comment="创建人",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_comment="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间", db_comment="更新时间")

    class Meta:
        verbose_name = "AI用例生成规则"
        verbose_name_plural = verbose_name
        ordering = ["category", "-priority", "-created_at"]
        indexes = [
            models.Index(fields=["category"], name="tc_rule_category_idx"),
            models.Index(fields=["is_enabled"], name="tc_rule_enabled_idx"),
        ]

    def __str__(self):
        return self.name

    @property
    def rule_lines(self):
        """按换行分割的规则列表（供前端展示）。"""
        if not self.rule_content:
            return []
        return [line.strip() for line in self.rule_content.splitlines() if line.strip()]

    def to_prompt_text(self):
        """将本规则渲染为提示词文本，供 AI 调用时使用。"""
        lines = self.rule_lines
        if not lines:
            return ""
        header = f"【{self.get_category_display()}】({self.get_priority_display()})"
        body = "\n".join(f"  - {line}" for line in lines)
        return f"{header}\n{body}"


class AICaseDraftRuleUsage(models.Model):
    """记录每次 AI 生成时使用了哪些规则，便于追溯和优化。"""

    draft_group = models.ForeignKey(
        "AICaseDraftGroup",
        on_delete=models.CASCADE,
        related_name="rule_usages",
        verbose_name="草稿组",
        db_comment="草稿组",
    )
    rule = models.ForeignKey(
        TestCaseGenerationRule,
        on_delete=models.CASCADE,
        related_name="usages",
        verbose_name="使用的规则",
        db_comment="使用的规则",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_comment="创建时间")

    class Meta:
        verbose_name = "AI草稿规则使用记录"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        unique_together = [("draft_group", "rule")]

    def __str__(self):
        return f"{self.draft_group_id}→{self.rule.name}"
