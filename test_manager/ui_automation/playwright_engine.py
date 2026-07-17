"""
Playwright 浏览器自动化引擎
"""
import asyncio
import logging
import os
from typing import Optional

logger = logging.getLogger('test_manager.ui_automation')

MEDIA_DIR = os.path.join('media', 'ui_traces')
SCREENSHOT_DIR = os.path.join('media', 'ui_screenshots')


class PlaywrightEngine:
    """
    Playwright 异步浏览器引擎

    提供浏览器生命周期管理和基础操作接口。
    支持 chromium/firefox/webkit 三种浏览器。
    """

    def __init__(self, browser_type='chromium', headless=True,
                 viewport_width=1920, viewport_height=1080, timeout=30):
        self.browser_type = browser_type
        self.headless = headless
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.timeout = timeout * 1000  # 转换为毫秒
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._trace_path = None

    async def start(self):
        """启动浏览器"""
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()

        browser_launcher = getattr(self._playwright, self.browser_type)
        self._browser = await browser_launcher.launch(headless=self.headless)

        self._context = await self._browser.new_context(
            viewport={'width': self.viewport_width, 'height': self.viewport_height},
            ignore_https_errors=True,
        )
        self._context.set_default_timeout(self.timeout)

        self._page = await self._context.new_page()
        logger.info(f"浏览器已启动: {self.browser_type}, headless={self.headless}")

    async def start_trace(self, name='trace'):
        """开始录制 Trace"""
        os.makedirs(MEDIA_DIR, exist_ok=True)
        self._trace_path = os.path.join(MEDIA_DIR, f'{name}.zip')
        await self._context.tracing.start(screenshots=True, snapshots=True, sources=True)

    async def stop_trace(self):
        """停止录制 Trace 并保存"""
        if self._trace_path and self._context:
            await self._context.tracing.stop(path=self._trace_path)
            return self._trace_path
        return None

    async def take_screenshot(self, name='screenshot'):
        """截取屏幕截图"""
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        import uuid
        filename = f"{uuid.uuid4().hex}.png"
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        await self._page.screenshot(path=filepath, full_page=False)
        return f'/media/ui_screenshots/{filename}'

    async def start_video(self):
        """开始录制视频"""
        if self._context:
            video_dir = os.path.join('media', 'ui_videos')
            os.makedirs(video_dir, exist_ok=True)
            # 需要重新创建 context 带 video 配置
            await self._context.close()
            self._context = await self._browser.new_context(
                viewport={'width': self.viewport_width, 'height': self.viewport_height},
                record_video_dir=video_dir,
                record_video_size={'width': self.viewport_width, 'height': self.viewport_height},
                ignore_https_errors=True,
            )
            self._context.set_default_timeout(self.timeout)
            self._page = await self._context.new_page()

    async def stop_video(self):
        """停止录制视频并返回路径"""
        if self._page and self._page.video:
            video = self._page.video
            path = await video.path()
            return path
        return None

    async def close(self):
        """关闭浏览器"""
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.warning(f"关闭浏览器时出错: {e}")

    @property
    def page(self):
        return self._page

    @property
    def context(self):
        return self._context

    # ============================================================
    # 元素定位
    # ============================================================

    async def locate_element(self, locator_type, locator_value, index=0, iframe_locator=None):
        """
        定位元素，支持多种定位策略

        Args:
            locator_type: css/xpath/text/role/label/placeholder/testid/id/name
            locator_value: 定位值
            index: 元素索引（当多个匹配时）
            iframe_locator: iframe 定位器（如果在 iframe 内）

        Returns:
            Playwright Locator 对象
        """
        target = self._page

        # 处理 iframe
        if iframe_locator:
            target = self._page.frame_locator(iframe_locator)

        locator_map = {
            'css': lambda: target.locator(locator_value),
            'xpath': lambda: target.locator(f'xpath={locator_value}'),
            'text': lambda: target.get_by_text(locator_value),
            'role': lambda: target.get_by_role(locator_value),
            'label': lambda: target.get_by_label(locator_value),
            'placeholder': lambda: target.get_by_placeholder(locator_value),
            'testid': lambda: target.get_by_test_id(locator_value),
            'id': lambda: target.locator(f'#{locator_value}'),
            'name': lambda: target.locator(f'[name="{locator_value}"]'),
        }

        locator_fn = locator_map.get(locator_type)
        if not locator_fn:
            raise ValueError(f"不支持的定位类型: {locator_type}")

        locator = locator_fn()

        if index > 0:
            locator = locator.nth(index)

        return locator

    async def locate_with_fallback(self, locators_list, wait_time=5):
        """
        带降级策略的元素定位

        Args:
            locators_list: 定位器列表 [{'type': 'css', 'value': '.btn', 'index': 0}, ...]
            wait_time: 每个定位器的等待时间（秒）

        Returns:
            第一个成功定位的 Locator
        """
        last_error = None
        for loc_info in locators_list:
            try:
                locator = await self.locate_element(
                    loc_info['type'], loc_info['value'], loc_info.get('index', 0)
                )
                await locator.wait_for(state='visible', timeout=wait_time * 1000)
                return locator
            except Exception as e:
                last_error = e
                logger.debug(f"定位器 {loc_info['type']}={loc_info['value']} 失败: {e}")
                continue

        raise TimeoutError(f"所有定位器均失败: {last_error}")

    # ============================================================
    # 元素操作
    # ============================================================

    async def click(self, locator, force=False):
        """点击元素"""
        await locator.click(force=force)

    async def fill(self, locator, value):
        """填充输入框"""
        await locator.fill(value)

    async def type_text(self, locator, text, delay=50):
        """逐字符输入"""
        await locator.press_sequentially(text, delay=delay)

    async def select_option(self, locator, value):
        """下拉选择"""
        await locator.select_option(value)

    async def check(self, locator):
        """勾选复选框"""
        await locator.check()

    async def uncheck(self, locator):
        """取消勾选"""
        await locator.uncheck()

    async def hover(self, locator):
        """悬停"""
        await locator.hover()

    async def get_text(self, locator):
        """获取元素文本"""
        return await locator.text_content()

    async def get_attribute(self, locator, attr):
        """获取元素属性"""
        return await locator.get_attribute(attr)

    async def is_visible(self, locator):
        """检查元素是否可见"""
        return await locator.is_visible()

    async def is_enabled(self, locator):
        """检查元素是否可用"""
        return await locator.is_enabled()

    async def wait_for_element(self, locator, state='visible', timeout=10000):
        """等待元素状态"""
        await locator.wait_for(state=state, timeout=timeout)

    async def upload_file(self, locator, file_path):
        """上传文件"""
        await locator.set_input_files(file_path)

    async def press_key(self, key):
        """按键操作"""
        await self._page.keyboard.press(key)

    async def navigate(self, url):
        """页面导航"""
        await self._page.goto(url, wait_until='domcontentloaded')

    async def wait_for_navigation(self, timeout=30000):
        """等待页面导航完成"""
        await self._page.wait_for_load_state('networkidle', timeout=timeout)

    async def execute_js(self, script):
        """执行 JavaScript"""
        return await self._page.evaluate(script)

    async def switch_to_frame(self, frame_locator):
        """切换到 iframe"""
        return self._page.frame_locator(frame_locator)

    async def switch_to_default(self):
        """切换回主文档"""
        return self._page
