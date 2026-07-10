"""更新AI模型供应商的默认提示词模板，加入输出示例以提高AI输出格式的准确性"""

from django.db import migrations, models

OLD_PROMPT = (
    '请根据以下接口信息和测试规则，生成{casetype_desc}类型的测试用例。\n\n'
    '【接口基本信息】\n'
    '接口名称：{api_name}\n'
    '接口描述：{api_desc}\n'
    '请求方法：{method}\n'
    '请求URL：{url}\n'
    '请求头：{headers}\n'
    '认证方式：{auth_config}\n\n'
    '【请求参数】\n'
    'Query/Path参数：{params}\n\n'
    '【请求体】\n'
    '类型：{body_format}\n'
    '结构：{request_body}\n\n'
    '【响应结构】\n'
    '{response_schema}\n\n'
    '【错误码】\n'
    '{error_codes}\n\n'
    '【测试规则】\n'
    '{rules_text}\n\n'
    '【生成要求】\n'
    '1. 每个用例包含：name, request_method, request_url, request_headers, request_body, expected_status_code, validation_rules\n'
    '2. 覆盖所有规则类别\n'
    '3. validation_rules 是数组, 每项格式为：{"path": "路径", "comparator": "比较器", "expected": 期望值}；'
    '比较器可选：eq, ne, gt, ge, lt, le, contains, startswith, endswith, regex_match, length_eq\n'
    '4. request_headers 必须是 JSON 对象（字典）格式, 如 {"Content-Type": "application/json"}\n'
    '5. 以纯 JSON 数组格式返回，不要包含任何 markdown 标记或其他文本'
)

NEW_PROMPT = (
    '请根据以下接口信息和测试规则，生成{casetype_desc}类型的测试用例。\n\n'
    '【接口基本信息】\n'
    '接口名称：{api_name}\n'
    '接口描述：{api_desc}\n'
    '请求方法：{method}\n'
    '请求URL：{url}\n'
    '请求头：{headers}\n'
    '认证方式：{auth_config}\n\n'
    '【请求参数】\n'
    'Query/Path参数：{params}\n\n'
    '【请求体】\n'
    '类型：{body_format}\n'
    '结构：{request_body}\n\n'
    '【响应结构】\n'
    '{response_schema}\n\n'
    '【错误码】\n'
    '{error_codes}\n\n'
    '【测试规则】\n'
    '{rules_text}\n\n'
    '【生成要求】\n'
    '1. 每个用例包含以下字段：name, request_method, request_url, request_headers, request_body, expected_status_code, validation_rules\n'
    '2. 覆盖所有规则类别\n'
    '3. validation_rules 是数组，每个元素格式必须为：{"path": "字段路径", "comparator": "比较器", "expected": 期望值}\n'
    '   - 注意：字段名必须使用 comparator，不要使用 validator 或其他名称\n'
    '   - 不要添加 checked 等其他多余字段\n'
    '   - 比较器可选：eq, ne, gt, ge, lt, le, contains, startswith, endswith, regex_match, length_eq\n'
    '4. request_headers 必须是 JSON 对象（字典）格式，如 {"Content-Type": "application/json"}\n'
    '5. 以纯 JSON 数组格式返回，不要包含任何 markdown 标记或其他文本\n\n'
    '输出示例：\n'
    '[\n'
    '  {\n'
    '    "name": "测试正常返回",\n'
    '    "request_method": "POST",\n'
    '    "request_url": "/api/example",\n'
    '    "request_headers": {"Content-Type": "application/json"},\n'
    '    "request_body": {"key": "value"},\n'
    '    "expected_status_code": 200,\n'
    '    "validation_rules": [\n'
    '      {"path": "$.code", "comparator": "eq", "expected": "200"},\n'
    '      {"path": "$.isSuccess", "comparator": "eq", "expected": true}\n'
    '    ]\n'
    '  }\n'
    ']'
)


def update_prompt_template(apps, schema_editor):
    AIModelProvider = apps.get_model("test_manager", "AIModelProvider")
    AIModelProvider.objects.filter(prompt_template=OLD_PROMPT).update(prompt_template=NEW_PROMPT)


def revert_prompt_template(apps, schema_editor):
    AIModelProvider = apps.get_model("test_manager", "AIModelProvider")
    AIModelProvider.objects.filter(prompt_template=NEW_PROMPT).update(prompt_template=OLD_PROMPT)


class Migration(migrations.Migration):
    dependencies = [
        ("test_manager", "0064_aigenerationrecord_duration_ms"),
    ]

    operations = [
        migrations.AlterField(
            model_name="aimodelprovider",
            name="prompt_template",
            field=models.TextField(
                db_comment="支持变量：{method} {url} {headers} {body_schema} {rules_text} {case_type} {casetype_desc} {api_name} {api_desc} {params} {body_format} {request_body} {response_schema} {error_codes} {auth_config}",
                default=NEW_PROMPT,
                verbose_name="提示词模板",
            ),
        ),
        migrations.RunPython(update_prompt_template, revert_prompt_template),
    ]
