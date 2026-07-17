from django.contrib import admin
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


class UiElementInline(admin.TabularInline):
    model = UiElement
    extra = 0
    fields = ['name', 'element_type', 'locator_type', 'locator_value', 'validation_status']


@admin.register(UiModule)
class UiModuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'parent', 'level', 'order']
    list_filter = ['project', 'level']
    search_fields = ['name']


@admin.register(UiPage)
class UiPageAdmin(admin.ModelAdmin):
    list_display = ['name', 'module', 'url']
    list_filter = ['module__project']
    search_fields = ['name']
    inlines = [UiElementInline]


@admin.register(UiElement)
class UiElementAdmin(admin.ModelAdmin):
    list_display = ['name', 'page', 'element_type', 'locator_type', 'validation_status', 'usage_count']
    list_filter = ['element_type', 'locator_type', 'validation_status']
    search_fields = ['name', 'locator_value']


@admin.register(UiElementGroup)
class UiElementGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'parent_group']
    list_filter = ['project']


@admin.register(UiPageSteps)
class UiPageStepsAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'page', 'status']
    list_filter = ['project', 'status']
    search_fields = ['name']


@admin.register(UiPageStepsDetailed)
class UiPageStepsDetailedAdmin(admin.ModelAdmin):
    list_display = ['page_step', 'step_type', 'step_sort', 'ope_key']
    list_filter = ['step_type']


@admin.register(UiTestCase)
class UiTestCaseAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'module', 'level', 'status']
    list_filter = ['project', 'level', 'status']
    search_fields = ['name']


@admin.register(UiCaseStepsDetailed)
class UiCaseStepsDetailedAdmin(admin.ModelAdmin):
    list_display = ['test_case', 'page_step', 'case_sort', 'status']
    list_filter = ['status']


@admin.register(UiTestScript)
class UiTestScriptAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'script_type', 'language']
    list_filter = ['project', 'script_type', 'language']


@admin.register(UiScriptStep)
class UiScriptStepAdmin(admin.ModelAdmin):
    list_display = ['script', 'step_order', 'action_type']


@admin.register(UiPageObject)
class UiPageObjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'url']
    list_filter = ['project']
    search_fields = ['name']


@admin.register(UiPageObjectElement)
class UiPageObjectElementAdmin(admin.ModelAdmin):
    list_display = ['page_object', 'element', 'method_name', 'is_property']


@admin.register(UiBatchExecutionRecord)
class UiBatchExecutionRecordAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'status', 'trigger_type', 'total_cases', 'passed_cases', 'start_time']
    list_filter = ['project', 'status', 'trigger_type']


@admin.register(UiExecutionRecord)
class UiExecutionRecordAdmin(admin.ModelAdmin):
    list_display = ['test_case', 'batch', 'status', 'duration', 'start_time']
    list_filter = ['status', 'trigger_type']


@admin.register(UiEnvironmentConfig)
class UiEnvironmentConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'browser', 'headless', 'is_default']
    list_filter = ['project', 'browser', 'is_default']


@admin.register(UiPublicData)
class UiPublicDataAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'key', 'data_type', 'is_enabled']
    list_filter = ['project', 'data_type', 'is_enabled']


@admin.register(UiActuator)
class UiActuatorAdmin(admin.ModelAdmin):
    list_display = ['name', 'host', 'port', 'status', 'last_heartbeat']
    list_filter = ['status']


@admin.register(UiScheduledTask)
class UiScheduledTaskAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'trigger_type', 'is_active', 'last_run_at', 'next_run_at']
    list_filter = ['project', 'trigger_type', 'is_active']


@admin.register(UiNotificationLog)
class UiNotificationLogAdmin(admin.ModelAdmin):
    list_display = ['task', 'trigger_type', 'channel', 'status', 'sent_at']
    list_filter = ['channel', 'status']


@admin.register(UiAICase)
class UiAICaseAdmin(admin.ModelAdmin):
    list_display = ['name', 'project']
    list_filter = ['project']
    search_fields = ['name', 'task_description']


@admin.register(UiAIExecutionRecord)
class UiAIExecutionRecordAdmin(admin.ModelAdmin):
    list_display = ['ai_case', 'status', 'token_cost', 'duration', 'start_time']
    list_filter = ['status']


@admin.register(UiOperationRecord)
class UiOperationRecordAdmin(admin.ModelAdmin):
    list_display = ['user', 'action_type', 'target_model', 'target_id', 'timestamp']
    list_filter = ['action_type', 'target_model']
