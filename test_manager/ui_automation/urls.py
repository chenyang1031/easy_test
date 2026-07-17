"""
UI自动化 API 路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UiModuleViewSet,
    UiPageViewSet,
    UiElementViewSet,
    UiElementGroupViewSet,
    UiPageStepsViewSet,
    UiPageStepsDetailedViewSet,
    UiTestCaseViewSet,
    UiCaseStepsDetailedViewSet,
    UiTestScriptViewSet,
    UiScriptStepViewSet,
    UiPageObjectViewSet,
    UiBatchExecutionRecordViewSet,
    UiExecutionRecordViewSet,
    UiTriggerBatchViewSet,
    UiScreenshotUploadView,
    UiTraceUploadView,
    UiEnvironmentConfigViewSet,
    UiPublicDataViewSet,
    UiActuatorViewSet,
    UiScheduledTaskViewSet,
    UiNotificationLogViewSet,
    UiAICaseViewSet,
    UiAIExecutionRecordViewSet,
    UiOperationRecordViewSet,
    UiDashboardViewSet,
)

router = DefaultRouter()
router.register(r'ui-modules', UiModuleViewSet, basename='ui-module')
router.register(r'ui-pages', UiPageViewSet, basename='ui-page')
router.register(r'ui-elements', UiElementViewSet, basename='ui-element')
router.register(r'ui-element-groups', UiElementGroupViewSet, basename='ui-element-group')
router.register(r'ui-page-steps', UiPageStepsViewSet, basename='ui-page-step')
router.register(r'ui-page-steps-detailed', UiPageStepsDetailedViewSet, basename='ui-page-step-detailed')
router.register(r'ui-test-cases', UiTestCaseViewSet, basename='ui-test-case')
router.register(r'ui-case-steps-detailed', UiCaseStepsDetailedViewSet, basename='ui-case-step-detailed')
router.register(r'ui-test-scripts', UiTestScriptViewSet, basename='ui-test-script')
router.register(r'ui-script-steps', UiScriptStepViewSet, basename='ui-script-step')
router.register(r'ui-page-objects', UiPageObjectViewSet, basename='ui-page-object')
router.register(r'ui-batch-records', UiBatchExecutionRecordViewSet, basename='ui-batch-record')
router.register(r'ui-execution-records', UiExecutionRecordViewSet, basename='ui-execution-record')
router.register(r'ui-environments', UiEnvironmentConfigViewSet, basename='ui-environment')
router.register(r'ui-public-data', UiPublicDataViewSet, basename='ui-public-data')
router.register(r'ui-actuators', UiActuatorViewSet, basename='ui-actuator')
router.register(r'ui-scheduled-tasks', UiScheduledTaskViewSet, basename='ui-scheduled-task')
router.register(r'ui-notification-logs', UiNotificationLogViewSet, basename='ui-notification-log')
router.register(r'ui-ai-cases', UiAICaseViewSet, basename='ui-ai-case')
router.register(r'ui-ai-execution-records', UiAIExecutionRecordViewSet, basename='ui-ai-execution-record')
router.register(r'ui-operation-records', UiOperationRecordViewSet, basename='ui-operation-record')
router.register(r'ui-dashboard', UiDashboardViewSet, basename='ui-dashboard')

urlpatterns = [
    # 触发批量执行
    path('ui-trigger-batch/', UiTriggerBatchViewSet.as_view({'post': 'create'}), name='ui-trigger-batch'),
    # 文件上传
    path('ui-upload/screenshot/', UiScreenshotUploadView.as_view({'post': 'create'}), name='ui-upload-screenshot'),
    path('ui-upload/trace/', UiTraceUploadView.as_view({'post': 'create'}), name='ui-upload-trace'),
    # Router URLs
    path('', include(router.urls)),
]
