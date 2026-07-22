# -*- coding: utf-8 -*-
"""
APP 自动化 — 独立变量替换器

支持 ${function_name(args)} 格式的变量表达式。
内置常用函数：random_int, random_string, random_uuid, timestamp, datetime 等。
"""
import re
import uuid
import time
import random
import string
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def resolve_variables(text):
    """
    解析文本中的变量表达式，将 ${func(args)} 替换为执行结果。

    Args:
        text: 包含变量表达式的文本

    Returns:
        解析后的文本
    """
    if not text or not isinstance(text, str):
        return text

    pattern = re.compile(r'\$\{([^}]+)\}')

    def _replace(match):
        expr = match.group(1).strip()
        try:
            return str(_evaluate(expr))
        except Exception as e:
            logger.warning(f"变量解析失败: {expr} -> {e}")
            return match.group(0)

    return pattern.sub(_replace, text)


def _evaluate(expr):
    """解析并执行单个表达式"""
    # 尝试匹配 function_name(args) 格式
    m = re.match(r'^(\w+)\((.*)\)$', expr, re.DOTALL)
    if not m:
        # 无参数的简单常量或函数
        return _call_function(expr.strip(), [])

    func_name = m.group(1)
    raw_args = m.group(2).strip()
    args = _parse_args(raw_args) if raw_args else []
    return _call_function(func_name, args)


def _parse_args(raw):
    """解析参数列表，支持引号字符串、数字、布尔值"""
    args = []
    current = ''
    in_quote = None
    depth = 0

    for ch in raw:
        if ch in ('"', "'") and depth == 0:
            if in_quote == ch:
                in_quote = None
            elif in_quote is None:
                in_quote = ch
            current += ch
        elif ch == '[':
            depth += 1
            current += ch
        elif ch == ']':
            depth -= 1
            current += ch
        elif ch == ',' and in_quote is None and depth == 0:
            args.append(_convert_arg(current.strip()))
            current = ''
        else:
            current += ch

    if current.strip():
        args.append(_convert_arg(current.strip()))
    return args


def _convert_arg(val):
    """将字符串参数转换为适当的 Python 类型"""
    if not isinstance(val, str):
        return val
    # 去除引号
    if (val.startswith('"') and val.endswith('"')) or \
       (val.startswith("'") and val.endswith("'")):
        return val[1:-1]
    if val.lower() == 'true':
        return True
    if val.lower() == 'false':
        return False
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val


# ==================================================================
# 内置函数注册表
# ==================================================================

_FUNCTIONS = {}


def _register(name):
    """装饰器：注册一个内置函数"""
    def decorator(fn):
        _FUNCTIONS[name] = fn
        return fn
    return decorator


def _call_function(name, args):
    """调用已注册的函数"""
    fn = _FUNCTIONS.get(name)
    if fn:
        return fn(*args)
    raise ValueError(f"未知函数: {name}")


# ---- 随机函数 ----

@_register('random_int')
def _random_int(min_val=0, max_val=9999):
    return random.randint(int(min_val), int(max_val))


@_register('random_string')
def _random_string(length=8):
    length = int(length)
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


@_register('random_uuid')
def _random_uuid():
    return str(uuid.uuid4())


@_register('random_phone')
def _random_phone():
    prefixes = ['138', '139', '136', '137', '135', '158', '159', '188', '187', '186']
    return random.choice(prefixes) + ''.join(random.choices(string.digits, k=8))


@_register('random_email')
def _random_email():
    user = ''.join(random.choices(string.ascii_lowercase, k=8))
    domains = ['gmail.com', 'qq.com', '163.com', 'outlook.com', 'test.com']
    return f"{user}@{random.choice(domains)}"


@_register('random_date')
def _random_date(start_year=2020, end_year=2025):
    start = datetime(int(start_year), 1, 1)
    end = datetime(int(end_year), 12, 31)
    delta = (end - start).days
    d = start + timedelta(days=random.randint(0, max(delta, 1)))
    return d.strftime('%Y-%m-%d')


# ---- 时间函数 ----

@_register('timestamp')
def _timestamp():
    return int(time.time())


@_register('datetime')
def _datetime(fmt='%Y-%m-%d %H:%M:%S'):
    if isinstance(fmt, str) and fmt:
        return datetime.now().strftime(fmt)
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


@_register('date')
def _date(fmt='%Y-%m-%d'):
    if isinstance(fmt, str) and fmt:
        return datetime.now().strftime(fmt)
    return datetime.now().strftime('%Y-%m-%d')


@_register('time')
def _time(fmt='%H:%M:%S'):
    if isinstance(fmt, str) and fmt:
        return datetime.now().strftime(fmt)
    return datetime.now().strftime('%H:%M:%S')


# ---- 编码函数 ----

@_register('base64_encode')
def _base64_encode(text=''):
    import base64
    return base64.b64encode(str(text).encode('utf-8')).decode('utf-8')


@_register('url_encode')
def _url_encode(text=''):
    from urllib.parse import quote
    return quote(str(text))


@_register('md5')
def _md5(text=''):
    import hashlib
    return hashlib.md5(str(text).encode('utf-8')).hexdigest()


@_register('sha256')
def _sha256(text=''):
    import hashlib
    return hashlib.sha256(str(text).encode('utf-8')).hexdigest()
