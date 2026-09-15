"""
EasyTest Automation 测试辅助工具
"""
import os
import sys
import random
import string
from typing import Any, Dict, List, Optional
from django.contrib.auth.models import User
from test_manager.models import (
    Project, ApiProject, ApiGroup, ApiAsset, TestCase,
    Environment, TestScene, TestSceneExecution
)


class TestDataGenerator:
    """测试数据生成器"""
    
    @staticmethod
    def random_string(length=10):
        """生成随机字符串"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    @staticmethod
    def random_email():
        """生成随机邮箱"""
        username = TestDataGenerator.random_string(8)
        domains = ['example.com', 'test.com', 'demo.com']
        return f"{username}@{random.choice(domains)}"
    
    @staticmethod
    def random_url():
        """生成随机URL"""
        paths = ['/api/users', '/api/products', '/api/orders', '/api/test']
        return random.choice(paths)
    
    @staticmethod
    def random_http_method():
        """生成随机HTTP方法"""
        methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
        return random.choice(methods)
    
    @staticmethod
    def create_test_user(username=None, password='testpassword123'):
        """创建测试用户"""
        if username is None:
            username = f"testuser_{TestDataGenerator.random_string(6)}"
        return User.objects.create_user(
            username=username,
            password=password,
            email=TestDataGenerator.random_email()
        )
    
    @staticmethod
    def create_test_project(created_by=None, name=None):
        """创建测试项目"""
        if created_by is None:
            created_by = TestDataGenerator.create_test_user()
        if name is None:
            name = f"测试项目_{TestDataGenerator.random_string(6)}"
        return Project.objects.create(
            name=name,
            description=f"测试项目描述_{TestDataGenerator.random_string(10)}",
            created_by=created_by
        )
    
    @staticmethod
    def create_api_project(platform_project=None, created_by=None, name=None):
        """创建API项目"""
        if platform_project is None:
            platform_project = TestDataGenerator.create_test_project()
        if created_by is None:
            created_by = platform_project.created_by
        if name is None:
            name = f"API项目_{TestDataGenerator.random_string(6)}"
        return ApiProject.objects.create(
            platform_project=platform_project,
            name=name,
            description=f"API项目描述_{TestDataGenerator.random_string(10)}",
            created_by=created_by
        )
    
    @staticmethod
    def create_api_group(api_project=None, name=None):
        """创建API分组"""
        if api_project is None:
            api_project = TestDataGenerator.create_api_project()
        if name is None:
            name = f"分组_{TestDataGenerator.random_string(6)}"
        return ApiGroup.objects.create(
            project=api_project,
            name=name,
            sort_order=random.randint(1, 100)
        )
    
    @staticmethod
    def create_api_asset(api_project=None, group=None, created_by=None, **kwargs):
        """创建API资产"""
        if api_project is None:
            api_project = TestDataGenerator.create_api_project()
        if group is None:
            group = TestDataGenerator.create_api_group(api_project)
        if created_by is None:
            created_by = api_project.created_by
        
        defaults = {
            'name': f"接口_{TestDataGenerator.random_string(6)}",
            'method': TestDataGenerator.random_http_method(),
            'url': TestDataGenerator.random_url(),
            'status': ApiAsset.STATUS_ACTIVE,
            'source': ApiAsset.SOURCE_MANUAL,
            'created_by': created_by
        }
        defaults.update(kwargs)
        
        return ApiAsset.objects.create(
            project=api_project,
            group=group,
            **defaults
        )
    
    @staticmethod
    def create_test_case(project=None, created_by=None, **kwargs):
        """创建测试用例"""
        if project is None:
            project = TestDataGenerator.create_test_project()
        if created_by is None:
            created_by = project.created_by
        
        defaults = {
            'name': f"用例_{TestDataGenerator.random_string(6)}",
            'request_method': TestDataGenerator.random_http_method(),
            'request_url': TestDataGenerator.random_url(),
            'request_headers': {},
            'request_body': {},
            'request_body_format': 'json',
            'expected_status_code': 200,
            'validation_rules': [],
            'extract_params': [],
            'created_by': created_by
        }
        defaults.update(kwargs)
        
        return TestCase.objects.create(
            project=project,
            **defaults
        )
    
    @staticmethod
    def create_environment(project=None, name=None):
        """创建测试环境"""
        if project is None:
            project = TestDataGenerator.create_test_project()
        if name is None:
            name = f"环境_{TestDataGenerator.random_string(6)}"
        return Environment.objects.create(
            name=name,
            project=project,
            base_url=f"https://{TestDataGenerator.random_string(8)}.example.com"
        )
    
    @staticmethod
    def create_test_scene(api_project=None, created_by=None, **kwargs):
        """创建测试场景"""
        if api_project is None:
            api_project = TestDataGenerator.create_api_project()
        if created_by is None:
            created_by = api_project.created_by
        
        defaults = {
            'name': f"场景_{TestDataGenerator.random_string(6)}",
            'description': f"场景描述_{TestDataGenerator.random_string(10)}",
            'created_by': created_by
        }
        defaults.update(kwargs)
        
        return TestScene.objects.create(
            project=api_project,
            **defaults
        )
    
    @staticmethod
    def create_scene_execution(scene=None, environment=None, created_by=None, **kwargs):
        """创建场景执行记录"""
        if scene is None:
            scene = TestDataGenerator.create_test_scene()
        if environment is None:
            environment = TestDataGenerator.create_environment(scene.project.platform_project)
        if created_by is None:
            created_by = scene.created_by
        
        defaults = {
            'status': TestSceneExecution.STATUS_SUCCESS,
            'created_by': created_by
        }
        defaults.update(kwargs)
        
        return TestSceneExecution.objects.create(
            scene=scene,
            environment=environment,
            **defaults
        )


class TestAssertions:
    """测试断言辅助类"""
    
    @staticmethod
    def assert_response_success(response, expected_status=200):
        """断言响应成功"""
        assert response.status_code == expected_status, \
            f"期望状态码 {expected_status}，实际 {response.status_code}"
        return response
    
    @staticmethod
    def assert_response_contains(response, text):
        """断言响应包含文本"""
        content = response.content.decode('utf-8')
        assert text in content, f"响应中未找到 '{text}'"
        return response
    
    @staticmethod
    def assert_json_response(response, expected_keys=None):
        """断言JSON响应"""
        assert response.status_code == 200
        data = response.json()
        if expected_keys:
            for key in expected_keys:
                assert key in data, f"JSON响应中缺少键 '{key}'"
        return data
    
    @staticmethod
    def assert_model_exists(model_class, **kwargs):
        """断言模型实例存在"""
        assert model_class.objects.filter(**kwargs).exists(), \
            f"{model_class.__name__} 实例不存在，条件: {kwargs}"
    
    @staticmethod
    def assert_model_count(model_class, expected_count, **kwargs):
        """断言模型实例数量"""
        actual_count = model_class.objects.filter(**kwargs).count()
        assert actual_count == expected_count, \
            f"期望 {model_class.__name__} 数量为 {expected_count}，实际 {actual_count}"


class TestHelpers:
    """测试辅助函数"""
    
    @staticmethod
    def get_or_create_test_user(username='testuser'):
        """获取或创建测试用户"""
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@test.com',
                'password': 'testpassword123'
            }
        )
        if created:
            user.set_password('testpassword123')
            user.save()
        return user
    
    @staticmethod
    def cleanup_test_data():
        """清理测试数据"""
        # 按照依赖关系顺序删除
        TestSceneExecution.objects.all().delete()
        TestScene.objects.all().delete()
        TestCase.objects.all().delete()
        ApiAsset.objects.all().delete()
        ApiGroup.objects.all().delete()
        ApiProject.objects.all().delete()
        Environment.objects.all().delete()
        Project.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
    
    @staticmethod
    def create_full_test_setup():
        """创建完整的测试环境"""
        user = TestDataGenerator.create_test_user()
        project = TestDataGenerator.create_test_project(created_by=user)
        api_project = TestDataGenerator.create_api_project(platform_project=project, created_by=user)
        group = TestDataGenerator.create_api_group(api_project=api_project)
        environment = TestDataGenerator.create_environment(project=project)
        
        return {
            'user': user,
            'project': project,
            'api_project': api_project,
            'group': group,
            'environment': environment
        }