.PHONY: help install test test-unit test-integration test-api test-dashboard test-performance clean

help: ## 显示帮助信息
	@echo "EasyTest Automation 可用命令:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## 安装依赖
	pip install -r requirements.txt

test: ## 运行所有测试
	python run_tests.py

test-unit: ## 运行单元测试
	python run_tests.py --unit

test-integration: ## 运行集成测试
	python run_tests.py --integration

test-api: ## 运行API测试
	python run_tests.py --api

test-dashboard: ## 运行仪表盘测试
	python run_tests.py --dashboard

test-performance: ## 运行性能测试
	python run_tests.py --performance

test-existing: ## 运行现有Django测试
	python run_existing_tests.py

test-existing-list: ## 列出现有测试
	python run_existing_tests.py --list

clean: ## 清理临时文件
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf reports/*
	rm -rf .pytest_cache
	rm -rf htmlcov

coverage: ## 生成覆盖率报告
	python -m pytest --cov=../test_manager --cov-report=html:reports/coverage --cov-report=term-missing

lint: ## 代码检查
	flake8 tests/ utils/
	black --check tests/ utils/
	isort --check-only tests/ utils/

format: ## 代码格式化
	black tests/ utils/
	isort tests/ utils/

type-check: ## 类型检查
	mypy tests/ utils/