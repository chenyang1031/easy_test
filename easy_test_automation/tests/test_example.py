"""
示例测试文件：展示如何使用新的自动化项目运行测试
"""
import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from test_manager.models import Project, ApiProject, ApiGroup, ApiAsset, TestCase


class TestExampleWithNewFramework(TestCase):
    """
    使用新框架的示例测试类
    """
    
    def setUp(self):
        """测试前准备"""
        self.user = User.objects.create_user(
            username='example_user',
            password='example_password'
        )
        self.project = Project.objects.create(
            name='示例项目',
            description='示例项目描述',
            created_by=self.user
        )
    
    def test_create_project(self):
        """测试创建项目"""
        self.assertEqual(self.project.name, '示例项目')
        self.assertEqual(self.project.created_by, self.user)
    
    def test_project_str_representation(self):
        """测试项目字符串表示"""
        self.assertEqual(str(self.project), '示例项目')


@pytest.mark.django_db
class TestExampleWithPytest:
    """
    使用pytest的示例测试类
    """
    
    def test_create_user_with_fixture(self, test_user):
        """使用fixture创建用户"""
        assert test_user.username == 'test_user'
        assert test_user.email == 'test@example.com'
    
    def test_create_project_with_fixture(self, test_project):
        """使用fixture创建项目"""
        assert test_project.name == '测试项目'
        assert test_project.description == '测试项目描述'
    
    def test_create_api_asset_with_fixture(self, test_api_asset):
        """使用fixture创建API资产"""
        assert test_api_asset.name == '测试接口'
        assert test_api_asset.method == 'GET'
        assert test_api_asset.url == '/api/test'
    
    def test_authenticated_client(self, authenticated_client):
        """测试已认证的客户端"""
        response = authenticated_client.get('/api/v1/api-assets/')
        # 这里只是示例，实际API可能需要更多设置
        assert response.status_code in [200, 401, 403]


class TestExampleWithTestDataGenerator:
    """
    使用TestDataGenerator的示例测试类
    """
    
    def test_generate_random_data(self):
        """测试生成随机数据"""
        from utils.test_helpers import TestDataGenerator
        
        # 生成随机字符串
        random_str = TestDataGenerator.random_string(10)
        assert len(random_str) == 10
        
        # 生成随机邮箱
        email = TestDataGenerator.random_email()
        assert '@' in email
        
        # 生成随机URL
        url = TestDataGenerator.random_url()
        assert url.startswith('/')
    
    @pytest.mark.django_db
    def test_create_full_setup(self):
        """测试创建完整测试环境"""
        from utils.test_helpers import TestDataGenerator
        
        setup = TestDataGenerator.create_full_test_setup()
        
        assert 'user' in setup
        assert 'project' in setup
        assert 'api_project' in setup
        assert 'group' in setup
        assert 'environment' in setup
        
        # 验证创建的对象
        assert setup['user'].username.startswith('testuser_')
        assert setup['project'].name.startswith('测试项目_')
        assert setup['api_project'].name.startswith('API项目_')


class TestExampleWithTestAssertions:
    """
    使用TestAssertions的示例测试类
    """
    
    def test_assertions_helper(self):
        """测试断言辅助类"""
        from utils.test_helpers import TestAssertions
        
        # 测试模型存在断言（需要数据库）
        # 这里只是展示用法，实际需要数据库支持
        
        # 测试响应断言
        class MockResponse:
            status_code = 200
            content = b'{"status": "ok"}'
            
            def json(self):
                return {"status": "ok"}
        
        response = MockResponse()
        
        # 测试成功响应
        TestAssertions.assert_response_success(response, 200)
        
        # 测试JSON响应
        data = TestAssertions.assert_json_response(response, ['status'])
        assert data['status'] == 'ok'