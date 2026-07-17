"""
UI 测试执行器 - 编排 Playwright 引擎执行测试用例
"""
import asyncio
import logging
import json
import uuid
from django.utils import timezone

logger = logging.getLogger('test_manager.ui_automation')


class UIExecutor:
    """
    UI 测试用例执行器

    负责将测试用例中的步骤转换为 Playwright 操作并执行。
    支持 6 种操作类型：元素操作、断言、SQL、变量、条件、Python代码。
    """

    def __init__(self, env_config):
        """
        Args:
            env_config: UiEnvironmentConfig 实例
        """
        self.env = env_config
        self.engine = None
        self.variables = {}  # 运行时变量存储
        self.screenshots = []
        self.step_results = []
        self.logs = []

    def _log(self, message):
        self.logs.append(f"[{timezone.now().strftime('%H:%M:%S')}] {message}")
        logger.info(message)

    def execute_test_case(self, test_case):
        """同步入口：执行测试用例（内部启动异步循环）"""
        return asyncio.run(self._execute_test_case(test_case))

    async def _execute_test_case(self, test_case):
        """异步执行测试用例"""
        from .playwright_engine import PlaywrightEngine
        from .variable_resolver import VariableResolver

        self.engine = PlaywrightEngine(
            browser_type=self.env.browser,
            headless=self.env.headless,
            viewport_width=self.env.viewport_width,
            viewport_height=self.env.viewport_height,
            timeout=self.env.timeout,
        )

        resolver = VariableResolver(self.variables)

        try:
            await self.engine.start()
            await self.engine.start_trace(name=f"case_{test_case.id}_{uuid.uuid4().hex[:8]}")

            # 导航到基础 URL
            if self.env.base_url:
                await self.engine.navigate(self.env.base_url)
                self._log(f"导航到: {self.env.base_url}")

            # 加载公共变量
            await self._load_public_data(test_case.project_id)

            # 执行前置 SQL
            if test_case.front_sql:
                await self._execute_sql(test_case.front_sql, resolver)

            # 加载前置自定义变量
            if test_case.front_custom:
                self.variables.update(test_case.front_custom)

            # 获取用例步骤
            case_steps = test_case.case_steps.select_related(
                'page_step'
            ).prefetch_related(
                'page_step__details__element'
            ).order_by('case_sort')

            for case_step in case_steps:
                page_step = case_step.page_step
                details = page_step.details.order_by('step_sort')

                # 步骤切换时是否打开 URL
                if case_step.switch_step_open_url and page_step.page and page_step.page.url:
                    url = resolver.resolve(page_step.page.url)
                    await self.engine.navigate(url)
                    self._log(f"步骤切换导航: {url}")

                for detail in details:
                    try:
                        result = await self._execute_step_detail(detail, resolver, case_step.error_retry)
                        self.step_results.append({
                            'step_id': detail.id,
                            'step_sort': detail.step_sort,
                            'type': detail.get_step_type_display(),
                            'status': 'passed',
                            'message': result.get('message', ''),
                        })
                    except Exception as e:
                        self._log(f"步骤 {detail.step_sort} 失败: {e}")
                        screenshot_url = await self.engine.take_screenshot()
                        self.screenshots.append(screenshot_url)
                        self.step_results.append({
                            'step_id': detail.id,
                            'step_sort': detail.step_sort,
                            'type': detail.get_step_type_display(),
                            'status': 'failed',
                            'error': str(e),
                            'screenshot': screenshot_url,
                        })
                        # 有重试次数则重试
                        raise

            # 执行后置 SQL
            if test_case.posterior_sql:
                await self._execute_sql(test_case.posterior_sql, resolver)

            trace_path = await self.engine.stop_trace()
            video_path = await self.engine.stop_video()

            return {
                'success': True,
                'step_results': self.step_results,
                'screenshots': self.screenshots,
                'log': '\n'.join(self.logs),
                'trace_path': trace_path or '',
                'video_path': video_path or '',
            }

        except Exception as e:
            self._log(f"测试用例执行失败: {e}")
            try:
                screenshot_url = await self.engine.take_screenshot()
                self.screenshots.append(screenshot_url)
            except Exception:
                pass

            try:
                trace_path = await self.engine.stop_trace()
            except Exception:
                trace_path = None

            return {
                'success': False,
                'step_results': self.step_results,
                'screenshots': self.screenshots,
                'log': '\n'.join(self.logs),
                'error': str(e),
                'trace_path': trace_path or '',
            }

        finally:
            await self.engine.close()

    async def _execute_step_detail(self, detail, resolver, retry_count=0):
        """执行单个步骤明细，支持重试"""
        last_error = None
        for attempt in range(retry_count + 1):
            try:
                if attempt > 0:
                    self._log(f"重试第 {attempt} 次...")
                    await asyncio.sleep(1)
                return await self._do_execute_step(detail, resolver)
            except Exception as e:
                last_error = e
        raise last_error

    async def _do_execute_step(self, detail, resolver):
        """实际执行步骤逻辑"""
        step_type = detail.step_type

        if step_type == 0:
            # 元素操作
            return await self._execute_element_op(detail, resolver)
        elif step_type == 1:
            # 断言
            return await self._execute_assertion(detail, resolver)
        elif step_type == 2:
            # SQL 操作
            return await self._execute_sql(detail.sql_execute, resolver)
        elif step_type == 3:
            # 自定义变量
            return self._set_variable(detail, resolver)
        elif step_type == 4:
            # 条件逻辑
            return await self._execute_condition(detail, resolver)
        elif step_type == 5:
            # Python 代码
            return await self._execute_python(detail, resolver)
        else:
            raise ValueError(f"未知步骤类型: {step_type}")

    async def _execute_element_op(self, detail, resolver):
        """执行元素操作"""
        element = detail.element
        if not element:
            raise ValueError("元素操作缺少关联元素")

        # 使用降级定位
        locators = element.get_all_locators()
        iframe_locator = element.iframe_locator if element.is_iframe else None

        locator = await self.engine.locate_with_fallback(locators, wait_time=element.wait_time)

        ope_key = detail.ope_key
        ope_value = resolver.resolve(detail.ope_value)

        op_map = {
            'click': lambda: self.engine.click(locator, force=element.force_action),
            'fill': lambda: self.engine.fill(locator, ope_value),
            'type': lambda: self.engine.type_text(locator, ope_value),
            'select': lambda: self.engine.select_option(locator, ope_value),
            'check': lambda: self.engine.check(locator),
            'uncheck': lambda: self.engine.uncheck(locator),
            'hover': lambda: self.engine.hover(locator),
            'get_text': lambda: self.engine.get_text(locator),
            'get_attribute': lambda: self.engine.get_attribute(locator, ope_value),
            'upload': lambda: self.engine.upload_file(locator, ope_value),
            'press_key': lambda: self.engine.press_key(ope_value),
            'wait_visible': lambda: self.engine.wait_for_element(locator, 'visible'),
            'wait_hidden': lambda: self.engine.wait_for_element(locator, 'hidden'),
        }

        op_fn = op_map.get(ope_key)
        if not op_fn:
            raise ValueError(f"不支持的操作: {ope_key}")

        result = await op_fn()
        self._log(f"元素操作: {element.name} -> {ope_key}({ope_value})")

        # 存储结果到变量
        if result is not None:
            self.variables[f'__last_result__'] = result

        # 更新元素使用计数
        element.increment_usage_count()

        return {'message': f'{ope_key} 执行成功'}

    async def _execute_assertion(self, detail, resolver):
        """执行断言"""
        element = detail.element
        if not element:
            raise ValueError("断言操作缺少关联元素")

        locators = element.get_all_locators()
        locator = await self.engine.locate_with_fallback(locators, wait_time=element.wait_time)

        ope_key = detail.ope_key
        expected = resolver.resolve(detail.ope_value)

        if ope_key == 'assert_text':
            actual = await self.engine.get_text(locator)
            if expected not in (actual or ''):
                raise AssertionError(f"文本断言失败: 期望包含 '{expected}', 实际 '{actual}'")

        elif ope_key == 'assert_visible':
            visible = await self.engine.is_visible(locator)
            if not visible:
                raise AssertionError(f"可见性断言失败: 元素 {element.name} 不可见")

        elif ope_key == 'assert_enabled':
            enabled = await self.engine.is_enabled(locator)
            if not enabled:
                raise AssertionError(f"可用性断言失败: 元素 {element.name} 不可用")

        elif ope_key == 'assert_attribute':
            # expected 格式: "attr_name=expected_value"
            parts = expected.split('=', 1)
            if len(parts) != 2:
                raise ValueError("属性断言格式应为: attr_name=expected_value")
            attr_name, expected_val = parts
            actual = await self.engine.get_attribute(locator, attr_name.strip())
            if actual != expected_val.strip():
                raise AssertionError(
                    f"属性断言失败: {attr_name} 期望 '{expected_val}', 实际 '{actual}'"
                )
        else:
            raise ValueError(f"不支持的断言类型: {ope_key}")

        self._log(f"断言通过: {element.name} -> {ope_key}")
        return {'message': f'断言 {ope_key} 通过'}

    async def _execute_sql(self, sql, resolver):
        """执行 SQL（如果环境配置了数据库）"""
        if not self.env.db_status:
            self._log("数据库未启用，跳过 SQL 执行")
            return {'message': '数据库未启用'}

        resolved_sql = resolver.resolve(sql)
        self._log(f"执行 SQL: {resolved_sql[:100]}...")

        # 简化实现：通过 Django ORM 连接配置的数据库
        try:
            from django.db import connections
            db_alias = 'default'
            with connections[db_alias].cursor() as cursor:
                cursor.execute(resolved_sql)
                if resolved_sql.strip().upper().startswith('SELECT'):
                    rows = cursor.fetchall()
                    self.variables['__sql_result__'] = rows
                    return {'message': f'查询返回 {len(rows)} 行'}
                return {'message': 'SQL 执行成功'}
        except Exception as e:
            self._log(f"SQL 执行失败: {e}")
            raise

    def _set_variable(self, detail, resolver):
        """设置自定义变量"""
        custom = detail.custom
        if custom and isinstance(custom, dict):
            key = custom.get('key', '')
            value = custom.get('value', '')
            self.variables[key] = resolver.resolve(str(value))
            self._log(f"设置变量: {key} = {self.variables[key]}")
            return {'message': f'变量 {key} 已设置'}
        raise ValueError("自定义变量格式错误")

    async def _execute_condition(self, detail, resolver):
        """执行条件逻辑"""
        condition = detail.condition_value
        if not condition or not isinstance(condition, dict):
            raise ValueError("条件值格式错误")

        var_name = condition.get('variable', '')
        operator = condition.get('operator', '==')
        expected = resolver.resolve(str(condition.get('value', '')))
        actual = self.variables.get(var_name, '')

        ops = {
            '==': lambda a, b: str(a) == str(b),
            '!=': lambda a, b: str(a) != str(b),
            'contains': lambda a, b: str(b) in str(a),
            'not_contains': lambda a, b: str(b) not in str(a),
            '>': lambda a, b: float(a) > float(b),
            '<': lambda a, b: float(a) < float(b),
            '>=': lambda a, b: float(a) >= float(b),
            '<=': lambda a, b: float(a) <= float(b),
        }

        op_fn = ops.get(operator)
        if not op_fn:
            raise ValueError(f"不支持的条件操作: {operator}")

        result = op_fn(actual, expected)
        self._log(f"条件判断: {var_name} {operator} {expected} -> {result}")

        if not result:
            on_fail = condition.get('on_fail', 'skip')
            if on_fail == 'abort':
                raise AssertionError(f"条件断言失败: {var_name} {operator} {expected}")
            # skip: 跳过后续步骤（由调用方处理）

        return {'message': f'条件判断结果: {result}'}

    async def _execute_python(self, detail, resolver):
        """执行 Python 代码片段"""
        func_code = detail.func
        if not func_code:
            raise ValueError("Python 函数代码为空")

        resolved_code = resolver.resolve(func_code)

        # 在受限环境中执行
        safe_globals = {
            '__builtins__': {
                'print': print, 'len': len, 'str': str, 'int': int,
                'float': float, 'list': list, 'dict': dict, 'bool': bool,
                'range': range, 'enumerate': enumerate, 'zip': zip,
                'min': min, 'max': max, 'sum': sum, 'abs': abs,
                'True': True, 'False': False, 'None': None,
            },
            'variables': self.variables,
            'json': json,
        }

        try:
            exec(resolved_code, safe_globals)
            self._log(f"Python 代码执行成功")
            return {'message': 'Python 执行成功'}
        except Exception as e:
            self._log(f"Python 代码执行失败: {e}")
            raise

    async def _load_public_data(self, project_id):
        """加载项目公共变量"""
        from .models import UiPublicData
        public_data = UiPublicData.objects.filter(project_id=project_id, is_enabled=True)
        for item in public_data:
            self.variables[item.key] = item.value
        if public_data.exists():
            self._log(f"加载了 {public_data.count()} 个公共变量")
