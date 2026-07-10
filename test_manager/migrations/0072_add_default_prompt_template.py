"""
Migration 0072: 添加默认的 API 生成提示词模板

1. 使 created_by 字段可为 null（允许系统内置模板）
2. 插入默认的 API 文档提取提示词（原硬编码在 base.py）
"""
from django.db import migrations, models


DEFAULT_API_GEN_PROMPT = """你是一个专业的 API 接口文档解析专家。请从以下文档内容中提取所有 API 接口定义。

请严格按照以下 JSON 数组格式输出，每个元素包含以下字段：
- name: 接口名称
- method: 请求方法（GET/POST/PUT/DELETE/PATCH）
- url: 请求 URL 路径
- interface_desc: 接口描述
- request_headers: 请求头（JSON 对象）
- request_params: 请求参数（数组，每个元素包含 key/type/required/desc）
- request_body_format: 请求体格式（json/form-data）
- request_body: 请求体结构（JSON 对象）
- response_schema: 响应结构（JSON 对象）
- error_code: 错误码列表（数组）
- auth_config: 鉴权配置（JSON 对象）

注意事项：
1. 如果文档中没有明确说明某个字段，请使用 null 或空值
2. URL 请提取完整路径，如 /api/v1/users
3. method 必须是大写
4. 只输出 JSON 数组，不要包含 markdown 代码块标记或其他文字说明

文档内容：
{document_content}"""


def insert_default_prompt(apps, schema_editor):
    PromptTemplate = apps.get_model("test_manager", "PromptTemplate")
    # 仅当不存在同名的默认 api_gen 模板时才插入
    exists = PromptTemplate.objects.filter(
        category="api_gen",
        is_default=True,
    ).exists()
    if not exists:
        PromptTemplate.objects.create(
            name="API文档提取（默认）",
            description="从 API 文档中自动提取接口定义的默认提示词，支持 .docx 和 .md 文档",
            template_text=DEFAULT_API_GEN_PROMPT,
            is_default=True,
            is_enabled=True,
            category="api_gen",
            created_by=None,
        )


def reverse_default_prompt(apps, schema_editor):
    PromptTemplate = apps.get_model("test_manager", "PromptTemplate")
    PromptTemplate.objects.filter(
        category="api_gen",
        is_default=True,
        name="API文档提取（默认）",
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("test_manager", "0071_document_gen_record_names"),
    ]

    operations = [
        migrations.AlterField(
            model_name="prompttemplate",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.CASCADE,
                related_name="created_prompt_templates",
                to="auth.user",
                verbose_name="创建人",
                db_comment="创建人（null 表示系统内置模板）",
            ),
        ),
        migrations.RunPython(insert_default_prompt, reverse_default_prompt),
    ]
