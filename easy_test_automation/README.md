# EasyTest Automation

一个用于运行EasyTesting项目测试场景的Python自动化测试框架。

## 项目概述

本项目提供了一个完整的测试自动化框架，能够：

1. **运行现有Django测试**：无缝运行EasyTesting项目中的现有测试场景
2. **提供测试辅助工具**：包含测试数据生成、断言辅助等工具
3. **支持多种测试类型**：单元测试、集成测试、API测试、性能测试等
4. **生成测试报告**：支持HTML覆盖率报告和测试结果报告

## 项目结构

```
easy_test_automation/
├── conftest.py              # pytest配置和测试夹具
├── requirements.txt         # 项目依赖
├── pytest.ini              # pytest配置
├── run_tests.py            # 测试运行器
├── run_existing_tests.py   # 运行现有测试脚本
├── Makefile                # 常用命令
├── .gitignore              # Git忽略文件
├── __init__.py             # 项目包初始化
├── tests/                  # 测试目录
│   ├── __init__.py
│   └── test_example.py     # 示例测试
├── utils/                  # 工具目录
│   ├── __init__.py
│   └── test_helpers.py     # 测试辅助工具
├── config/                 # 配置目录
│   └── __init__.py
└── reports/                # 报告目录
    └── __init__.py
```

## 快速开始

### 1. 安装依赖

```bash
cd easy_test_automation
pip install -r requirements.txt
```

### 2. 运行现有测试

```bash
# 运行所有现有测试
python run_existing_tests.py

# 列出可用测试模块
python run_existing_tests.py --list

# 运行特定测试模块
python run_existing_tests.py -m tests_dashboard

# 运行特定测试类
python run_existing_tests.py -c DashboardSceneTests

# 运行特定测试方法
python run_existing_tests.py -c DashboardSceneTests -t test_parse_dashboard_project_id_valid
```

### 3. 运行新测试

```bash
# 运行所有测试
python run_tests.py

# 运行单元测试
python run_tests.py --unit

# 运行集成测试
python run_tests.py --integration

# 运行API测试
python run_tests.py --api

# 运行仪表盘测试
python run_tests.py --dashboard

# 运行性能测试
python run_tests.py --performance
```

### 4. 使用Makefile

```bash
# 查看所有可用命令
make help

# 安装依赖
make install

# 运行所有测试
make test

# 运行现有测试
make test-existing

# 生成覆盖率报告
make coverage

# 代码检查
make lint

# 代码格式化
make format
```

## 测试类型

### 单元测试
测试单个函数或方法的正确性。

```bash
make test-unit
```

### 集成测试
测试多个组件之间的交互。

```bash
make test-integration
```

### API测试
测试REST API端点的功能。

```bash
make test-api
```

### 仪表盘测试
测试仪表盘相关的功能。

```bash
make test-dashboard
```

### 性能测试
测试性能相关的功能。

```bash
make test-performance
```

## 测试辅助工具

### TestDataGenerator

测试数据生成器，用于创建测试所需的各种数据。

```python
from utils.test_helpers import TestDataGenerator

# 创建测试用户
user = TestDataGenerator.create_test_user()

# 创建测试项目
project = TestDataGenerator.create_test_project(created_by=user)

# 创建API资产
asset = TestDataGenerator.create_api_asset()

# 创建完整测试环境
setup = TestDataGenerator.create_full_test_setup()
```

### TestAssertions

测试断言辅助类，提供常用的断言方法。

```python
from utils.test_helpers import TestAssertions

# 断言响应成功
TestAssertions.assert_response_success(response, 200)

# 断言JSON响应
data = TestAssertions.assert_json_response(response, ['status', 'data'])

# 断言模型存在
TestAssertions.assert_model_exists(User, username='testuser')
```

### TestHelpers

测试辅助函数，提供常用的测试辅助功能。

```python
from utils.test_helpers import TestHelpers

# 获取或创建测试用户
user = TestHelpers.get_or_create_test_user('testuser')

# 创建完整测试环境
setup = TestHelpers.create_full_test_setup()

# 清理测试数据
TestHelpers.cleanup_test_data()
```

## 测试夹具

项目提供了多种测试夹具，可以在测试中直接使用：

```python
def test_example(test_user, test_project, test_api_asset):
    """使用测试夹具的示例"""
    assert test_user.username == 'test_user'
    assert test_project.name == '测试项目'
    assert test_api_asset.method == 'GET'
```

可用夹具：
- `test_user`：测试用户
- `test_project`：测试项目
- `test_api_project`：测试API项目
- `test_api_group`：测试API分组
- `test_api_asset`：测试API资产
- `test_case`：测试用例
- `api_client`：DRF测试客户端
- `authenticated_client`：已认证的测试客户端

## 测试标记

使用pytest标记来分类测试：

```python
@pytest.mark.unit
def test_unit_example():
    """单元测试示例"""
    pass

@pytest.mark.integration
def test_integration_example():
    """集成测试示例"""
    pass

@pytest.mark.api
def test_api_example():
    """API测试示例"""
    pass

@pytest.mark.slow
def test_slow_example():
    """慢速测试示例"""
    pass
```

运行特定标记的测试：

```bash
python run_tests.py -m unit
python run_tests.py -m integration
python run_tests.py -m api
```

## 配置说明

### pytest.ini

pytest配置文件，包含：
- Django设置模块
- 测试发现配置
- 测试标记定义
- 输出配置
- 超时设置

### conftest.py

pytest配置文件，包含：
- 环境设置
- 测试夹具
- 钩子函数

## 报告生成

### 覆盖率报告

```bash
make coverage
```

生成的报告位于 `reports/coverage/` 目录。

### 测试报告

```bash
python run_tests.py --html=reports/test_report.html
```

生成的报告位于 `reports/` 目录。

## 最佳实践

1. **测试命名**：使用描述性的测试名称，格式为 `test_<功能>_<场景>_<预期结果>`
2. **测试隔离**：每个测试应该独立运行，不依赖其他测试的状态
3. **使用夹具**：使用pytest夹具来管理测试数据和设置
4. **测试标记**：使用适当的标记来分类测试
5. **清理数据**：测试后清理创建的测试数据

## 常见问题

### Q: 如何运行特定的现有测试？

A: 使用 `run_existing_tests.py` 脚本：
```bash
python run_existing_tests.py -m tests_dashboard
```

### Q: 如何添加新的测试？

A: 在 `tests/` 目录下创建新的测试文件，遵循 `test_*.py` 命名规则。

### Q: 如何生成测试报告？

A: 使用 `make coverage` 或 `python run_tests.py --html=reports/test_report.html`

### Q: 如何并行运行测试？

A: 使用 `python run_tests.py --parallel` 或 `make test-parallel`

## 贡献指南

1. 遵循PEP 8代码规范
2. 为新功能添加测试
3. 保持测试覆盖率在80%以上
4. 更新相关文档

## 许可证

本项目采用MIT许可证。