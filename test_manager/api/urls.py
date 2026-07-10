from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProjectViewSet, EnvironmentViewSet, TestCaseViewSet,
    TestSuiteViewSet, TestRunViewSet, TestResultViewSet,
    AIGenerateMultiTestCasesViewSet, AIImportTestCasesViewSet, AICaseDraftBoxViewSet,
    RuleManagementViewSet,
    PromptTemplateManagementViewSet,
    AIModelProviderViewSet,
    TestCaseGroupViewSet, TestSuiteGroupViewSet,
    AIGenerationRecordViewSet,
)
from .api_asset_views import (
    ApiProjectViewSet,
    ApiGroupViewSet,
    ApiAssetViewSet,
    ApiImportExportViewSet,
    ApiPresetViewSet,
    ApiAssetDraftViewSet,
)
from .scene_views import (
    TestSceneViewSet,
    TestSceneNodeViewSet,
    TestSceneExecutionViewSet,
    SceneDownloadedFileViewSet,
)
from .performance_views import PerformanceTestTaskViewSet
from .replay_import_views import ReplayImportViewSet
from .mock_data_views import MockDataViewSet
from .document_gen_views import DocumentGenRecordViewSet
from .dashboard_views import DashboardStatsView
from .report_views import TestReportViewSet, ReportDownloadView
from .scene_report_views import SceneExecutionGenerateReportView
from .test_run_report_views import TestRunGenerateReportView
from .auth_views import (
    AuthLoginView,
    AuthLogoutView,
    AuthUserView,
    AuthRegisterView,
    AuthProfileView,
    AuthPasswordChangeView,
)
from .scheduled_task_views import (
    ScheduledTaskViewSet,
    TaskExecutionLogViewSet,
    TaskMonitorView,
    TaskSyncView,
    TaskCleanupView,
)
from .email_config_views import EmailConfigViewSet
from .parameter_config_views import ParameterConfigViewSet

router = DefaultRouter()
router.register(r'projects', ProjectViewSet)
router.register(r'environments', EnvironmentViewSet)
router.register(r'test-cases', TestCaseViewSet)
router.register(r'test-suites', TestSuiteViewSet)
router.register(r'test-runs', TestRunViewSet)
router.register(r'test-results', TestResultViewSet)
router.register(r'ai/generate-multi-test-cases', AIGenerateMultiTestCasesViewSet, basename='ai-generate-multi-test-cases')
router.register(r'ai/import-test-cases', AIImportTestCasesViewSet, basename='ai-import-test-cases')
router.register(r'ai/draft-box', AICaseDraftBoxViewSet, basename='ai-draft-box')
router.register(r'ai/rules', RuleManagementViewSet, basename='ai-rules')
router.register(r'ai/prompt-templates', PromptTemplateManagementViewSet, basename='ai-prompt-templates')
router.register(r'ai/model-providers', AIModelProviderViewSet, basename='ai-model-providers')
router.register(r'api-projects', ApiProjectViewSet, basename='api-project')
router.register(r'api-groups', ApiGroupViewSet, basename='api-group')
router.register(r'api-assets', ApiAssetViewSet, basename='api-asset')
router.register(r'api-presets', ApiPresetViewSet, basename='api-preset')
router.register(r'api-asset-drafts', ApiAssetDraftViewSet, basename='api-asset-draft')
router.register(r'test-scenes', TestSceneViewSet, basename='test-scene')
router.register(r'test-scene-nodes', TestSceneNodeViewSet, basename='test-scene-node')
router.register(r'test-scene-executions', TestSceneExecutionViewSet, basename='test-scene-execution')
router.register(r'downloaded-files', SceneDownloadedFileViewSet, basename='downloaded-file')
router.register(r'performance/tasks', PerformanceTestTaskViewSet, basename='performance-task')
router.register(r'ai/generation-records', AIGenerationRecordViewSet, basename='ai-generation-record')
router.register(r'test-case-groups', TestCaseGroupViewSet, basename='test-case-group')
router.register(r'test-suite-groups', TestSuiteGroupViewSet, basename='test-suite-group')
router.register(r'mock-data', MockDataViewSet, basename='mock-data')
router.register(r'ai/document-gen-records', DocumentGenRecordViewSet, basename='ai-document-gen-records')
router.register(r'reports', TestReportViewSet, basename='report')

urlpatterns = [
    # API v1 版本前缀
    path('v1/', include(router.urls)),
    path('v1/', include('test_manager.report.api_urls')),
    path(
        'v1/performance/task/<int:pk>/stop/',
        PerformanceTestTaskViewSet.as_view({'post': 'stop_test'}),
        name='performance-task-stop',
    ),
    path(
        'v1/api-assets/import/preview',
        ApiImportExportViewSet.as_view({'post': 'preview_import'}),
        name='api_asset_import_preview',
    ),
    path(
        'v1/api-assets/import/preview-url',
        ApiImportExportViewSet.as_view({'post': 'preview_url'}),
        name='api_asset_import_preview_url',
    ),
    path(
        'v1/api-assets/import/confirm',
        ApiImportExportViewSet.as_view({'post': 'confirm_import'}),
        name='api_asset_import_confirm',
    ),
    path(
        'v1/api-assets/export',
        ApiImportExportViewSet.as_view({'post': 'export_assets'}),
        name='api_asset_export',
    ),
    path(
        'v1/test-scenes/replay-import/preview',
        ReplayImportViewSet.as_view({'post': 'preview'}),
        name='replay_import_preview',
    ),
    path(
        'v1/test-scenes/replay-import/confirm',
        ReplayImportViewSet.as_view({'post': 'confirm'}),
        name='replay_import_confirm',
    ),
    path(
        'v1/scene-executions/<int:execution_id>/generate-report/',
        SceneExecutionGenerateReportView.as_view(),
        name='api_v1_scene_execution_generate_report',
    ),
    path(
        'v1/test-runs/<int:test_run_id>/generate-report/',
        TestRunGenerateReportView.as_view(),
        name='api_v1_test_run_generate_report',
    ),
    path(
        'v1/dashboard/stats/',
        DashboardStatsView.as_view(),
        name='dashboard-stats',
    ),
    path(
        'v1/reports/<int:pk>/download/',
        ReportDownloadView.as_view(),
        name='api_v1_report_download',
    ),
    # 认证 API — 供 Vue SPA 使用（JSON 接口）
    path('v1/auth/login/', AuthLoginView.as_view(), name='api_auth_login'),
    path('v1/auth/logout/', AuthLogoutView.as_view(), name='api_auth_logout'),
    path('v1/auth/user/', AuthUserView.as_view(), name='api_auth_user'),
    path('v1/auth/register/', AuthRegisterView.as_view(), name='api_auth_register'),
    path('v1/auth/profile/', AuthProfileView.as_view(), name='api_auth_profile'),
    path('v1/auth/password-change/', AuthPasswordChangeView.as_view(), name='api_auth_password_change'),
    # DRF 内置的 API 浏览器登录（HTML，开发调试用）
    path('v1/auth/', include('rest_framework.urls')),

    # ===== 定时任务 API =====
    path('v1/scheduled-tasks/',
         ScheduledTaskViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='scheduled-task-list'),
    path('v1/scheduled-tasks/<int:pk>/',
         ScheduledTaskViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}),
         name='scheduled-task-detail'),
    path('v1/scheduled-tasks/<int:pk>/toggle_status/',
         ScheduledTaskViewSet.as_view({'post': 'toggle_status'}),
         name='scheduled-task-toggle-status'),
    path('v1/scheduled-tasks/<int:pk>/run_now/',
         ScheduledTaskViewSet.as_view({'post': 'run_now'}),
         name='scheduled-task-run-now'),
    path('v1/task-execution-logs/',
         TaskExecutionLogViewSet.as_view({'get': 'list'}),
         name='task-execution-log-list'),
    path('v1/task-execution-logs/<int:pk>/',
         TaskExecutionLogViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'}),
         name='task-execution-log-detail'),
    path('v1/task-monitor/',
         TaskMonitorView.as_view(),
         name='api-task-monitor'),
    path('v1/task-monitor/sync/',
         TaskSyncView.as_view(),
         name='api-task-monitor-sync'),
    path('v1/task-monitor/cleanup/',
         TaskCleanupView.as_view(),
         name='api-task-monitor-cleanup'),
    # ===== 邮件配置 API =====
    path('v1/email-config/',
         EmailConfigViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='email-config-list'),
    path('v1/email-config/<int:pk>/',
         EmailConfigViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}),
         name='email-config-detail'),
    path('v1/email-config/<int:pk>/test_email/',
         EmailConfigViewSet.as_view({'post': 'test_email'}),
         name='email-config-test-email'),
    path('v1/email-config/<int:pk>/test_connection/',
         EmailConfigViewSet.as_view({'post': 'test_connection'}),
         name='email-config-test-connection'),
    path('v1/email-config/<int:pk>/activate/',
         EmailConfigViewSet.as_view({'post': 'activate'}),
         name='email-config-activate'),

    # ===== 参数配置 API =====
    path('v1/parameter-config/',
         ParameterConfigViewSet.as_view({'get': 'list'}),
         name='parameter-config-list'),
    path('v1/parameter-config/<int:pk>/',
         ParameterConfigViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}),
         name='parameter-config-detail'),
    path('v1/parameter-config/test_ai/',
         ParameterConfigViewSet.as_view({'post': 'test_ai'}),
         name='parameter-config-test-ai'),
]
