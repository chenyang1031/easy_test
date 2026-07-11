"""
序列化器 — 为所有 ViewSet 提供数据序列化与反序列化。
部分简单场景（MockData）的序列化器定义在各自视图中，此处仅集中管理通用序列化器。
"""
import json
from rest_framework import serializers
from django.contrib.auth.models import User
from test_manager.forms import normalize_validation_rules as _normalize_rules
from test_manager.models import (
    Project, Environment, TestCase, TestSuite,
    TestSuiteCase, TestRun, TestResult, TestCaseGroup, TestSuiteGroup, AICaseDraftGroup, AICaseDraft,
    ApiProject, ApiGroup, ApiAsset, ApiHistory, ApiPreset, ApiAssetDraft,
    TestScene, TestSceneNode, TestSceneExecution, TestReport,
    TestCaseGenerationRule, AICaseDraftRuleUsage,
    PromptTemplate,
    AIModelProvider,
    AIGenerationRecord,
    DocumentGenRecord,
    MockData,
    ScheduledTask, TaskExecutionLog,
    SceneDownloadedFile,
    EmailConfig, ParameterConfig,
)


# ========================================================================
#  用户
# ========================================================================

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


# ========================================================================
#  项目
# ========================================================================

class ProjectSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'created_at', 'updated_at', 'created_by_name']


# ========================================================================
#  环境
# ========================================================================

class EnvironmentSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)

    class Meta:
        model = Environment
        fields = [
            'id', 'name', 'project', 'project_name', 'base_url',
            'variables', 'request_headers', 'category', 'is_global_visible',
            'pre_request_script', 'script_timeout',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


# ========================================================================
#  测试用例
# ========================================================================

class TestCaseSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True, allow_null=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = TestCase
        fields = [
            'id', 'name', 'project', 'project_name', 'group', 'group_name',
            'description', 'request_method', 'request_url',
            'request_headers', 'request_body', 'request_body_format',
            'expected_status_code', 'validation_rules', 'extract_params',
            'upload_file', 'upload_field_name', 'timeout',
            'created_at', 'updated_at', 'created_by_name',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_request_body(self, value):
        if value is None:
            return {}
        return value

    def validate_request_headers(self, value):
        if value is None:
            return {}
        return value

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


# ========================================================================
#  测试套件
# ========================================================================

class TestSuiteCaseSerializer(serializers.ModelSerializer):
    test_case_name = serializers.CharField(source='test_case.name', read_only=True)
    request_method = serializers.SerializerMethodField()
    request_url = serializers.SerializerMethodField()
    environment_name = serializers.CharField(source='environment.name', read_only=True, allow_null=True)

    def get_request_method(self, obj):
        return obj.test_case.request_method if obj.test_case else None

    def get_request_url(self, obj):
        return obj.test_case.request_url if obj.test_case else None

    class Meta:
        model = TestSuiteCase
        fields = [
            'id', 'test_suite', 'test_case', 'test_case_name',
            'request_method', 'request_url',
            'environment', 'environment_name', 'order',
        ]


class TestSuiteSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True, allow_null=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    class Meta:
        model = TestSuite
        fields = [
            'id', 'name', 'project', 'project_name', 'group', 'group_name',
            'description',
            'created_at', 'updated_at', 'created_by_name',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


# ========================================================================
#  测试运行 / 结果
# ========================================================================

class TestResultSerializer(serializers.ModelSerializer):
    test_case_name = serializers.CharField(source='test_case.name', read_only=True, default='-')
    request_method = serializers.SerializerMethodField()
    request_url = serializers.SerializerMethodField()
    expected_status_code = serializers.SerializerMethodField()
    environment_name = serializers.CharField(source='environment.name', read_only=True, default='-')

    def get_request_method(self, obj):
        return obj.test_case.request_method if obj.test_case else None

    def get_request_url(self, obj):
        return obj.test_case.request_url if obj.test_case else None

    def get_expected_status_code(self, obj):
        return obj.test_case.expected_status_code if obj.test_case else None

    class Meta:
        model = TestResult
        fields = [
            'id', 'test_run', 'test_case', 'test_case_name',
            'request_method', 'request_url', 'expected_status_code',
            'environment', 'environment_name',
            'status', 'response_time', 'response_status_code',
            'response_headers', 'response_body',
            'request_headers', 'request_body',
            'error_message', 'extracted_params', 'validators', 'created_at',
        ]
        read_only_fields = ['created_at']


class TestRunListSerializer(serializers.ModelSerializer):
    """轻量序列化器，用于列表页（不含嵌套的 test_results）"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    test_suite_name = serializers.CharField(source='test_suite.name', read_only=True, allow_null=True)
    environment_name = serializers.CharField(source='environment.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = TestRun
        fields = [
            'id', 'name', 'project', 'project_name',
            'test_suite', 'test_suite_name', 'environment', 'environment_name',
            'status', 'start_time', 'end_time',
            'created_at', 'created_by_name',
        ]


class TestRunSerializer(serializers.ModelSerializer):
    """完整序列化器，用于详情页（不含 test_results，前端通过独立 results 端点获取）"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    test_suite_name = serializers.CharField(source='test_suite.name', read_only=True, allow_null=True)
    environment_name = serializers.CharField(source='environment.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = TestRun
        fields = [
            'id', 'name', 'project', 'project_name',
            'test_suite', 'test_suite_name', 'environment', 'environment_name',
            'status', 'start_time', 'end_time',
            'created_at', 'created_by_name',
        ]


# ========================================================================
#  分组（测试用例 / 测试套件），含递归树
# ========================================================================

class TestCaseGroupSerializer(serializers.ModelSerializer):
    test_case_count = serializers.SerializerMethodField()
    sub_group_count = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()

    class Meta:
        model = TestCaseGroup
        fields = [
            'id', 'name', 'project', 'parent',
            'test_case_count', 'sub_group_count', 'children',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by']

    def get_test_case_count(self, obj):
        return TestCase.objects.filter(group=obj).count()

    def get_sub_group_count(self, obj):
        return TestCaseGroup.objects.filter(parent=obj).count()

    def get_children(self, obj):
        children_qs = TestCaseGroup.objects.filter(parent=obj).order_by('name')
        return TestCaseGroupSerializer(children_qs, many=True).data


class TestSuiteGroupSerializer(serializers.ModelSerializer):
    test_suite_count = serializers.SerializerMethodField()
    sub_group_count = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()

    class Meta:
        model = TestSuiteGroup
        fields = [
            'id', 'name', 'project', 'parent',
            'test_suite_count', 'sub_group_count', 'children',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by']

    def get_test_suite_count(self, obj):
        return TestSuite.objects.filter(group=obj).count()

    def get_sub_group_count(self, obj):
        return TestSuiteGroup.objects.filter(parent=obj).count()

    def get_children(self, obj):
        children_qs = TestSuiteGroup.objects.filter(parent=obj).order_by('name')
        return TestSuiteGroupSerializer(children_qs, many=True).data


# ========================================================================
#  AI 用例生成 — 草稿
# ========================================================================

class AICaseDraftItemSerializer(serializers.ModelSerializer):
    """单个草稿项 — 含从 case_data JSON 中提取的扁平化字段"""
    case_name = serializers.SerializerMethodField()
    request_method = serializers.SerializerMethodField()
    request_url = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    request_headers = serializers.SerializerMethodField()
    request_body = serializers.SerializerMethodField()
    validation_rules = serializers.SerializerMethodField()
    request_params = serializers.SerializerMethodField()
    can_select = serializers.SerializerMethodField()

    class Meta:
        model = AICaseDraft
        fields = [
            'id', 'draft_group', 'case_data', 'is_valid',
            'validation_errors', 'import_status', 'imported_case',
            'case_name', 'request_method', 'request_url', 'description',
            'request_headers', 'request_body', 'validation_rules', 'request_params',
            'can_select',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def _get_case_data(self, obj):
        return obj.case_data if isinstance(obj.case_data, dict) else {}

    def get_case_name(self, obj):
        return obj.case_data.get('name', '') if isinstance(obj.case_data, dict) else ''

    def get_request_method(self, obj):
        return obj.case_data.get('request_method', '') if isinstance(obj.case_data, dict) else ''

    def get_request_url(self, obj):
        return obj.case_data.get('request_url', '') if isinstance(obj.case_data, dict) else ''

    def get_description(self, obj):
        return obj.case_data.get('description', '') if isinstance(obj.case_data, dict) else ''

    def get_request_headers(self, obj):
        data = obj.case_data if isinstance(obj.case_data, dict) else {}
        headers = data.get('request_headers', {})
        if isinstance(headers, str):
            try:
                return json.loads(headers)
            except (json.JSONDecodeError, TypeError):
                return {}
        return headers

    def get_request_body(self, obj):
        data = obj.case_data if isinstance(obj.case_data, dict) else {}
        body = data.get('request_body', {})
        if isinstance(body, str):
            try:
                return json.loads(body)
            except (json.JSONDecodeError, TypeError):
                return {}
        return body

    def get_validation_rules(self, obj):
        data = obj.case_data if isinstance(obj.case_data, dict) else {}
        rules = data.get('validation_rules', [])
        if isinstance(rules, str):
            try:
                return json.loads(rules)
            except (json.JSONDecodeError, TypeError):
                return []
        return rules

    def get_request_params(self, obj):
        data = obj.case_data if isinstance(obj.case_data, dict) else {}
        params = data.get('request_params', {})
        if isinstance(params, str):
            try:
                return json.loads(params)
            except (json.JSONDecodeError, TypeError):
                return []
        return params

    def get_can_select(self, obj):
        return obj.import_status == AICaseDraft.IMPORT_PENDING or obj.import_status == AICaseDraft.IMPORT_FAILED


class AICaseDraftGroupItemSerializer(serializers.ModelSerializer):
    """草稿组，含嵌套草稿列表及从 base_info JSON 中提取的扁平化字段"""
    drafts = AICaseDraftItemSerializer(many=True, read_only=True)
    rule_ids = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    project_name = serializers.SerializerMethodField()
    draft_count = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = AICaseDraftGroup
        fields = [
            'id', 'project', 'project_name', 'group', 'interface_id', 'case_type', 'status',
            'base_info', 'name', 'draft_count', 'drafts', 'rule_ids',
            'created_by_name', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_created_by_name(self, obj):
        return obj.created_by.username if obj.created_by else None

    def get_rule_ids(self, obj):
        return list(obj.rule_usages.values_list('rule_id', flat=True))

    def get_name(self, obj):
        if isinstance(obj.base_info, dict):
            return obj.base_info.get('api_name', '') or obj.base_info.get('name', '') or f"草稿组 #{obj.id}"
        return f"草稿组 #{obj.id}"

    def get_project_name(self, obj):
        return obj.project.name if obj.project_id else ''

    def get_draft_count(self, obj):
        return obj.drafts.count()


class AICaseDraftRuleUsageSerializer(serializers.ModelSerializer):
    rule_name = serializers.CharField(source='rule.name', read_only=True)

    class Meta:
        model = AICaseDraftRuleUsage
        fields = ['id', 'draft_group', 'rule', 'rule_name', 'created_at']
        read_only_fields = ['created_at']


# ========================================================================
#  测试报告
# ========================================================================

class TestReportListSerializer(serializers.ModelSerializer):
    """轻量序列化器，用于报告列表页（不返回 content 大字段）"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    scene_name = serializers.SerializerMethodField()
    report_type_display = serializers.SerializerMethodField()
    report_format_display = serializers.SerializerMethodField()

    class Meta:
        model = TestReport
        fields = [
            'id', 'name', 'description', 'project', 'project_name',
            'report_type', 'report_type_display', 'report_format', 'report_format_display',
            'scene_execution', 'scene_name',
            'is_public', 'created_by', 'created_by_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_scene_name(self, obj):
        if obj.scene_execution_id and obj.scene_execution:
            return obj.scene_execution.scene.name if obj.scene_execution.scene_id else ''
        return ''

    def get_report_type_display(self, obj):
        mapping = {
            'test_run': '测试运行',
            'test_suite_run': '测试套件',
            'scene_execution': '场景执行',
            'custom': '自定义',
        }
        return mapping.get(obj.report_type, obj.report_type)

    def get_report_format_display(self, obj):
        return {'html': 'HTML', 'pdf': 'PDF', 'json': 'JSON'}.get(obj.report_format, obj.report_format)


class TestReportDetailSerializer(serializers.ModelSerializer):
    """完整序列化器，用于报告详情页（含 content）"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    scene_name = serializers.SerializerMethodField()
    report_type_display = serializers.SerializerMethodField()
    report_format_display = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()

    class Meta:
        model = TestReport
        fields = [
            'id', 'name', 'description', 'project', 'project_name',
            'report_type', 'report_type_display', 'report_format', 'report_format_display',
            'content', 'scene_execution', 'scene_name',
            'test_run', 'test_suite_run', 'test_results',
            'is_public', 'created_by', 'created_by_name',
            'created_at', 'updated_at', 'summary',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_scene_name(self, obj):
        if obj.scene_execution_id and obj.scene_execution:
            return obj.scene_execution.scene.name if obj.scene_execution.scene_id else ''
        return ''

    def get_report_type_display(self, obj):
        mapping = {
            'test_run': '测试运行',
            'test_suite_run': '测试套件',
            'scene_execution': '场景执行',
            'custom': '自定义',
        }
        return mapping.get(obj.report_type, obj.report_type)

    def get_report_format_display(self, obj):
        return {'html': 'HTML', 'pdf': 'PDF', 'json': 'JSON'}.get(obj.report_format, obj.report_format)

    def get_summary(self, obj):
        return obj.get_summary()


class TestReportCreateSerializer(serializers.ModelSerializer):
    """创建/编辑报告用序列化器"""
    class Meta:
        model = TestReport
        fields = [
            'name', 'description', 'project', 'report_type', 'report_format',
            'content', 'test_run', 'test_suite_run', 'scene_execution',
            'test_results', 'is_public',
        ]

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


# ========================================================================
#  AI 用例生成 — 请求 / 输入
# ========================================================================

class AIGenerateMultiTestCasesRequestSerializer(serializers.Serializer):
    """校验 AI 生成测试用例的请求参数"""
    base_info = serializers.DictField()
    case_type = serializers.CharField(max_length=50)
    creator_id = serializers.IntegerField()
    rule_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    prompt_template_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    model_provider_id = serializers.IntegerField(required=False, allow_null=True, default=None)

    def validate(self, attrs):
        # 校验 & 注入规则对象
        rule_ids = attrs.get('rule_ids', [])
        if rule_ids:
            rules = TestCaseGenerationRule.objects.filter(id__in=rule_ids)
            attrs['rule_objs'] = list(rules)
        else:
            attrs['rule_objs'] = []

        # 校验 & 注入提示词模板对象
        tmpl_id = attrs.get('prompt_template_id')
        if tmpl_id:
            try:
                attrs['prompt_template_obj'] = PromptTemplate.objects.get(id=tmpl_id)
            except PromptTemplate.DoesNotExist:
                raise serializers.ValidationError({'prompt_template_id': '提示词模板不存在'})
        else:
            attrs['prompt_template_obj'] = None

        # 校验 & 注入模型供应商对象
        provider_id = attrs.get('model_provider_id')
        if provider_id:
            try:
                attrs['model_provider_obj'] = AIModelProvider.objects.get(id=provider_id)
            except AIModelProvider.DoesNotExist:
                raise serializers.ValidationError({'model_provider_id': '模型供应商不存在'})
        else:
            attrs['model_provider_obj'] = None

        return attrs


class AIImportTestCasesRequestSerializer(serializers.Serializer):
    """校验 AI 导入测试用例的请求参数"""
    draft_group_id = serializers.IntegerField()
    draft_ids = serializers.ListField(child=serializers.IntegerField(), min_length=1)
    target_suite_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    new_suite_name = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    user_id = serializers.IntegerField()


# ========================================================================
#  AI 用例生成规则
# ========================================================================

class TestCaseGenerationRuleSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    rule_lines = serializers.ListField(read_only=True)

    class Meta:
        model = TestCaseGenerationRule
        fields = [
            'id', 'name', 'description', 'category', 'priority',
            'rule_content', 'rule_lines', 'is_enabled',
            'created_by_name', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


# ========================================================================
#  AI 提示词模板
# ========================================================================

class PromptTemplateSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PromptTemplate
        fields = [
            'id', 'name', 'description', 'template_text',
            'is_default', 'is_enabled', 'category',
            'created_by_name', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_created_by_name(self, obj):
        return obj.created_by.username if obj.created_by else None


# ========================================================================
#  文档AI生成记录
# ========================================================================

class DocumentGenRecordSerializer(serializers.ModelSerializer):
    """文档AI生成记录序列化器"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    model_provider_name = serializers.CharField(
        source='model_provider.name', read_only=True, allow_null=True
    )
    prompt_template_name = serializers.CharField(
        source='prompt_template.name', read_only=True, allow_null=True
    )
    created_by_name = serializers.CharField(
        source='created_by.username', read_only=True, allow_null=True
    )

    class Meta:
        model = DocumentGenRecord
        fields = [
            'id', 'task_name', 'project', 'project_name',
            'original_file', 'original_filename', 'file_type',
            'converted_md_path', 'md_content',
            'model_provider', 'model_provider_name',
            'prompt_template', 'prompt_template_name',
            'model_name', 'template_name',
            'prompt_full_text',
            'status', 'extracted_apis', 'response_raw', 'error_message',
            'duration_ms', 'api_count',
            'import_status', 'imported_asset_ids',
            'created_by_name', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'converted_md_path', 'md_content', 'prompt_full_text',
            'status', 'extracted_apis', 'response_raw', 'error_message',
            'duration_ms', 'api_count', 'import_status', 'imported_asset_ids',
            'created_by_name', 'created_at', 'updated_at',
        ]


class DocumentGenRecordUploadSerializer(serializers.Serializer):
    """文档上传请求校验"""
    task_name = serializers.CharField(max_length=200)
    file = serializers.FileField()
    project_id = serializers.IntegerField()
    model_provider_id = serializers.IntegerField(required=False, allow_null=True)
    prompt_template_id = serializers.IntegerField(required=False, allow_null=True)

    # 允许的 MIME 类型（浏览器上传的 content_type 仅供参考，不可完全信赖）
    ALLOWED_MIME_TYPES = {
        'docx': [
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/octet-stream',  # 某些浏览器上传 docx 时使用此类型
        ],
        'md': [
            'text/markdown',
            'text/plain',
            'text/x-markdown',
            'application/octet-stream',
        ],
    }

    def validate_file(self, value):
        ext = value.name.rsplit('.', 1)[-1].lower() if '.' in value.name else ''
        if ext not in ('docx', 'md'):
            raise serializers.ValidationError("仅支持 .docx 和 .md 文件格式")
        if value.size > 50 * 1024 * 1024:
            raise serializers.ValidationError("文件大小不能超过 50MB")
        # MIME 类型基础校验（content_type 由浏览器提供，不能作为唯一安全依据）
        content_type = getattr(value, 'content_type', '') or ''
        allowed = self.ALLOWED_MIME_TYPES.get(ext, [])
        if content_type and allowed and content_type not in allowed:
            raise serializers.ValidationError(
                f"文件类型不匹配：检测到 {content_type}，期望 {', '.join(allowed)}"
            )
        return value


# ========================================================================
#  AI 大模型供应商
# ========================================================================

class AIModelProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIModelProvider
        fields = [
            'id', 'name', 'provider_type', 'base_url', 'api_path', 'api_key',
            'model_name', 'system_prompt', 'prompt_template',
            'response_cases_path', 'temperature', 'max_tokens', 'timeout',
            'is_enabled', 'is_default',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'api_key': {'write_only': True},
        }


# ========================================================================
#  AI 生成记录
# ========================================================================

class AIGenerationRecordSerializer(serializers.ModelSerializer):
    model_provider_name = serializers.CharField(
        source='model_provider.name', read_only=True, allow_null=True
    )
    created_by_name = serializers.CharField(
        source='created_by.username', read_only=True, allow_null=True
    )

    class Meta:
        model = AIGenerationRecord
        fields = [
            'id', 'model_provider', 'model_provider_name',
            'request_prompt', 'response_raw', 'case_type',
            'interface_info', 'case_count', 'duration_ms',
            'success', 'status', 'error_message',
            'created_by_name', 'created_at',
        ]
        read_only_fields = ['created_at']


# ========================================================================
#  API 资产管理 — 项目 / 分组 / 资产 / 历史 / 预设 / 草稿
# ========================================================================

class ApiProjectSerializer(serializers.ModelSerializer):
    platform_project_name = serializers.CharField(
        source='platform_project.name', read_only=True, allow_null=True
    )
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = ApiProject
        fields = ['id', 'platform_project', 'platform_project_name', 'name', 'description',
                  'created_by_name', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class ApiGroupListSerializer(serializers.ModelSerializer):
    """分组列表序列化器，含子分组数量"""
    sub_group_count = serializers.SerializerMethodField()
    asset_count = serializers.SerializerMethodField()

    class Meta:
        model = ApiGroup
        fields = ['id', 'project', 'parent', 'name', 'sort_order',
                  'sub_group_count', 'asset_count', 'created_at', 'updated_at']

    def get_sub_group_count(self, obj):
        return ApiGroup.objects.filter(parent=obj).count()

    def get_asset_count(self, obj):
        return ApiAsset.objects.filter(group=obj, is_deleted=False).count()


class ApiGroupSerializer(serializers.ModelSerializer):
    """分组详情序列化器，递归展开 children"""
    children = serializers.SerializerMethodField()

    class Meta:
        model = ApiGroup
        fields = ['id', 'project', 'parent', 'name', 'sort_order',
                  'children', 'created_at', 'updated_at']

    def get_children(self, obj):
        children_qs = ApiGroup.objects.filter(parent=obj).order_by('sort_order', 'name')
        return ApiGroupSerializer(children_qs, many=True).data


def _dict_params_to_array(params):
    """将 dict 格式的请求参数转为 array 格式 [{key, value, checked}]"""
    if not params:
        return []
    if isinstance(params, list):
        return params
    if isinstance(params, dict):
        return [{'key': k, 'value': v, 'checked': True} for k, v in params.items()]
    return []


class ApiAssetSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True, allow_null=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = ApiAsset
        fields = [
            'id', 'project', 'project_name', 'group', 'group_name',
            'name', 'method', 'url', 'interface_desc',
            'request_headers', 'request_params', 'request_body_format', 'request_body',
            'response_schema', 'error_code', 'auth_config',
            'status', 'source', 'external_id',
            'required', 'param_type', 'sort', 'param_status', 'is_deleted',
            'created_by_name', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def to_internal_value(self, data):
        # 将前端 array 格式的 request_params 转成 dict 存储
        result = super().to_internal_value(data)
        if 'request_params' in data:
            result['request_params'] = _dict_params_to_array(data['request_params'])
        return result


class ApiAssetLiteSerializer(serializers.ModelSerializer):
    """资产精简序列化器（不含请求体明细，用于下拉/弹窗列表）"""
    group_name = serializers.CharField(source='group.name', read_only=True, allow_null=True)

    class Meta:
        model = ApiAsset
        fields = ['id', 'name', 'method', 'url', 'group', 'group_name',
                  'source', 'external_id', 'status', 'is_deleted']


class ApiHistorySerializer(serializers.ModelSerializer):
    operator_name = serializers.CharField(source='operator.username', read_only=True, allow_null=True)

    class Meta:
        model = ApiHistory
        fields = ['id', 'asset', 'operation', 'content', 'operator', 'operator_name', 'created_at']
        read_only_fields = ['created_at']


class ApiPresetSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = ApiPreset
        fields = ['id', 'project', 'name', 'preset_type', 'data',
                  'created_by_name', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class ApiAssetDraftSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = ApiAssetDraft
        fields = ['id', 'project', 'asset', 'draft_key', 'draft_data',
                  'created_by_name', 'expires_at', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


# ========================================================================
#  测试场景 / 节点 / 执行
# ========================================================================

class TestSceneSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    group_name = serializers.SerializerMethodField()
    # 注解字段 — 由 TestSceneViewSet.get_queryset 中的 annotate 提供
    node_count = serializers.SerializerMethodField()
    latest_execution_status = serializers.SerializerMethodField()
    latest_execution_started_at = serializers.SerializerMethodField()
    latest_execution_duration_ms = serializers.SerializerMethodField()
    latest_execution_error_message = serializers.SerializerMethodField()
    # 关联 API 资产变更检测
    api_updated = serializers.SerializerMethodField()
    api_updated_node_ids = serializers.SerializerMethodField()
    api_updated_node_count = serializers.SerializerMethodField()

    class Meta:
        model = TestScene
        fields = [
            'id', 'project', 'project_name', 'name', 'description',
            'variables', 'runtime_config', 'is_active', 'is_deleted',
            'group', 'group_name',
            'created_by_name', 'created_at', 'updated_at',
            'node_count', 'latest_execution_status',
            'latest_execution_started_at', 'latest_execution_duration_ms',
            'latest_execution_error_message',
            'api_updated', 'api_updated_node_ids', 'api_updated_node_count',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_group_name(self, obj):
        if obj.group_id:
            try:
                return obj.group.name
            except Exception:
                return None
        return None

    def get_node_count(self, obj):
        return getattr(obj, 'node_count', 0) or 0

    def get_latest_execution_status(self, obj):
        return getattr(obj, 'latest_execution_status', None)

    def get_latest_execution_started_at(self, obj):
        return getattr(obj, 'latest_execution_started_at', None)

    def get_latest_execution_duration_ms(self, obj):
        return getattr(obj, 'latest_execution_duration_ms', None)

    def get_latest_execution_error_message(self, obj):
        return getattr(obj, 'latest_execution_error_message', None)

    def _get_updated_nodes(self, obj):
        """获取节点中 api_asset.updated_at > api_synced_at 的节点列表。"""
        nodes = self.context.get('_prefetched_nodes', {}).get(obj.id, [])
        if not nodes:
            return []
        return [
            n for n in nodes
            if n.api_asset_id and n.api_synced_at and n.api_asset is not None
            and not n.api_asset.is_deleted
            and n.api_asset.updated_at > n.api_synced_at
        ]

    def get_api_updated(self, obj):
        return len(self._get_updated_nodes(obj)) > 0

    def get_api_updated_node_ids(self, obj):
        return [n.id for n in self._get_updated_nodes(obj)]

    def get_api_updated_node_count(self, obj):
        return len(self._get_updated_nodes(obj))

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class TestSceneNodeSerializer(serializers.ModelSerializer):
    group_name = serializers.SerializerMethodField()
    api_asset_url = serializers.SerializerMethodField()
    api_asset_method = serializers.SerializerMethodField()
    api_asset_request_headers = serializers.SerializerMethodField()
    api_asset_request_params = serializers.SerializerMethodField()
    api_asset_request_body_format = serializers.SerializerMethodField()
    api_asset_response_schema = serializers.SerializerMethodField()
    api_updated = serializers.SerializerMethodField()

    class Meta:
        model = TestSceneNode
        fields = [
            'id', 'scene', 'api_asset', 'node_key', 'name', 'description',
            'method',
            'request_headers', 'request_params', 'request_body',
            'param_type', 'body_type',
            'assert_rules', 'extract_rules',
            'expected_status_code', 'expected_response_headers', 'expected_response_body',
            'timeout', 'on_failed', 'sort', 'is_enabled', 'is_deleted',
            'environment', 'custom_base_url',
            'api_synced_at', 'api_sync_snapshot',
            'pre_request_script', 'script_timeout',
            'request_url',
            'group_name',
            'api_asset_url', 'api_asset_method',
            'api_asset_request_headers', 'api_asset_request_params',
            'api_asset_request_body_format', 'api_asset_response_schema',
            'api_updated',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_group_name(self, obj):
        if obj.api_asset_id and obj.api_asset.group_id:
            return obj.api_asset.group.name
        return None

    def get_api_asset_url(self, obj):
        return obj.api_asset.url if obj.api_asset_id and obj.api_asset else None

    def get_api_asset_method(self, obj):
        return obj.api_asset.method if obj.api_asset_id and obj.api_asset else None

    def get_api_asset_request_headers(self, obj):
        return obj.api_asset.request_headers if obj.api_asset_id and obj.api_asset else None

    def get_api_asset_request_params(self, obj):
        return obj.api_asset.request_params if obj.api_asset_id and obj.api_asset else None

    def get_api_asset_request_body_format(self, obj):
        return obj.api_asset.request_body_format if obj.api_asset_id and obj.api_asset else None

    def get_api_asset_response_schema(self, obj):
        return obj.api_asset.response_schema if obj.api_asset_id and obj.api_asset else None

    def get_api_updated(self, obj):
        """检测关联 API 资产自上次同步后是否有变更。"""
        if obj.api_asset_id and obj.api_synced_at and obj.api_asset and not obj.api_asset.is_deleted:
            try:
                return obj.api_asset.updated_at > obj.api_synced_at
            except (TypeError, AttributeError):
                pass
        return False


class TestSceneExecutionListSerializer(serializers.ModelSerializer):
    """轻量序列化器 — 列表页使用，不包含 node_results/summary 等大 JSON 字段"""
    scene_name = serializers.CharField(source='scene.name', read_only=True)
    project_name = serializers.SerializerMethodField()
    environment_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    def get_project_name(self, obj):
        try:
            return obj.scene.project.platform_project.name
        except AttributeError:
            return None

    def get_environment_name(self, obj):
        return obj.environment.name if obj.environment else None

    def get_created_by_name(self, obj):
        return obj.created_by.username if obj.created_by else None

    class Meta:
        model = TestSceneExecution
        fields = [
            'id', 'scene', 'scene_name', 'project_name',
            'target_node', 'run_mode',
            'status', 'total_nodes', 'passed_nodes', 'failed_nodes', 'skipped_nodes',
            'duration_ms',
            'started_at', 'finished_at',
            'created_by_name', 'environment', 'environment_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class TestSceneExecutionSerializer(TestSceneExecutionListSerializer):
    """完整序列化器 — 详情页使用，含 node_results/summary/error_message"""

    class Meta(TestSceneExecutionListSerializer.Meta):
        fields = TestSceneExecutionListSerializer.Meta.fields + [
            'summary', 'node_results', 'error_message',
        ]


class SceneDownloadedFileSerializer(serializers.ModelSerializer):
    """下载文件序列化器"""
    scene_name = serializers.CharField(source='scene.name', read_only=True)
    node_name = serializers.CharField(source='node.name', read_only=True, allow_null=True)
    execution_status = serializers.CharField(source='execution.status', read_only=True, allow_null=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)

    class Meta:
        model = SceneDownloadedFile
        fields = [
            'id', 'execution', 'node', 'scene', 'project',
            'filename', 'file_path', 'file_size', 'md5', 'content_type',
            'scene_name', 'node_name', 'execution_status', 'created_by_name',
            'created_at',
        ]
        read_only_fields = ['created_at']


# ========================================================================
#  定时任务
# ========================================================================

class ScheduledTaskSerializer(serializers.ModelSerializer):
    """定时任务序列化器"""
    test_suite_name = serializers.SerializerMethodField()
    test_scene_name = serializers.SerializerMethodField()
    environment_name = serializers.CharField(source='environment.name', read_only=True, allow_null=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    success_rate = serializers.FloatField(read_only=True)
    project_id = serializers.SerializerMethodField()

    class Meta:
        model = ScheduledTask
        fields = '__all__'
        read_only_fields = [
            'created_by', 'celery_task_id',
            'last_run_time', 'next_run_time',
            'total_runs', 'successful_runs', 'failed_runs',
            'created_at', 'updated_at', 'success_rate',
        ]

    def get_test_suite_name(self, obj):
        return obj.test_suite.name if obj.test_suite else None

    def get_test_scene_name(self, obj):
        return obj.test_scene.name if obj.test_scene else None

    def get_project_id(self, obj):
        """返回关联的 Project ID（无论是通过 test_suite 还是 test_scene）"""
        if obj.test_suite:
            return obj.test_suite.project_id
        if obj.test_scene:
            # TestScene.project → ApiProject → platform_project → Project
            try:
                return obj.test_scene.project.platform_project_id
            except AttributeError:
                return None
        return None

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class TaskExecutionLogSerializer(serializers.ModelSerializer):
    """任务执行日志序列化器"""
    scheduled_task_name = serializers.CharField(source='scheduled_task.name', read_only=True)
    test_run_name = serializers.CharField(source='test_run.name', read_only=True, allow_null=True)
    success_rate = serializers.SerializerMethodField()
    scene_execution_scene_id = serializers.SerializerMethodField()

    class Meta:
        model = TaskExecutionLog
        fields = '__all__'
        read_only_fields = ['created_at']

    def get_success_rate(self, obj):
        return obj.success_rate

    def get_scene_execution_scene_id(self, obj):
        if obj.scene_execution_id:
            return obj.scene_execution.scene_id
        return None


# ========================================================================
#  邮件配置
# ========================================================================

class EmailConfigSerializer(serializers.ModelSerializer):
    """邮件配置序列化器"""
    class Meta:
        model = EmailConfig
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


# ========================================================================
#  参数配置
# ========================================================================

class ParameterConfigSerializer(serializers.ModelSerializer):
    """参数配置序列化器"""
    class Meta:
        model = ParameterConfig
        fields = '__all__'
        read_only_fields = ['updated_at']
