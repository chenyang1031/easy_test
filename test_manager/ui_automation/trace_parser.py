"""
Playwright Trace 解析器

解析 Playwright 生成的 .zip trace 文件，提取操作步骤和截图信息。
"""
import json
import logging
import os
import zipfile
from typing import Optional

logger = logging.getLogger('test_manager.ui_automation')


class TraceParser:
    """
    Playwright Trace 文件解析器

    Trace 文件是一个 ZIP 包，包含:
    - trace.trace: JSON Lines 格式的操作记录
    - resources/: 截图和其他资源文件
    """

    def __init__(self, trace_path):
        """
        Args:
            trace_path: trace .zip 文件路径
        """
        self.trace_path = trace_path
        self._events = []
        self._screenshots = []
        self._actions = []

    def parse(self):
        """
        解析 trace 文件

        Returns:
            dict: {actions: [...], screenshots: [...], metadata: {...}}
        """
        if not os.path.exists(self.trace_path):
            logger.error(f"Trace 文件不存在: {self.trace_path}")
            return {'actions': [], 'screenshots': [], 'metadata': {}}

        try:
            with zipfile.ZipFile(self.trace_path, 'r') as zf:
                # 读取 trace 数据
                trace_files = [f for f in zf.namelist() if f.endswith('.trace')]
                for trace_file in trace_files:
                    content = zf.read(trace_file).decode('utf-8')
                    for line in content.strip().split('\n'):
                        if line.strip():
                            try:
                                event = json.loads(line)
                                self._process_event(event)
                            except json.JSONDecodeError:
                                continue

                # 提取截图列表
                screenshot_files = [
                    f for f in zf.namelist()
                    if f.startswith('resources/') and f.endswith('.png')
                ]
                for sf in screenshot_files:
                    self._screenshots.append({
                        'filename': os.path.basename(sf),
                        'path': sf,
                    })

            return {
                'actions': self._actions,
                'screenshots': self._screenshots,
                'metadata': {
                    'total_actions': len(self._actions),
                    'total_screenshots': len(self._screenshots),
                    'trace_file': os.path.basename(self.trace_path),
                },
            }

        except zipfile.BadZipFile:
            logger.error(f"无效的 ZIP 文件: {self.trace_path}")
            return {'actions': [], 'screenshots': [], 'metadata': {'error': '无效的 trace 文件'}}
        except Exception as e:
            logger.exception(f"解析 trace 失败: {e}")
            return {'actions': [], 'screenshots': [], 'metadata': {'error': str(e)}}

    def _process_event(self, event):
        """处理单个 trace 事件"""
        event_type = event.get('type', '')

        if event_type == 'action':
            action = {
                'name': event.get('apiName', event.get('method', '')),
                'selector': event.get('params', {}).get('selector', ''),
                'url': event.get('params', {}).get('url', ''),
                'start_time': event.get('startTime', 0),
                'end_time': event.get('endTime', 0),
                'error': event.get('error', None),
                'log': event.get('log', []),
                'type': 'action',
            }
            # 计算耗时
            if action['start_time'] and action['end_time']:
                action['duration'] = action['end_time'] - action['start_time']
            else:
                action['duration'] = 0

            self._actions.append(action)

        elif event_type == 'navigation':
            self._actions.append({
                'name': 'navigation',
                'url': event.get('url', ''),
                'start_time': event.get('timestamp', 0),
                'type': 'navigation',
                'duration': 0,
            })

        elif event_type == 'screenshot':
            self._screenshots.append({
                'filename': event.get('name', ''),
                'timestamp': event.get('timestamp', 0),
            })

    def extract_screenshot(self, screenshot_filename, output_dir):
        """
        从 trace 中提取指定截图

        Args:
            screenshot_filename: 截图文件名
            output_dir: 输出目录

        Returns:
            截图文件路径
        """
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, screenshot_filename)

        if os.path.exists(output_path):
            return output_path

        try:
            with zipfile.ZipFile(self.trace_path, 'r') as zf:
                for name in zf.namelist():
                    if name.endswith(screenshot_filename):
                        data = zf.read(name)
                        with open(output_path, 'wb') as f:
                            f.write(data)
                        return output_path
        except Exception as e:
            logger.error(f"提取截图失败: {e}")

        return None

    def get_summary(self):
        """获取 trace 摘要信息"""
        if not self._actions:
            self.parse()

        total_duration = sum(a.get('duration', 0) for a in self._actions)
        error_count = sum(1 for a in self._actions if a.get('error'))
        navigation_count = sum(1 for a in self._actions if a.get('type') == 'navigation')

        return {
            'total_actions': len(self._actions),
            'total_screenshots': len(self._screenshots),
            'total_duration_ms': total_duration,
            'error_count': error_count,
            'navigation_count': navigation_count,
            'success': error_count == 0,
        }


def parse_trace_file(trace_path):
    """便捷函数：解析 trace 文件并返回结果"""
    parser = TraceParser(trace_path)
    return parser.parse()
