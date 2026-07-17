"""
变量解析器 - 将字符串中的 {{variable}} 占位符替换为实际值
"""
import re
import logging

logger = logging.getLogger('test_manager.ui_automation')


class VariableResolver:
    """
    变量解析器

    支持 {{key}} 格式的变量替换。
    内置变量：
    - {{timestamp}}: 当前时间戳
    - {{random_int}}: 随机整数
    - {{random_str}}: 随机字符串
    - {{uuid}}: UUID
    """

    VAR_PATTERN = re.compile(r'\{\{(\w+)\}\}')

    BUILT_IN_VARS = {
        'timestamp': lambda: str(int(__import__('time').time())),
        'random_int': lambda: str(__import__('random').randint(1000, 9999)),
        'random_str': lambda: __import__('random').choice('abcdefghijklmnopqrstuvwxyz') * 8,
        'uuid': lambda: __import__('uuid').uuid4().hex,
        'date': lambda: __import__('datetime').datetime.now().strftime('%Y-%m-%d'),
        'datetime': lambda: __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }

    def __init__(self, variables=None):
        """
        Args:
            variables: 初始变量字典
        """
        self.variables = variables or {}

    def set(self, key, value):
        """设置变量"""
        self.variables[key] = value

    def get(self, key, default=''):
        """获取变量"""
        return self.variables.get(key, default)

    def resolve(self, text):
        """
        解析文本中的所有变量占位符

        Args:
            text: 包含 {{variable}} 占位符的字符串

        Returns:
            替换后的字符串
        """
        if not text or not isinstance(text, str):
            return text

        def replace_var(match):
            var_name = match.group(1)
            # 优先查找用户变量
            if var_name in self.variables:
                return str(self.variables[var_name])
            # 其次查找内置变量
            if var_name in self.BUILT_IN_VARS:
                return self.BUILT_IN_VARS[var_name]()
            # 未找到则保留原样并记录警告
            logger.warning(f"变量未定义: {var_name}")
            return match.group(0)

        return self.VAR_PATTERN.sub(replace_var, text)

    def resolve_dict(self, data):
        """解析字典中所有字符串值"""
        if not isinstance(data, dict):
            return data
        result = {}
        for k, v in data.items():
            if isinstance(v, str):
                result[k] = self.resolve(v)
            elif isinstance(v, dict):
                result[k] = self.resolve_dict(v)
            elif isinstance(v, list):
                result[k] = [self.resolve(item) if isinstance(item, str) else item for item in v]
            else:
                result[k] = v
        return result
