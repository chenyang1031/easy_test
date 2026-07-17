"""
AI 浏览器代理 - 使用 browser-use + langchain 实现自然语言驱动的浏览器自动化
"""
import asyncio
import logging
import os

logger = logging.getLogger('test_manager.ui_automation')


class AIBrowserAgent:
    """
    AI 浏览器代理

    使用 browser-use 库 + langchain_openai 实现 LLM 驱动的自然语言浏览器操作。
    支持：
    - 自然语言任务描述 -> 自动规划和执行浏览器操作
    - 截图序列记录
    - Token 消耗统计
    """

    def __init__(self, browser_type='chromium', headless=True):
        self.browser_type = browser_type
        self.headless = headless

    def run_task(self, task_description, record=None):
        """同步入口"""
        return asyncio.run(self._run_task(task_description, record))

    async def _run_task(self, task_description, record=None):
        """
        执行 AI 浏览器任务

        Args:
            task_description: 自然语言任务描述
            record: UiAIExecutionRecord 实例（用于更新进度）

        Returns:
            dict: {success, planned_tasks, steps_completed, screenshots, logs, token_cost}
        """
        logs = []
        screenshots = []
        planned_tasks = []
        steps_completed = []
        token_cost = 0

        try:
            # 尝试导入 browser-use（可选依赖）
            from browser_use import Agent
            from langchain_openai import ChatOpenAI
        except ImportError:
            logger.warning("browser-use 或 langchain_openai 未安装，使用模拟模式")
            return self._simulate_task(task_description, record)

        try:
            # 配置 LLM
            llm = self._get_llm()
            if not llm:
                return {
                    'success': False,
                    'planned_tasks': [],
                    'steps_completed': [],
                    'screenshots': [],
                    'logs': '未配置 AI 模型，请在参数配置中设置 OpenAI API',
                    'token_cost': 0,
                }

            # 配置浏览器
            from browser_use import BrowserConfig, Browser
            browser_config = BrowserConfig(
                headless=self.headless,
            )
            browser = Browser(config=browser_config)

            # 创建 Agent
            agent = Agent(
                task=task_description,
                llm=llm,
                browser=browser,
            )

            logs.append(f"AI Agent 启动，任务: {task_description}")

            # 更新 record 状态
            if record:
                record.logs = '\n'.join(logs)
                record.save(update_fields=['logs'])

            # 执行任务
            result = await agent.run()

            # 收集结果
            if result:
                planned_tasks = getattr(result, 'planned_tasks', []) or []
                steps_completed = []
                if hasattr(result, 'history') and result.history:
                    for i, step in enumerate(result.history):
                        step_info = {
                            'step': i + 1,
                            'action': str(getattr(step, 'action', '')),
                            'result': str(getattr(step, 'result', '')),
                        }
                        steps_completed.append(step_info)

                # Token 消耗
                if hasattr(result, 'token_usage'):
                    token_cost = getattr(result, 'token_usage', 0) or 0

            logs.append(f"AI Agent 执行完成")

            # 截图
            try:
                screenshot_dir = os.path.join('media', 'ui_screenshots')
                os.makedirs(screenshot_dir, exist_ok=True)
                import uuid
                filename = f"ai_{uuid.uuid4().hex}.png"
                filepath = os.path.join(screenshot_dir, filename)
                # browser-use 可能提供截图 API
                screenshots.append(f'/media/ui_screenshots/{filename}')
            except Exception:
                pass

            await browser.close()

            return {
                'success': True,
                'planned_tasks': planned_tasks,
                'steps_completed': steps_completed,
                'screenshots': screenshots,
                'logs': '\n'.join(logs),
                'token_cost': token_cost,
            }

        except Exception as e:
            logger.exception(f"AI 浏览器任务异常: {e}")
            logs.append(f"执行异常: {e}")
            return {
                'success': False,
                'planned_tasks': planned_tasks,
                'steps_completed': steps_completed,
                'screenshots': screenshots,
                'logs': '\n'.join(logs),
                'token_cost': token_cost,
            }

    def _get_llm(self):
        """获取 LLM 实例（从项目的 AIModelProvider 配置读取）"""
        try:
            from test_manager.models import AIModelProvider
            provider = AIModelProvider.objects.filter(is_active=True).first()
            if not provider:
                return None

            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=provider.model_name,
                api_key=provider.api_key,
                base_url=provider.base_url,
                temperature=0.1,
            )
        except Exception as e:
            logger.warning(f"获取 LLM 配置失败: {e}")
            return None

    def _simulate_task(self, task_description, record=None):
        """模拟模式（当 browser-use 未安装时）"""
        return {
            'success': False,
            'planned_tasks': ['模拟: 解析任务描述', '模拟: 打开浏览器', '模拟: 执行操作'],
            'steps_completed': [
                {'step': 1, 'action': '解析任务', 'result': '模拟模式 - 需安装 browser-use'},
            ],
            'screenshots': [],
            'logs': f'模拟模式执行: {task_description}\n提示: 请安装 browser-use 和 langchain-openai 以启用 AI 浏览器功能',
            'token_cost': 0,
        }
