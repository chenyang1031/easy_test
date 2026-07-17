"""
UI自动化序列化器
"""
from rest_framework import serializers
from .models import (
    UiModule, UiPage, UiElement, UiElementGroup,
    UiPageSteps, UiPageStepsDetailed,
    UiTestCase, UiCaseStepsDetailed,
    UiTestScript, UiScriptStep,
    UiPageObject, UiPageObjectElement,
    UiBatchExecutionRecord, UiExecutionRecord,
    UiEnvironmentConfig, UiPublicData, UiActuator,
    UiScheduledTask, UiNotificationLog,
    UiAICase, UiAIExecutionRecord, UiOperationRecord,
)


# ============================================================
# 模块管理
# ============================================================

class UiModuleSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    element_count = serializers.SerializerMethodField()
    creator_name = serializers.CharField(source='created_by.username', read_only=True, default='')

    class Meta:
        model = UiModule
        fields = [
            'id', 'project', 'name', 'parent', 'level', 'order',
            'description', 'children', 'element_count', 'creator_name',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_children(self, obj):
        children = obj.children.all().order_by('order', 'name')
        return UiModuleSerializer(children, many=True, context=self.context).data

    def get_element_count(self, obj):
        return UiElement.objects.filter(page__module=obj).count()


class UiModuleMoveSerializer(serializers.Serializer):
    target_id = serializers.IntegerField(required=False, allow_null=True)
    drop_position = serializers.ChoiceField(choices=['before', 'after', 'inside'])


# ============================================================
# 页面管理
# ============================================================

class UiElementSerializer(serializers.ModelSerializer):
    page_name = serializers.CharField(source='page.name', read_only=True, default='')
    module_name = serializers.CharField(source='page.module.name', read_only=True, default='')
    creator_name = serializers.CharField(source='created_by.username', read_only=True, default='')

    class Meta:
        model = UiElement
        fields = [
            'id', 'page', 'page_name', 'module_name', 'name', 'element_type',
            'locator_type', 'locator_value', 'locator_index',
            'locator_type_2', 'locator_value_2', 'locator_index_2',
            'locator_type_3', 'locator_value_3', 'locator_index_3',
            'is_iframe', 'iframe_locator',
            'wait_time', 'is_visible', 'is_enabled', 'force_action', 'is_unique',
            'validation_status', 'validation_message', 'last_validated', 'usage_count',
            'parent_element', 'component', 'page_name', 'description',
            'created_by', 'creator_name', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'usage_count', 'last_validated']


class UiElementValidateSerializer(serializers.Serializer):
    environment = serializers.IntegerField(required=False)


class UiElementSuggestionSerializer(serializers.Serializer):
    page_url = serializers.URLField(required=False)


class UiPageSerializer(serializers.ModelSerializer):
    module_name = serializers.CharField(source='module.name', read_only=True, default='')
    element_count = serializers.SerializerMethodField()
    creator_name = serializers.CharField(source='created_by.username', read_only=True, default='')

    class Meta:
        model = UiPage
        fields = [
            'id', 'module', 'module_name', 'name', 'url', 'description',
            'element_count', 'creator_name', 'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_element_count(self, obj):
        return obj.elements.count()


class UiPageDetailSerializer(UiPageSerializer):
    elements = UiElementSerializer(many=True, read_only=True)

    class Meta(UiPageSerializer.Meta):
        fields = UiPageSerializer.Meta.fields + ['elements']


# ============================================================
# 元素分组
# ============================================================

class UiElementGroupSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    element_count = serializers.SerializerMethodField()

    class Meta:
        model = UiElementGroup
        fields = ['id', 'project', 'name', 'parent_group', 'description', 'children', 'element_count', 'created_at']

    def get_children(self, obj):
        children = obj.children.all()
        return UiElementGroupSerializer(children, many=True).data

    def get_element_count(self, obj):
        return 0  # TODO: implement element-group relationship


# ============================================================
# 操作步骤
# ============================================================

class UiPageStepsDetailedSerializer(serializers.ModelSerializer):
    element_name = serializers.CharField(source='element.name', read_only=True, default='')
    step_type_display = serializers.CharField(source='get_step_type_display', read_only=True)

    class Meta:
        model = UiPageStepsDetailed
        fields = [
            'id', 'page_step', 'step_type', 'step_type_display',
            'element', 'element_name', 'step_sort',
            'ope_key', 'ope_value', 'sql_execute',
            'custom', 'condition_value', 'func',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class UiPageStepsDetailedBatchSerializer(serializers.Serializer):
    details = UiPageStepsDetailedSerializer(many=True)


class UiPageStepsSerializer(serializers.ModelSerializer):
    module_name = serializers.CharField(source='module.name', read_only=True, default='')
    page_name = serializers.CharField(source='page.name', read_only=True, default='')
    detail_count = serializers.SerializerMethodField()
    creator_name = serializers.CharField(source='created_by.username', read_only=True, default='')

    class Meta:
        model = UiPageSteps
        fields = [
            'id', 'project', 'page', 'page_name', 'module', 'module_name',
            'name', 'status', 'flow_data', 'description',
            'detail_count', 'creator_name', 'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_detail_count(self, obj):
        return obj.details.count()


class UiPageStepsDetailSerializer(UiPageStepsSerializer):
    details = UiPageStepsDetailedSerializer(many=True, read_only=True)

    class Meta(UiPageStepsSerializer.Meta):
        fields = UiPageStepsSerializer.Meta.fields + ['details']


# ============================================================
# 测试用例
# ============================================================

class UiCaseStepsDetailedSerializer(serializers.ModelSerializer):
    page_step_name = serializers.CharField(source='page_step.name', read_only=True, default='')

    class Meta:
        model = UiCaseStepsDetailed
        fields = [
            'id', 'test_case', 'page_step', 'page_step_name',
            'case_sort', 'case_data', 'switch_step_open_url',
            'error_retry', 'status', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class UiCaseStepsDetailedBatchSerializer(serializers.Serializer):
    steps = UiCaseStepsDetailedSerializer(many=True)


class UiTestCaseSerializer(serializers.ModelSerializer):
    module_name = serializers.CharField(source='module.name', read_only=True, default='')
    step_count = serializers.SerializerMethodField()
    creator_name = serializers.CharField(source='created_by.username', read_only=True, default='')

    class Meta:
        model = UiTestCase
        fields = [
            'id', 'project', 'module', 'module_name', 'name', 'description',
            'level', 'status', 'front_sql', 'front_custom', 'posterior_sql',
            'parametrize', 'step_count', 'creator_name',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_step_count(self, obj):
        return obj.case_steps.count()


class UiTestCaseDetailSerializer(UiTestCaseSerializer):
    case_steps = UiCaseStepsDetailedSerializer(many=True, read_only=True)

    class Meta(UiTestCaseSerializer.Meta):
        fields = UiTestCaseSerializer.Meta.fields + ['case_steps']


class UiTestCaseBatchDeleteSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField())


class UiTestCaseRunSerializer(serializers.Serializer):
    environment = serializers.IntegerField(required=True)
    actuator = serializers.IntegerField(required=False, allow_null=True)
    browser = serializers.ChoiceField(choices=['chromium', 'firefox', 'webkit'], default='chromium')
    headless = serializers.BooleanField(default=True)


# ============================================================
# 脚本管理
# ============================================================

class UiScriptStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = UiScriptStep
        fields = ['id', 'script', 'step_order', 'action_type', 'action_params', 'expected_result', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class UiTestScriptSerializer(serializers.ModelSerializer):
    step_count = serializers.SerializerMethodField()
    creator_name = serializers.CharField(source='created_by.username', read_only=True, default='')

    class Meta:
        model = UiTestScript
        fields = [
            'id', 'project', 'name', 'description', 'script_type',
            'content', 'language', 'step_count', 'creator_name',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_step_count(self, obj):
        return obj.steps.count()


class UiTestScriptDetailSerializer(UiTestScriptSerializer):
    steps = UiScriptStepSerializer(many=True, read_only=True)

    class Meta(UiTestScriptSerializer.Meta):
        fields = UiTestScriptSerializer.Meta.fields + ['steps']


# ============================================================
# Page Object
# ============================================================

class UiPageObjectElementSerializer(serializers.ModelSerializer):
    element_name = serializers.CharField(source='element.name', read_only=True, default='')

    class Meta:
        model = UiPageObjectElement
        fields = ['id', 'page_object', 'element', 'element_name', 'method_name', 'is_property']


class UiPageObjectSerializer(serializers.ModelSerializer):
    element_count = serializers.SerializerMethodField()
    creator_name = serializers.CharField(source='created_by.username', read_only=True, default='')

    class Meta:
        model = UiPageObject
        fields = [
            'id', 'project', 'name', 'url', 'description',
            'generated_code_js', 'generated_code_python',
            'element_count', 'creator_name',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_element_count(self, obj):
        return obj.po_elements.count()


class UiPageObjectDetailSerializer(UiPageObjectSerializer):
    po_elements = UiPageObjectElementSerializer(many=True, read_only=True)

    class Meta(UiPageObjectSerializer.Meta):
        fields = UiPageObjectSerializer.Meta.fields + ['po_elements']


# ============================================================
# 执行记录
# ============================================================

class UiExecutionRecordSerializer(serializers.ModelSerializer):
    test_case_name = serializers.CharField(source='test_case.name', read_only=True, default='')

    class Meta:
        model = UiExecutionRecord
        fields = [
            'id', 'batch', 'test_case', 'test_case_name', 'executor',
            'status', 'trigger_type', 'step_results', 'screenshots',
            'video_path', 'trace_path', 'start_time', 'end_time',
            'duration', 'error_message',
        ]
        read_only_fields = ['created_at']


class UiExecutionRecordDetailSerializer(UiExecutionRecordSerializer):
    class Meta(UiExecutionRecordSerializer.Meta):
        fields = UiExecutionRecordSerializer.Meta.fields + ['log', 'trace_data']


class UiBatchExecutionRecordSerializer(serializers.ModelSerializer):
    execution_records = UiExecutionRecordSerializer(many=True, read_only=True)
    creator_name = serializers.CharField(source='created_by.username', read_only=True, default='')
    pass_rate = serializers.SerializerMethodField()

    class Meta:
        model = UiBatchExecutionRecord
        fields = [
            'id', 'project', 'name', 'total_cases', 'passed_cases', 'failed_cases',
            'status', 'trigger_type', 'start_time', 'end_time', 'duration',
            'execution_records', 'creator_name', 'pass_rate', 'created_at',
        ]
        read_only_fields = ['created_at']

    def get_pass_rate(self, obj):
        if obj.total_cases > 0:
            return round(obj.passed_cases / obj.total_cases * 100, 1)
        return 0


class UiBatchRecordListSerializer(serializers.ModelSerializer):
    """列表视图用的简化版（不含execution_records）"""
    creator_name = serializers.CharField(source='created_by.username', read_only=True, default='')
    pass_rate = serializers.SerializerMethodField()

    class Meta:
        model = UiBatchExecutionRecord
        fields = [
            'id', 'project', 'name', 'total_cases', 'passed_cases', 'failed_cases',
            'status', 'trigger_type', 'start_time', 'end_time', 'duration',
            'creator_name', 'pass_rate', 'created_at',
        ]

    def get_pass_rate(self, obj):
        if obj.total_cases > 0:
            return round(obj.passed_cases / obj.total_cases * 100, 1)
        return 0


class UiTriggerBatchSerializer(serializers.Serializer):
    test_case_ids = serializers.ListField(child=serializers.IntegerField())
    environment = serializers.IntegerField(required=True)
    actuator = serializers.IntegerField(required=False, allow_null=True)
    browser = serializers.ChoiceField(choices=['chromium', 'firefox', 'webkit'], default='chromium')
    headless = serializers.BooleanField(default=True)
    trigger_type = serializers.ChoiceField(choices=['manual', 'scheduled', 'api'], default='manual')


# ============================================================
# 环境配置
# ============================================================

class UiEnvironmentConfigSerializer(serializers.ModelSerializer):
    creator_name = serializers.CharField(source='created_by.username', read_only=True, default='')

    class Meta:
        model = UiEnvironmentConfig
        fields = [
            'id', 'project', 'name', 'base_url', 'is_default',
            'browser', 'headless', 'viewport_width', 'viewport_height', 'timeout',
            'db_status', 'db_type', 'mysql_config', 'db2_config',
            'creator_name', 'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']


# ============================================================
# 公共数据
# ============================================================

class UiPublicDataSerializer(serializers.ModelSerializer):
    data_type_display = serializers.CharField(source='get_data_type_display', read_only=True)

    class Meta:
        model = UiPublicData
        fields = [
            'id', 'project', 'name', 'data_type', 'data_type_display',
            'key', 'value', 'is_enabled', 'description',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


# ============================================================
# 执行器
# ============================================================

class UiActuatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = UiActuator
        fields = [
            'id', 'name', 'host', 'port', 'status',
            'browser_capabilities', 'last_heartbeat',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


# ============================================================
# 定时任务
# ============================================================

class UiScheduledTaskSerializer(serializers.ModelSerializer):
    creator_name = serializers.CharField(source='created_by.username', read_only=True, default='')
    environment_name = serializers.CharField(source='environment.name', read_only=True, default='')
    test_case_count = serializers.SerializerMethodField()

    class Meta:
        model = UiScheduledTask
        fields = [
            'id', 'project', 'name', 'task_type', 'trigger_type',
            'cron_expression', 'interval_seconds', 'run_at',
            'test_cases', 'environment', 'environment_name',
            'actuator', 'engine', 'browser', 'headless',
            'notify_on_success', 'notify_on_failure', 'notify_email', 'notify_webhook',
            'total_runs', 'successful_runs', 'failed_runs',
            'last_run_at', 'next_run_at', 'is_active',
            'test_case_count', 'creator_name',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'total_runs', 'successful_runs', 'failed_runs', 'last_run_at', 'next_run_at']

    def get_test_case_count(self, obj):
        return obj.test_cases.count()


# ============================================================
# 通知日志
# ============================================================

class UiNotificationLogSerializer(serializers.ModelSerializer):
    task_name = serializers.CharField(source='task.name', read_only=True, default='')

    class Meta:
        model = UiNotificationLog
        fields = [
            'id', 'task', 'task_name', 'trigger_type', 'channel',
            'recipient', 'status', 'retry_count', 'content',
            'error_message', 'sent_at',
        ]


# ============================================================
# AI
# ============================================================

class UiAICaseSerializer(serializers.ModelSerializer):
    creator_name = serializers.CharField(source='created_by.username', read_only=True, default='')

    class Meta:
        model = UiAICase
        fields = [
            'id', 'project', 'name', 'task_description', 'tags',
            'creator_name', 'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class UiAIExecutionRecordSerializer(serializers.ModelSerializer):
    ai_case_name = serializers.CharField(source='ai_case.name', read_only=True, default='')
    creator_name = serializers.CharField(source='created_by.username', read_only=True, default='')

    class Meta:
        model = UiAIExecutionRecord
        fields = [
            'id', 'ai_case', 'ai_case_name', 'status',
            'planned_tasks', 'steps_completed', 'screenshots_sequence',
            'gif_path', 'token_cost', 'start_time', 'end_time', 'duration',
            'creator_name', 'created_by', 'created_at',
        ]
        read_only_fields = ['created_by', 'created_at']


class UiAIExecutionRecordDetailSerializer(UiAIExecutionRecordSerializer):
    class Meta(UiAIExecutionRecordSerializer.Meta):
        fields = UiAIExecutionRecordSerializer.Meta.fields + ['logs']


class UiAICaseRunSerializer(serializers.Serializer):
    environment = serializers.IntegerField(required=False)
    browser = serializers.ChoiceField(choices=['chromium', 'firefox', 'webkit'], default='chromium')
    headless = serializers.BooleanField(default=True)


# ============================================================
# 操作审计
# ============================================================

class UiOperationRecordSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True, default='')

    class Meta:
        model = UiOperationRecord
        fields = [
            'id', 'project', 'user', 'user_name', 'action_type',
            'target_model', 'target_id', 'target_name',
            'old_value', 'new_value', 'timestamp',
        ]


# ============================================================
# 仪表盘
# ============================================================

class UiDashboardStatsSerializer(serializers.Serializer):
    total_modules = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    total_elements = serializers.IntegerField()
    total_test_cases = serializers.IntegerField()
    total_executions = serializers.IntegerField()
    pass_rate = serializers.FloatField()
    recent_executions = serializers.ListField()
    cases_by_level = serializers.DictField()
