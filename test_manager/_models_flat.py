"""
_backward-compatibility module_

Re-exports all model classes from the split model files.
保留此文件不影响 Django 迁移和已有引用代码。

原有模型类定义已拆分到 test_manager/models/ 目录下各文件中。
"""
# flake8: noqa: F401, F403
# pylint: disable=unused-import

from test_manager.models.project import Project, ApiProject
from test_manager.models.api_asset import (
    ApiGroup, ApiAsset, ApiHistory, ApiAssetChangeRecord,
    ApiPreset, ApiAssetDraft,
)
from test_manager.models.test_case import (
    TestCaseGroup, TestCase, TestSuiteGroup, TestSuite,
    TestSuiteCase, TestRun, TestResult, TestSuiteRun,
)
from test_manager.models.scene import (
    TestScene, TestSceneNode, TestSceneNodeSyncLog, TestSceneExecution,
)
from test_manager.models.environment import Environment
from test_manager.models.ai_draft import AICaseDraftGroup, AICaseDraft
from test_manager.models.scheduled import ScheduledTask, TaskExecutionLog
from test_manager.models.report import TestReport
from test_manager.models.email_config import EmailConfig
from test_manager.models.mock_data import MockData
from test_manager.models.document_gen import DocumentGenRecord, AIGenerationRecord
from test_manager.models.parameter import ParameterConfig
from test_manager.models.performance import PerformanceTestResult, PerformanceTestTask
from test_manager.models.test_case_rule import TestCaseGenerationRule, AICaseDraftRuleUsage
from test_manager.models.prompt_template import PromptTemplate
from test_manager.models.ai_model_provider import AIModelProvider
