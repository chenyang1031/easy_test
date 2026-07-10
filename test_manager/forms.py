from typing import List

from django import forms
from .env_variables_compat import ENV_VAR_DESCRIPTIONS_KEY
from .models import (
    Project, Environment, TestCase, TestSuite, TestRun, EmailConfig, TestSuiteGroup, TestCaseGroup, TestReport,
    MockData, ScheduledTask, TestSuiteCase, ParameterConfig, ApiAsset, ApiGroup, ApiProject,
    TestSceneExecution,
)
import json


def normalize_validation_rules(rules):
    """将 validation_rules 统一为标准格式 [{"op": [path, expected]}, ...]。
    兼容三种格式：标准格式（直通）、AI 格式 {path, comparator, expected}、
    内部编辑器格式 {validator, path, expected}。
    """
    if not rules:
        return []
    result = []
    for rule in rules:
        if not rule or not isinstance(rule, dict):
            continue
        keys = list(rule.keys())
        if not keys:
            continue
        first_val = rule[keys[0]]
        # 已经是标准格式: {"eq": ["$.data.id", 200]}
        if isinstance(first_val, list) and len(first_val) >= 2:
            result.append(rule)
            continue
        # AI 格式 {path, comparator, expected} 或 内部编辑器格式 {validator, path, expected}
        comparator = (rule.get("comparator") or rule.get("validator") or "").strip()
        path = (rule.get("path") or "").strip()
        expected = rule.get("expected", "")
        if comparator and path:
            result.append({comparator: [path, expected]})
    return result


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class EnvironmentForm(forms.ModelForm):
    variables_json = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False,
        help_text='输入json类型的环境变量, 例如. {"key1": "value1"}'
    )
    request_headers_json = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 6}),
        required=False,
        help_text='请求头预设，用于API资产编辑时一键填充。格式为 [{key, value, required, type, ...}] 的JSON数组'
    )
    pre_request_script = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 8, 'class': 'form-control font-monospace'}),
        required=False,
        help_text='JS前置脚本（仅支持 ES5.1），为当前环境下所有接口提供统一请求预处理。禁止网络请求、文件操作，超时≤1000ms。如执行报错，建议使用 AI 工具将脚本转换为 ES5.1',
    )
    script_timeout = forms.IntegerField(
        min_value=100,
        max_value=1000,
        initial=1000,
        help_text='脚本执行超时时间(ms)，最大1000',
    )

    class Meta:
        model = Environment
        fields = ['name', 'project', 'base_url', 'category', 'is_global_visible', 'pre_request_script', 'script_timeout']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            variables_data = self.instance.variables
            if variables_data is None:
                variables_data = {}
            self.fields['variables_json'].initial = json.dumps(variables_data, indent=2)
            headers_data = self.instance.request_headers
            headers_data = self._normalize_environment_request_headers_for_form(headers_data)
            self.fields['request_headers_json'].initial = json.dumps(
                headers_data, ensure_ascii=False, indent=2
            )
            self.fields['pre_request_script'].initial = self.instance.pre_request_script or ""
            self.fields['script_timeout'].initial = getattr(self.instance, 'script_timeout', 1000) or 1000
        else:
            self.fields['variables_json'].initial = json.dumps({})
            self.fields['request_headers_json'].initial = json.dumps([])
            self.fields['pre_request_script'].initial = ""
            self.fields['script_timeout'].initial = 1000

    @staticmethod
    def _normalize_environment_request_headers_for_form(raw):
        """
        请求头预设 DB 中应为 list[{key,value,...}]；兼容历史或异常 dict 形态。
        """
        if isinstance(raw, list):
            return raw
        if isinstance(raw, dict):
            rows = []
            for k, v in raw.items():
                if not str(k).strip():
                    continue
                if isinstance(v, dict) and "value" in v:
                    inner = v.get("value")
                else:
                    inner = v
                if isinstance(inner, (dict, list)):
                    inner = json.dumps(inner, ensure_ascii=False)
                rows.append(
                    {
                        "key": str(k),
                        "value": inner,
                        "required": True,
                        "type": "string",
                    }
                )
            return rows
        return []

    def clean_variables_json(self):
        variables_json = self.cleaned_data.get('variables_json')
        if not variables_json:
            return {}

        try:
            data = json.loads(variables_json)
        except json.JSONDecodeError:
            raise forms.ValidationError('Invalid JSON format')
        if not isinstance(data, dict):
            raise forms.ValidationError('环境变量必须是 JSON 对象')
        meta = data.get(ENV_VAR_DESCRIPTIONS_KEY)
        if meta is not None and not isinstance(meta, dict):
            raise forms.ValidationError('__var_descriptions__ 必须是对象')
        return data

    def clean_request_headers_json(self):
        val = self.cleaned_data.get('request_headers_json')
        if not val or not val.strip():
            return []
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            raise forms.ValidationError('请求头预设必须是有效的JSON数组格式')

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.variables = self.cleaned_data.get('variables_json', {})
        instance.request_headers = self.cleaned_data.get('request_headers_json', [])
        instance.pre_request_script = self.cleaned_data.get('pre_request_script', '') or ''
        instance.script_timeout = min(1000, max(100, int(self.cleaned_data.get('script_timeout', 1000) or 1000)))
        if commit:
            instance.save()
        return instance


class TestCaseForm(forms.ModelForm):
    request_headers_json = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False,
        help_text='Enter headers as JSON, e.g., {"Content-Type": "application/json"}'
    )

    request_body_json = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 6}),
        required=False,
        help_text='Enter request body as JSON'
    )

    request_body_form_data = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 6, 'class': 'form-control'}),
        required=False,
        help_text='Enter form data as key-value pairs, one per line (e.g., key=value)'
    )

    validation_rules_json = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 6}),
        required=False,
        help_text='Enter validation rules as JSON array, e.g., [{"eq": ["$.data.id", 1]}]'
    )

    extract_params_json = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 6}),
        required=False,
        help_text='Enter extract parameters as JSON array, e.g., [{"name": "token", "path": "$.data.token"}]'
    )

    class Meta:
        model = TestCase
        fields = [
            'name', 'project', 'group', 'description', 'request_method',
            'request_url', 'expected_status_code', 'request_body_format',
            'upload_file', 'upload_field_name', 'timeout'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'upload_field_name': forms.TextInput(attrs={
                'placeholder': '例如: file, upload, document',
                'class': 'form-control'
            }),
            'timeout': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': '秒，如 30'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['request_headers_json'].initial = json.dumps(self.instance.request_headers, indent=2)

            # 根据请求体格式初始化相应的字段
            if self.instance.request_body:
                if self.instance.request_body_format == 'json':
                    self.fields['request_body_json'].initial = json.dumps(self.instance.request_body,
                                                                          ensure_ascii=False, indent=2)
                elif self.instance.request_body_format == 'form-data':
                    # 使用 JSON 格式，便于前端正确解析（含已有文件的回显）
                    form_data_list = []
                    has_file_row = False
                    for key, value in self.instance.request_body.items():
                        if isinstance(value, dict) and value.get('type') == 'File':
                            has_file_row = True
                            form_data_list.append({
                                "key": key,
                                "value": {
                                    "type": "File",
                                    "existingFilename": value.get('existingFilename', '')
                                },
                                "type": "File",
                                "description": ""
                            })
                        else:
                            form_data_list.append({
                                "key": key,
                                "value": value,
                                "type": "Text",
                                "description": ""
                            })
                    # 如果有已有文件，添加 File 类型占位符（用于编辑时回显，保存时保留）
                    if self.instance.upload_file and self.instance.upload_field_name and not has_file_row:
                        form_data_list.append({
                            "key": self.instance.upload_field_name,
                            "value": {"type": "File", "existingFilename": self.instance.upload_file.name},
                            "type": "File",
                            "description": ""
                        })
                    self.fields['request_body_form_data'].initial = json.dumps(
                        form_data_list, ensure_ascii=False, indent=2
                    )

            self.fields['validation_rules_json'].initial = json.dumps(self.instance.validation_rules,
                                                                      ensure_ascii=False, indent=2)
            self.fields['extract_params_json'].initial = json.dumps(self.instance.extract_params, ensure_ascii=False,
                                                                    indent=2)
        # 为upload_field_name设置默认值
        # if not self.instance.pk:  # 新建时
        #     self.fields['upload_field_name'].initial = 'file'

        # 添加文件上传的help_text
        # self.fields['upload_file'].help_text = "选择要上传的文件（可选）"
        # self.fields['upload_field_name'].help_text = "文件在multipart/form-data中的字段名"

    def clean_request_headers_json(self):
        headers_json = self.cleaned_data.get('request_headers_json')
        if not headers_json:
            return {}

        try:
            return json.loads(headers_json)
        except json.JSONDecodeError:
            raise forms.ValidationError('Invalid JSON format')

    def clean_request_body_json(self):
        body_json = self.cleaned_data.get('request_body_json')
        if not body_json:
            return None

        try:
            return json.loads(body_json)
        except json.JSONDecodeError:
            raise forms.ValidationError('Invalid JSON format')

    def clean_request_body_form_data(self):
        raw_data = self.cleaned_data.get('request_body_form_data')
        if not raw_data or raw_data == '[]':
            # 触发校验：空数组时报错
            if self.cleaned_data.get('request_body_format') == 'form-data' and \
                    self.cleaned_data.get('request_method') in ['POST', 'PUT', 'PATCH']:
                raise forms.ValidationError('Form data 至少需填写一组 key-value')
            return {}

        try:
            params = json.loads(raw_data)
        except json.JSONDecodeError:
            raise forms.ValidationError('Form data 格式错误，必须是 JSON 数组')

        if not isinstance(params, list) or not params:
            raise forms.ValidationError('Form data 至少需填写一组 key-value')

        result = {}
        for item in params:
            key = str(item.get('key', '')).strip()
            if not key:
                continue
            value = item.get('value', '')
            if isinstance(value, dict) and value.get('type') == 'File':
                result[key] = value  # 文件字段
            else:
                result[key] = str(value)  # 普通文本字段

        return result

    def clean_validation_rules_json(self):
        rules_json = self.cleaned_data.get('validation_rules_json')
        if not rules_json:
            return []

        try:
            return json.loads(rules_json)
        except json.JSONDecodeError:
            raise forms.ValidationError('Invalid JSON format')

    def clean_extract_params_json(self):
        extract_json = self.cleaned_data.get('extract_params_json')
        if not extract_json:
            return []

        try:
            return json.loads(extract_json)
        except json.JSONDecodeError:
            raise forms.ValidationError('Invalid JSON format')

    def clean(self):
        cleaned_data = super().clean()
        request_body_format = cleaned_data.get('request_body_format')

        # 根据选择的请求体格式验证相应的字段
        # 注意：空对象 {} 视为合法（AI生成用例可能无请求体），仅 None/空字符串才报错
        if request_body_format == 'json':
            body_json = cleaned_data.get('request_body_json')
            if body_json is None and cleaned_data.get('request_method') in ['POST', 'PUT', 'PATCH']:
                self.add_error('request_body_json', 'Request body is required for this method when using JSON format')
        elif request_body_format == 'form-data':
            if not cleaned_data.get('request_body_form_data') and cleaned_data.get('request_method') in ['POST', 'PUT',
                                                                                                         'PATCH']:
                self.add_error('request_body_form_data', 'Form data is required for this method')

        return cleaned_data

    def save(self, commit=True):
        # 先保存旧值，避免 super().save(commit=False) 清空后无法恢复
        preserved_upload_file = self.instance.upload_file if self.instance.pk else None
        preserved_upload_field_name = self.instance.upload_field_name if self.instance.pk else ''

        # 若编辑时未上传新文件，临时移除字段，防止 ModelForm 将其置空
        removed_upload_file_field = None
        removed_upload_field_name_field = None
        if preserved_upload_file and not self.files.get('upload_file'):
            removed_upload_file_field = self.fields.pop('upload_file', None)
            removed_upload_field_name_field = self.fields.pop('upload_field_name', None)

        instance = super().save(commit=False)

        # 还原字段定义，保证当前 form 对象后续可用
        if removed_upload_file_field is not None:
            self.fields['upload_file'] = removed_upload_file_field
        if removed_upload_field_name_field is not None:
            self.fields['upload_field_name'] = removed_upload_field_name_field

        instance.request_headers = self.cleaned_data.get('request_headers_json', {})
        request_body_format = self.cleaned_data.get('request_body_format')

        if request_body_format == 'json':
            instance.request_body = self.cleaned_data.get('request_body_json')
        elif request_body_format == 'form-data':
            form_data = self.cleaned_data.get('request_body_form_data', {})
            uploaded_file = self.files.get('upload_file')

            # 从 form-data 里识别 file 类型参数 key（前端隐藏字段可能为空）
            file_param_key = ''
            for key, value in form_data.items():
                if isinstance(value, dict) and value.get('type') == 'File':
                    file_param_key = key
                    break

            if uploaded_file:
                instance.upload_file = uploaded_file
                if file_param_key:
                    instance.upload_field_name = file_param_key
            else:
                # 未上传新文件：强制保留已有文件和字段名
                if preserved_upload_file:
                    instance.upload_file = preserved_upload_file
                    instance.upload_field_name = preserved_upload_field_name

            # 保留 File 参数 key（用于二次编辑回显），同时保留普通文本参数
            persisted_form_data = {}
            for key, value in form_data.items():
                if isinstance(value, dict) and value.get('type') == 'File':
                    if key == (instance.upload_field_name or file_param_key or preserved_upload_field_name):
                        existing_name = ''
                        if instance.upload_file:
                            existing_name = instance.upload_file.name
                        elif preserved_upload_file:
                            existing_name = preserved_upload_file.name
                        persisted_form_data[key] = {
                            'type': 'File',
                            'existingFilename': existing_name
                        }
                else:
                    persisted_form_data[key] = str(value)

            # 若 form-data 中没有 file 行，但数据库中有文件，也补一行占位，保证 key 不丢
            final_file_key = instance.upload_field_name or preserved_upload_field_name
            if final_file_key and instance.upload_file and final_file_key not in persisted_form_data:
                persisted_form_data[final_file_key] = {
                    'type': 'File',
                    'existingFilename': instance.upload_file.name
                }

            instance.request_body = persisted_form_data

        instance.validation_rules = normalize_validation_rules(
            self.cleaned_data.get('validation_rules_json', [])
        )
        instance.extract_params = self.cleaned_data.get('extract_params_json', [])

        # 最终兜底，防止任何分支误清空
        if preserved_upload_file and not instance.upload_file:
            instance.upload_file = preserved_upload_file
            instance.upload_field_name = preserved_upload_field_name

        if commit:
            instance.save()
        return instance


class TestSuiteForm(forms.ModelForm):
    class Meta:
        model = TestSuite
        fields = ['name', 'project', 'group', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class TestRunForm(forms.ModelForm):
    class Meta:
        model = TestRun
        fields = ['name', 'project', 'test_suite', 'environment']


from django import forms


class EmailConfigForm(forms.ModelForm):
    """邮件配置表单"""

    class Meta:
        model = EmailConfig
        fields = [
            'name', 'is_active', 'email_backend',
            'smtp_host', 'smtp_port', 'smtp_username', 'smtp_password',
            'smtp_use_tls', 'smtp_use_ssl',
            'api_key',
            'default_from_email', 'default_from_name',
        ]
        widgets = {
            'smtp_password': forms.PasswordInput(render_value=True),
            'api_key': forms.PasswordInput(render_value=True),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 添加帮助文本
        self.fields['smtp_host'].help_text = "例如: smtp.gmail.com, smtp.qq.com"
        self.fields['smtp_port'].help_text = "常见端口: 25, 465(SSL), 587(TLS)"
        self.fields['api_key'].help_text = "如果使用 SendGrid 或 Mailgun，请输入 API 密钥"
        self.fields['default_from_email'].help_text = "发件人邮箱地址"
        self.fields['default_from_name'].help_text = "发件人显示名称"

        # 设置必填字段
        self.fields['name'].required = True
        self.fields['default_from_email'].required = True
        self.fields['default_from_name'].required = True


class TestEmailForm(forms.Form):
    """测试邮件表单"""
    email = forms.EmailField(label="测试邮箱", help_text="用于接收测试邮件的邮箱地址")


class ParameterConfigForm(forms.ModelForm):
    class Meta:
        model = ParameterConfig
        fields = ["key", "value", "description", "category"]
        widgets = {
            "key": forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"}),
            "value": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "description": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.TextInput(attrs={"class": "form-control"}),
        }


class ApiAssetForm(forms.ModelForm):
    request_headers_json = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4, "class": "form-control font-monospace"}),
    )
    request_params_json = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4, "class": "form-control font-monospace"}),
    )
    request_body_json = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 5, "class": "form-control font-monospace"}),
    )
    request_body_form_data = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 5, "class": "form-control font-monospace"}),
    )
    response_schema_json = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 5, "class": "form-control font-monospace"}),
    )
    error_code_json = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4, "class": "form-control font-monospace"}),
    )
    auth_config_json = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4, "class": "form-control font-monospace"}),
    )

    class Meta:
        model = ApiAsset
        fields = [
            "project",
            "group",
            "name",
            "method",
            "url",
            "interface_desc",
            "request_body_format",
            "status",
            "source",
            "external_id",
            "required",
            "param_type",
            "sort",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control form-control-lg"}),
            "project": forms.Select(attrs={"class": "form-select form-select-lg"}),
            "group": forms.Select(attrs={"class": "form-select"}),
            "method": forms.Select(attrs={"class": "form-select"}),
            "url": forms.TextInput(attrs={"class": "form-control"}),
            "interface_desc": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "request_body_format": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "source": forms.Select(attrs={"class": "form-select"}),
            "external_id": forms.TextInput(attrs={"class": "form-control"}),
            "required": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "param_type": forms.TextInput(attrs={"class": "form-control"}),
            "sort": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["method"].choices = ApiAsset.METHOD_CHOICES
        if self.instance and self.instance.pk:
            self.fields["method"].initial = self.instance.method
        if self.instance and self.instance.pk:
            self.fields["request_headers_json"].initial = json.dumps(
                self._build_kv_rows_for_initial(self.instance.request_headers or {}), ensure_ascii=False, indent=2
            )
            self.fields["request_params_json"].initial = json.dumps(
                self._build_kv_rows_for_initial(self.instance.request_params or {}), ensure_ascii=False, indent=2
            )
            if self.instance.request_body_format == "form-data":
                self.fields["request_body_form_data"].initial = json.dumps(
                    self._build_kv_rows_for_initial(self.instance.request_body or {}), ensure_ascii=False, indent=2
                )
            else:
                self.fields["request_body_json"].initial = json.dumps(
                    self.instance.request_body or {}, ensure_ascii=False, indent=2
                )
            self.fields["response_schema_json"].initial = json.dumps(
                self.instance.response_schema or {}, ensure_ascii=False, indent=2
            )
            self.fields["error_code_json"].initial = json.dumps(
                self.instance.error_code or [], ensure_ascii=False, indent=2
            )
            self.fields["auth_config_json"].initial = json.dumps(
                self.instance.auth_config or {}, ensure_ascii=False, indent=2
            )
        else:
            self.fields["request_headers_json"].initial = "[]"
            self.fields["request_params_json"].initial = "[]"
            self.fields["request_body_json"].initial = "{}"
            self.fields["request_body_form_data"].initial = "[]"
            self.fields["response_schema_json"].initial = "{}"
            self.fields["error_code_json"].initial = "[]"
            self.fields["auth_config_json"].initial = "{}"

    def _normalize_row_item(self, key, value):
        default_required = bool(getattr(self.instance, "required", False))
        default_type = str(getattr(self.instance, "param_type", "string") or "string")
        default_sort = int(getattr(self.instance, "sort", 0) or 0)
        default_status = str(
            getattr(self.instance, "param_status", ApiAsset.PARAM_STATUS_ENABLED) or ApiAsset.PARAM_STATUS_ENABLED
        )
        if default_status not in {ApiAsset.PARAM_STATUS_ENABLED, ApiAsset.PARAM_STATUS_DISABLED}:
            default_status = ApiAsset.PARAM_STATUS_ENABLED

        if isinstance(value, dict) and "value" in value:
            row_value = value.get("value")
            row_required = bool(value.get("required", default_required))
            row_type = str(value.get("type", default_type) or default_type)
            row_sort = int(value.get("sort", default_sort) or 0)
            row_status = str(value.get("status", default_status) or default_status)
            row_desc = str(value.get("description", "") or "")
            row_default = str(value.get("default", "") or "")
            row_validation = str(value.get("validation", "") or "")
        else:
            row_value = value
            row_required = default_required
            row_type = default_type
            row_sort = default_sort
            row_status = default_status
            row_desc = ""
            row_default = ""
            row_validation = ""

        if row_status not in {ApiAsset.PARAM_STATUS_ENABLED, ApiAsset.PARAM_STATUS_DISABLED}:
            row_status = ApiAsset.PARAM_STATUS_ENABLED

        return {
            "key": str(key).strip(),
            "value": "" if row_value is None else row_value,
            "required": row_required,
            "type": row_type,
            "sort": row_sort,
            "status": row_status,
            "description": row_desc,
            "default": row_default,
            "validation": row_validation,
        }

    def _build_kv_rows_for_initial(self, payload):
        rows = []
        if isinstance(payload, dict):
            for key, value in payload.items():
                row = self._normalize_row_item(key, value)
                if row["key"]:
                    rows.append(row)
        rows.sort(key=lambda item: item.get("sort", 0))
        return rows

    def _parse_json(self, field_name, default):
        text = self.cleaned_data.get(field_name)
        if not text:
            return default
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            raise forms.ValidationError("JSON格式不合法")

    def _parse_key_value_json(self, field_name):
        text = self.cleaned_data.get(field_name)
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            raise forms.ValidationError("JSON格式不合法")

        if isinstance(parsed, dict):
            result = {}
            for key, value in parsed.items():
                row = self._normalize_row_item(key, value)
                if not row["key"]:
                    continue
                result[row["key"]] = {
                    "value": row["value"],
                    "required": row["required"],
                    "type": row["type"],
                    "sort": row["sort"],
                    "status": row["status"],
                    "description": row["description"],
                    "default": "",
                    "validation": "",
                }
            return result

        if isinstance(parsed, list):
            result = {}
            for idx, item in enumerate(parsed):
                if not isinstance(item, dict):
                    continue
                key = str(item.get("key", "")).strip()
                if not key:
                    continue
                row = self._normalize_row_item(key, item)
                row["required"] = bool(item.get("required", row["required"]))
                row["type"] = str(item.get("type", row["type"]) or row["type"])
                row["sort"] = int(item.get("sort", idx))
                row["status"] = str(item.get("status", row["status"]) or row["status"])
                if row["status"] not in {ApiAsset.PARAM_STATUS_ENABLED, ApiAsset.PARAM_STATUS_DISABLED}:
                    row["status"] = ApiAsset.PARAM_STATUS_ENABLED
                row["description"] = str(item.get("description", row["description"]) or row["description"])
                row["default"] = str(item.get("default", ""))
                row["validation"] = str(item.get("validation", ""))
                result[key] = {
                    "value": item.get("value", row["value"]),
                    "required": row["required"],
                    "type": row["type"],
                    "sort": row["sort"],
                    "status": row["status"],
                    "description": row["description"],
                    "default": row["default"],
                    "validation": row["validation"],
                }
            return result

        raise forms.ValidationError("JSON格式不合法")

    def clean_request_headers_json(self):
        return self._parse_key_value_json("request_headers_json")

    def clean_request_params_json(self):
        return self._parse_key_value_json("request_params_json")

    def clean_request_body_json(self):
        text = self.cleaned_data.get("request_body_json")
        if not text:
            return {}
        return self._parse_json("request_body_json", {})

    def clean_request_body_form_data(self):
        return self._parse_key_value_json("request_body_form_data")

    def clean_response_schema_json(self):
        return self._parse_json("response_schema_json", {})

    def clean_error_code_json(self):
        parsed = self._parse_json("error_code_json", [])
        if not isinstance(parsed, list):
            raise forms.ValidationError("错误码格式必须为数组")
        normalized = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            code = str(item.get("code", "")).strip()
            message = str(item.get("message", "")).strip()
            description = str(item.get("description", "")).strip()
            if not code and not message:
                continue
            normalized.append(
                {
                    "code": code,
                    "message": message,
                    "description": description,
                }
            )
        return normalized

    def clean_auth_config_json(self):
        return self._parse_json("auth_config_json", {})

    def clean(self):
        cleaned_data = super().clean()
        method = str(cleaned_data.get("method") or "").upper()
        request_params = cleaned_data.get("request_params_json") or {}
        request_body_format = cleaned_data.get("request_body_format") or "json"
        request_body = (
            cleaned_data.get("request_body_form_data", {})
            if request_body_format == "form-data"
            else cleaned_data.get("request_body_json", {})
        )
        if method in {"GET", "DELETE"}:
            cleaned_data["request_body_format"] = "json"
            cleaned_data["request_body_json"] = {}
            cleaned_data["request_body_form_data"] = {}
            return cleaned_data
        has_params = isinstance(request_params, dict) and len(request_params) > 0
        has_body = isinstance(request_body, dict) and len(request_body) > 0
        if has_params and has_body:
            raise forms.ValidationError("请求参数与请求体只能二选一，不能同时填写")
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.request_headers = self.cleaned_data.get("request_headers_json", {})
        instance.request_params = self.cleaned_data.get("request_params_json", {})
        if instance.request_body_format == "form-data":
            instance.request_body = self.cleaned_data.get("request_body_form_data", {})
        else:
            instance.request_body = self.cleaned_data.get("request_body_json", {})
        instance.response_schema = self.cleaned_data.get("response_schema_json", {})
        instance.error_code = self.cleaned_data.get("error_code_json", [])
        instance.auth_config = self.cleaned_data.get("auth_config_json", {})
        if commit:
            instance.save()
        return instance


# 新增测试用例分组表单
class TestCaseGroupForm(forms.ModelForm):
    class Meta:
        model = TestCaseGroup
        fields = ['name', 'project', 'parent']
        widgets = {
            'parent': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        project_id = kwargs.pop('project_id', None)
        super().__init__(*args, **kwargs)

        if project_id:
            self.fields['project'].initial = project_id
            self.fields['project'].widget = forms.HiddenInput()
            # 只显示当前项目的分组
            self.fields['parent'].queryset = TestCaseGroup.objects.filter(project_id=project_id)

        # 如果是编辑模式，排除自己及其子分组，防止循环引用
        if self.instance.pk:
            exclude_ids = [self.instance.pk]
            children = TestCaseGroup.objects.filter(parent=self.instance)
            for child in children:
                exclude_ids.append(child.pk)

                # 递归获取所有子分组
                def get_child_ids(parent_id):
                    child_groups = TestCaseGroup.objects.filter(parent_id=parent_id)
                    for cg in child_groups:
                        exclude_ids.append(cg.pk)
                        get_child_ids(cg.pk)

                get_child_ids(child.pk)

            self.fields['parent'].queryset = self.fields['parent'].queryset.exclude(pk__in=exclude_ids)


# 新增测试套件分组表单
class TestSuiteGroupForm(forms.ModelForm):
    class Meta:
        model = TestSuiteGroup
        fields = ['name', 'project', 'parent']
        widgets = {
            'parent': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        project_id = kwargs.pop('project_id', None)
        super().__init__(*args, **kwargs)

        if project_id:
            self.fields['project'].initial = project_id
            self.fields['project'].widget = forms.HiddenInput()
            # 只显示当前项目的分组
            self.fields['parent'].queryset = TestSuiteGroup.objects.filter(project_id=project_id)

        # 如果是编辑模式，排除自己及其子分组，防止循环引用
        if self.instance.pk:
            exclude_ids = [self.instance.pk]
            children = TestSuiteGroup.objects.filter(parent=self.instance)
            for child in children:
                exclude_ids.append(child.pk)

                # 递归获取所有子分组
                def get_child_ids(parent_id):
                    child_groups = TestSuiteGroup.objects.filter(parent_id=parent_id)
                    for cg in child_groups:
                        exclude_ids.append(cg.pk)
                        get_child_ids(cg.pk)

                get_child_ids(child.pk)

            self.fields['parent'].queryset = self.fields['parent'].queryset.exclude(pk__in=exclude_ids)


# API 分组表单（与 API 资产管理中的分组数据共用）
class ApiGroupForm(forms.ModelForm):
    class Meta:
        model = ApiGroup
        fields = ['name', 'project', 'parent', 'sort_order']
        widgets = {
            'parent': forms.Select(attrs={'class': 'form-select'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }

    def __init__(self, *args, **kwargs):
        api_project_id = kwargs.pop('api_project_id', None)
        super().__init__(*args, **kwargs)

        if api_project_id:
            self.fields['project'].initial = api_project_id
            self.fields['project'].widget = forms.HiddenInput()
            self.fields['project'].queryset = ApiProject.objects.filter(pk=api_project_id)
            self.fields['parent'].queryset = ApiGroup.objects.filter(project_id=api_project_id).order_by("sort_order", "id")

        if self.instance.pk:
            exclude_ids = [self.instance.pk]
            children = ApiGroup.objects.filter(parent=self.instance)
            for child in children:
                exclude_ids.append(child.pk)

                def get_child_ids(parent_id):
                    for cg in ApiGroup.objects.filter(parent_id=parent_id):
                        exclude_ids.append(cg.pk)
                        get_child_ids(cg.pk)

                get_child_ids(child.pk)

            self.fields['parent'].queryset = self.fields['parent'].queryset.exclude(pk__in=exclude_ids)


class TestReportForm(forms.ModelForm):
    class Meta:
        model = TestReport
        fields = ['name', 'description', 'report_format', 'is_public', 'scene_execution']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'scene_execution': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['scene_execution'].required = False
        self.fields['scene_execution'].queryset = TestSceneExecution.objects.select_related('scene').order_by(
            '-id'
        )


class GenerateReportForm(forms.Form):
    name = forms.CharField(max_length=255)
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    report_format = forms.ChoiceField(choices=TestReport.REPORT_FORMAT_CHOICES)
    is_public = forms.BooleanField(required=False, initial=False)


class MockDataForm(forms.ModelForm):
    variables_json = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False,
        help_text='输入List类型的环境变量, 例如., [value1,value2,value3 ...]'
    )

    class Meta:
        model = MockData
        fields = ['aim', 'data', 'description']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['variables_json'].initial = json.dumps(self.instance.variables, ensure_ascii=False, indent=2)

    def clean_variables_json(self):
        variables_json = self.cleaned_data.get('variables_json')
        if not variables_json:
            return {}

        try:
            return json.loads(variables_json)
        except json.JSONDecodeError:
            raise forms.ValidationError('Invalid JSON format')

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.variables = self.cleaned_data.get('variables_json', {})
        if commit:
            instance.save()
        return instance


# 新增定时任务表单
class ScheduledTaskForm(forms.ModelForm):
    notification_emails = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': '输入邮箱地址，多个邮箱用逗号分隔'}),
        required=False,
        help_text='多个邮箱地址用逗号分隔'
    )

    class Meta:
        model = ScheduledTask
        fields = [
            'name', 'description', 'test_suite', 'environment',
            'schedule_type', 'scheduled_time', 'scheduled_date', 'weekday', 'day_of_month', 'cron_expression',
            'send_email_notification', 'notification_emails', 'notify_on_success', 'notify_on_failure',
            'max_retries', 'retry_delay'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'scheduled_time': forms.TimeInput(attrs={'type': 'time'}),
            'scheduled_date': forms.DateInput(attrs={'type': 'date'}),
            'weekday': forms.Select(choices=[
                (1, '星期一'), (2, '星期二'), (3, '星期三'), (4, '星期四'),
                (5, '星期五'), (6, '星期六'), (7, '星期日')
            ]),
            'day_of_month': forms.NumberInput(attrs={'min': 1, 'max': 31}),
            'cron_expression': forms.TextInput(attrs={'placeholder': '0 9 * * 1-5'}),
        }

    def __init__(self, *args, **kwargs):
        test_suite_id = kwargs.pop('test_suite_id', None)
        super().__init__(*args, **kwargs)

        if test_suite_id:
            self.fields['test_suite'].initial = test_suite_id
            # self.fields['test_suite'].widget = forms.HiddenInput()
            # 只显示该测试套件项目的环境
            test_suite = TestSuite.objects.get(pk=test_suite_id)
            self.fields['environment'].queryset = Environment.objects.filter(project=test_suite.project)



        # 添加CSS类
        for field_name, field in self.fields.items():
            if field_name not in ['send_email_notification', 'notify_on_success', 'notify_on_failure']:
                field.widget.attrs.update({'class': 'form-control'})

    def clean_notification_emails(self):
        emails = self.cleaned_data.get('notification_emails', '')
        if not emails:
            return ''

        # 验证邮箱格式
        email_list = [email.strip() for email in emails.split(',') if email.strip()]
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError as DjangoValidationError

        for email in email_list:
            try:
                validate_email(email)
            except DjangoValidationError:
                raise forms.ValidationError(f'无效的邮箱地址: {email}')

        return emails

    def clean(self):
        cleaned_data = super().clean()
        schedule_type = cleaned_data.get('schedule_type')

        if schedule_type == 'once':
            if not cleaned_data.get('scheduled_date') or not cleaned_data.get('scheduled_time'):
                raise forms.ValidationError('单次执行需要设置执行日期和时间')

        elif schedule_type == 'daily':
            if not cleaned_data.get('scheduled_time'):
                raise forms.ValidationError('每日执行需要设置执行时间')

        elif schedule_type == 'weekly':
            if not cleaned_data.get('weekday') or not cleaned_data.get('scheduled_time'):
                raise forms.ValidationError('每周执行需要设置星期几和执行时间')

        elif schedule_type == 'monthly':
            if not cleaned_data.get('day_of_month') or not cleaned_data.get('scheduled_time'):
                raise forms.ValidationError('每月执行需要设置日期和执行时间')

        elif schedule_type == 'cron':
            if not cleaned_data.get('cron_expression'):
                raise forms.ValidationError('Cron表达式不能为空')

        return cleaned_data
