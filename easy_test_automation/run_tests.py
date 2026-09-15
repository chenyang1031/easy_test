#!/usr/bin/env python
"""
EasyTest Automation 测试运行器
用于运行现有的Django测试场景
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path


def setup_environment():
    """设置环境变量"""
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'EasyTesting.settings')


def run_tests(test_path=None, markers=None, verbose=False, parallel=False, coverage=True):
    """
    运行测试
    
    Args:
        test_path: 测试路径（可选）
        markers: 测试标记（可选）
        verbose: 是否显示详细输出
        parallel: 是否并行运行
        coverage: 是否生成覆盖率报告
    """
    setup_environment()
    
    # 构建pytest命令
    cmd = ['python', '-m', 'pytest']
    
    # 添加测试路径
    if test_path:
        cmd.append(test_path)
    
    # 添加标记过滤
    if markers:
        cmd.extend(['-m', markers])
    
    # 添加详细输出
    if verbose:
        cmd.append('-v')
    
    # 添加并行运行
    if parallel:
        cmd.extend(['-n', 'auto'])
    
    # 添加覆盖率
    if coverage:
        cmd.extend(['--cov=../test_manager', '--cov-report=html:reports/coverage'])
    
    # 运行测试
    print(f"运行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    
    return result.returncode


def run_specific_tests(test_names):
    """
    运行特定的测试
    
    Args:
        test_names: 测试名称列表
    """
    setup_environment()
    
    cmd = ['python', '-m', 'pytest']
    cmd.extend(test_names)
    
    print(f"运行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    
    return result.returncode


def run_tests_by_marker(marker):
    """
    根据标记运行测试
    
    Args:
        marker: 测试标记
    """
    return run_tests(markers=marker)


def run_all_tests():
    """运行所有测试"""
    return run_tests()


def run_unit_tests():
    """运行单元测试"""
    return run_tests(markers='unit')


def run_integration_tests():
    """运行集成测试"""
    return run_tests(markers='integration')


def run_api_tests():
    """运行API测试"""
    return run_tests(markers='api')


def run_dashboard_tests():
    """运行仪表盘测试"""
    return run_tests(markers='dashboard')


def run_performance_tests():
    """运行性能测试"""
    return run_tests(markers='performance')


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='EasyTest Automation 测试运行器')
    parser.add_argument('test_path', nargs='?', help='测试路径')
    parser.add_argument('-m', '--markers', help='测试标记')
    parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    parser.add_argument('-p', '--parallel', action='store_true', help='并行运行')
    parser.add_argument('--no-coverage', action='store_true', help='不生成覆盖率报告')
    parser.add_argument('--specific', nargs='+', help='运行特定测试')
    parser.add_argument('--unit', action='store_true', help='运行单元测试')
    parser.add_argument('--integration', action='store_true', help='运行集成测试')
    parser.add_argument('--api', action='store_true', help='运行API测试')
    parser.add_argument('--dashboard', action='store_true', help='运行仪表盘测试')
    parser.add_argument('--performance', action='store_true', help='运行性能测试')
    
    args = parser.parse_args()
    
    # 根据参数运行测试
    if args.specific:
        return run_specific_tests(args.specific)
    elif args.unit:
        return run_unit_tests()
    elif args.integration:
        return run_integration_tests()
    elif args.api:
        return run_api_tests()
    elif args.dashboard:
        return run_dashboard_tests()
    elif args.performance:
        return run_performance_tests()
    else:
        return run_tests(
            test_path=args.test_path,
            markers=args.markers,
            verbose=args.verbose,
            parallel=args.parallel,
            coverage=not args.no_coverage
        )


if __name__ == '__main__':
    sys.exit(main())