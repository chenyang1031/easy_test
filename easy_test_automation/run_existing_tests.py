#!/usr/bin/env python
"""
运行现有Django测试场景的脚本
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path


def setup_environment():
    """设置环境变量"""
    # 获取项目根目录（easy_test目录）
    current_dir = Path(__file__).parent
    project_root = current_dir.parent
    sys.path.insert(0, str(project_root))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'EasyTesting.settings')


def run_existing_tests(test_module=None, test_class=None, test_method=None):
    """
    运行现有的Django测试
    
    Args:
        test_module: 测试模块名（如 tests_dashboard）
        test_class: 测试类名（如 DashboardSceneTests）
        test_method: 测试方法名（如 test_parse_dashboard_project_id_valid）
    """
    setup_environment()
    
    # 构建测试路径
    test_path = 'test_manager'
    
    if test_module:
        test_path = f'test_manager.{test_module}'
    elif test_class:
        test_path = f'test_manager.tests.{test_class}'
    elif test_method:
        test_path = f'test_manager.tests.{test_class}.{test_method}'
    
    # 使用Django测试运行器，在项目根目录运行
    cmd = [sys.executable, 'manage.py', 'test', test_path]
    
    print(f"运行命令: {' '.join(cmd)}")
    print(f"测试路径: {test_path}")
    
    # 在项目根目录运行命令
    project_root = Path(__file__).parent.parent
    result = subprocess.run(cmd, cwd=project_root)
    return result.returncode


def run_tests_by_module(module_name):
    """
    根据模块名运行测试
    
    Args:
        module_name: 模块名
    """
    return run_existing_tests(test_module=module_name)


def run_tests_by_class(class_name):
    """
    根据类名运行测试
    
    Args:
        class_name: 类名
    """
    return run_existing_tests(test_class=class_name)


def run_tests_by_method(class_name, method_name):
    """
    根据方法名运行测试
    
    Args:
        class_name: 类名
        method_name: 方法名
    """
    return run_existing_tests(test_class=class_name, test_method=method_name)


def run_all_existing_tests():
    """运行所有现有测试"""
    return run_existing_tests()


def list_available_tests():
    """列出可用的测试"""
    test_dir = Path(__file__).parent.parent / 'test_manager'
    test_files = list(test_dir.glob('tests*.py'))
    
    print("可用的测试模块:")
    for test_file in test_files:
        print(f"  - {test_file.stem}")
    
    return test_files


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='运行现有Django测试场景')
    parser.add_argument('-m', '--module', help='测试模块名')
    parser.add_argument('-c', '--class', dest='class_name', help='测试类名')
    parser.add_argument('-t', '--test', dest='test_name', help='测试方法名')
    parser.add_argument('-l', '--list', action='store_true', help='列出可用测试')
    
    args = parser.parse_args()
    
    if args.list:
        list_available_tests()
        return 0
    
    if args.module:
        return run_tests_by_module(args.module)
    elif args.class_name and args.test_name:
        return run_tests_by_method(args.class_name, args.test_name)
    elif args.class_name:
        return run_tests_by_class(args.class_name)
    else:
        return run_all_existing_tests()


if __name__ == '__main__':
    sys.exit(main())