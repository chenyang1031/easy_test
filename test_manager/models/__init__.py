"""
test_manager 模型包

从独立模型文件导入所有模型，并导出性能测试相关模型。
"""
from test_manager.models.project import Project, ApiProject
from test_manager.models.api_asset import ApiGroup, ApiAsset, ApiHistory, ApiAssetChangeRecord, ApiPreset, ApiAssetDraft
from test_manager.models.test_case import TestCaseGroup, TestCase, TestSuiteGroup, TestSuite, TestSuiteCase, TestRun, TestResult, TestSuiteRun
from test_manager.models.scene import TestScene, TestSceneNode, TestSceneNodeSyncLog, TestSceneExecution, SceneDownloadedFile
from test_manager.models.environment import Environment
from test_manager.models.ai_draft import AICaseDraftGroup, AICaseDraft
from test_manager.models.scheduled import ScheduledTask, TaskExecutionLog
from test_manager.models.report import TestReport
from test_manager.models.email_config import EmailConfig
from test_manager.models.mock_data import MockData
from test_manager.models.document_gen import DocumentGenRecord, AIGenerationRecord
from test_manager.models.parameter import ParameterConfig

from .performance import PerformanceTestResult, PerformanceTestTask
from .test_case_rule import TestCaseGenerationRule, AICaseDraftRuleUsage  # noqa: F401
from .prompt_template import PromptTemplate  # noqa: F401
from .ai_model_provider import AIModelProvider  # noqa: F401
