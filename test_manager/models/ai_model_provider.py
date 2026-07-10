"""AI 大模型配置模型"""
from django.db import models


class AIModelProvider(models.Model):
    """AI 大模型供应商配置"""

    PROVIDER_TYPES = [
        ("openai", "OpenAI 兼容"),
        ("zhipu", "智谱 AI"),
        ("deepseek", "DeepSeek"),
        ("custom", "自定义"),
    ]

    name = models.CharField(max_length=100, verbose_name="供应商名称", db_comment="供应商名称")
    provider_type = models.CharField(
        max_length=20,
        choices=PROVIDER_TYPES,
        default="openai",
        verbose_name="供应商类型",
        db_comment="供应商类型",
    )
    base_url = models.CharField(
        max_length=300,
        verbose_name="API 基础地址",
        db_comment="API 基础地址（含协议和端口）",
    )
    api_path = models.CharField(
        max_length=200,
        default="/chat/completions",
        blank=True,
        verbose_name="API 路径",
        db_comment="API 路径（如 /chat/completions）",
    )
    api_key = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="API Key",
        db_comment="API 密钥（Bearer Token）",
    )
    model_name = models.CharField(
        max_length=100,
        verbose_name="模型名称",
        db_comment="模型标识（如 glm-4-plus, deepseek-chat）",
    )

    # 系统提示词（可选）
    system_prompt = models.TextField(
        blank=True,
        default="你是一个专业的API测试工程师，擅长根据接口定义生成全面的测试用例。",
        verbose_name="系统提示词",
        db_comment="System Prompt，发送给模型的系统角色指令",
    )

    # 用户提示词模板 — 使用 {变量} 占位
    prompt_template = models.TextField(
        default=(
            "请根据以下接口信息和测试规则，生成{casetype_desc}类型的测试用例。\n\n"
            "【接口基本信息】\n"
            "接口名称：{api_name}\n"
            "接口描述：{api_desc}\n"
            "请求方法：{method}\n"
            "请求URL：{url}\n"
            "请求头：{headers}\n"
            "认证方式：{auth_config}\n\n"
            "【请求参数Schema】\n"
            "{param_schema}\n\n"
            "【请求体】\n"
            "类型：{body_format}\n"
            "结构：{request_body}\n\n"
            "【响应结构】\n"
            "{response_schema}\n\n"
            "【错误码】\n"
            "{error_codes}\n\n"
            "【测试规则】\n"
            "{rules_text}\n\n"
            "【生成要求】\n"
            "1. 每个用例包含以下字段：name, request_method, request_url, request_headers, request_body, expected_status_code, validation_rules\n"
            "2. 覆盖所有规则类别\n"
            "3. validation_rules 是数组，每个元素格式必须为：{\"path\": \"字段路径\", \"comparator\": \"比较器\", \"expected\": 期望值}\n"
            "   - 注意：字段名必须使用 comparator，不要使用 validator 或其他名称\n"
            "   - 不要添加 checked 等其他多余字段\n"
            "   - 比较器可选：eq, ne, gt, ge, lt, le, contains, startswith, endswith, regex_match, length_eq\n"
            "4. request_headers 必须是 JSON 对象（字典）格式，如 {\"Content-Type\": \"application/json\"}\n"
            "5. 以纯 JSON 数组格式返回，不要包含任何 markdown 标记或其他文本\n\n"
            "输出示例：\n"
            "[\n"
            "  {\n"
            "    \"name\": \"测试正常返回\",\n"
            "    \"request_method\": \"POST\",\n"
            "    \"request_url\": \"/api/example\",\n"
            "    \"request_headers\": {\"Content-Type\": \"application/json\"},\n"
            "    \"request_body\": {\"key\": \"value\"},\n"
            "    \"expected_status_code\": 200,\n"
            "    \"validation_rules\": [\n"
            "      {\"path\": \"$.code\", \"comparator\": \"eq\", \"expected\": \"200\"},\n"
            "      {\"path\": \"$.isSuccess\", \"comparator\": \"eq\", \"expected\": true}\n"
            "    ]\n"
            "  }\n"
            "]"
        ),
        verbose_name="提示词模板",
        db_comment="支持变量：{method} {url} {headers} {body_schema} {rules_text} {case_type} {casetype_desc} {api_name} {api_desc} {param_schema} {body_format} {request_body} {response_schema} {error_codes} {auth_config}",
    )

    # 响应解析
    response_cases_path = models.CharField(
        max_length=100,
        default="choices.0.message.content",
        verbose_name="响应用例路径",
        db_comment="JSON 路径，用于从响应中提取用例数组（如 choices.0.message.content）",
    )

    # 模型参数
    temperature = models.FloatField(
        default=0.7,
        verbose_name="温度",
        db_comment="采样温度 0-2，越高越随机",
    )
    max_tokens = models.IntegerField(
        default=4096,
        verbose_name="最大 Token",
        db_comment="单次请求最大输出 Token 数",
    )

    # 超时时间
    timeout = models.PositiveIntegerField(
        default=180,
        verbose_name="超时时间(秒)",
        db_comment="AI 服务调用超时时间，单位秒",
    )

    # 状态
    is_enabled = models.BooleanField(default=True, verbose_name="是否启用", db_comment="是否启用")
    is_default = models.BooleanField(default=False, verbose_name="是否默认", db_comment="是否默认供应商")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "AI大模型供应商"
        verbose_name_plural = verbose_name
        ordering = ["-is_enabled", "-is_default", "name"]
        db_table = "ai_model_provider"

    def __str__(self):
        return f"{self.name} ({self.get_provider_type_display()})"

    @property
    def endpoint(self):
        """完整 API 端点"""
        base = self.base_url.rstrip("/")
        path = self.api_path.lstrip("/")
        return f"{base}/{path}"
