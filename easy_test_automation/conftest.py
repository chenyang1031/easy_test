"""
EasyTest Automation 测试配置文件
"""
import os
import sys
import django
from django.conf import settings

# 将项目根目录添加到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 设置Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'EasyTesting.settings')

# 初始化Django
django.setup()

# 导入Django测试相关模块
from django.test.utils import setup_test_environment, teardown_test_environment
from django.test.runner import DiscoverRunner


def pytest_configure(config):
    """pytest配置钩子"""
    # 设置测试环境
    setup_test_environment()
    
    # 创建测试数据库
    test_runner = DiscoverRunner(verbosity=0)
    test_runner.setup_test_environment()


def pytest_unconfigure(config):
    """pytest清理钩子"""
    teardown_test_environment()


# 测试夹具
import pytest
from django.contrib.auth.models import User
from test_manager.models import Project, ApiProject, ApiGroup, ApiAsset, TestCase


@pytest.fixture
def test_user(db):
    """创建测试用户"""
    return User.objects.create_user(
        username='test_user',
        password='test_password',
        email='test@example.com'
    )


@pytest.fixture
def test_project(db, test_user):
    """创建测试项目"""
    return Project.objects.create(
        name='测试项目',
        description='测试项目描述',
        created_by=test_user
    )


@pytest.fixture
def test_api_project(db, test_project, test_user):
    """创建测试API项目"""
    return ApiProject.objects.create(
        platform_project=test_project,
        name='API测试项目',
        description='API测试项目描述',
        created_by=test_user
    )


@pytest.fixture
def test_api_group(db, test_api_project):
    """创建测试API分组"""
    return ApiGroup.objects.create(
        project=test_api_project,
        name='测试分组',
        sort_order=1
    )


@pytest.fixture
def test_api_asset(db, test_api_project, test_api_group, test_user):
    """创建测试API资产"""
    return ApiAsset.objects.create(
        project=test_api_project,
        group=test_api_group,
        name='测试接口',
        method='GET',
        url='/api/test',
        status=ApiAsset.STATUS_ACTIVE,
        source=ApiAsset.SOURCE_MANUAL,
        created_by=test_user
    )


@pytest.fixture
def test_case(db, test_project, test_user):
    """创建测试用例"""
    return TestCase.objects.create(
        name='测试用例',
        project=test_project,
        request_method='GET',
        request_url='/api/test',
        request_headers={},
        request_body={},
        request_body_format='json',
        expected_status_code=200,
        validation_rules=[],
        extract_params=[],
        created_by=test_user
    )


@pytest.fixture
def api_client():
    """创建DRF测试客户端"""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, test_user):
    """创建已认证的测试客户端"""
    api_client.force_authenticate(user=test_user)
    return api_client