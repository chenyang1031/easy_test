import json
import time
import logging
import requests
import re
import mimetypes
import os
import base64
from requests_toolbelt.multipart.encoder import MultipartEncoder
from urllib.parse import urljoin
from jsonpath_ng import jsonpath, parse
import sys

from django.core.files.storage import default_storage
from EasyTesting import settings
from test_manager.env_variables_compat import variables_for_runtime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import debugtalk as dt
except ImportError:
    dt = None

# 新增：通用断言映射表
ASSERT_MAP = {
    "eq": lambda a, e: str(a) == str(e),   # 弱类型相等
    "ne": lambda a, e: a != e,
    "gt": lambda a, e: a is not None and float(a) > float(e),
    "ge": lambda a, e: a is not None and float(a) >= float(e),
    "lt": lambda a, e: a is not None and float(a) < float(e),
    "le": lambda a, e: a is not None and float(a) <= float(e),
    "contains": lambda a, e: str(e) in str(a),
    "notcontains": lambda a, e: str(e) not in str(a),
    "startswith": lambda a, e: str(a).startswith(str(e)),
    "endswith": lambda a, e: str(a).endswith(str(e)),
    "regex_match": lambda a, e: bool(re.search(str(e), str(a))),
    "length_eq": lambda a, e: len(str(a)) == int(e),
    "length_gt": lambda a, e: len(str(a)) > int(e),
    "length_ge": lambda a, e: len(str(a)) >= int(e),
    "length_lt": lambda a, e: len(str(a)) < int(e),
    "length_le": lambda a, e: len(str(a)) <= int(e),
}

# ---------- 1. 把 debugtalk 函数挂到变量池 ----------
if dt is not None:
    # 只挂可调用函数，避免挂常量
    _funcs = {name: getattr(dt, name) for name in dir(dt)
              if callable(getattr(dt, name)) and not name.startswith('_')}
else:
    _funcs = {}


def _json_body_utf8_bytes(obj):
    """将对象序列化为 JSON 后以 UTF-8 编码（ensure_ascii=False，线路上为汉字明文字节，便于与签名字符串一致）。"""
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


def _set_request_json_utf8(kwargs, headers, body_obj):
    """使用 data 发送 UTF-8 明文 JSON；避免 requests 的 json= 使用默认 ensure_ascii=True 产生 \\uXXXX。"""
    kwargs["data"] = _json_body_utf8_bytes(body_obj)
    if "Content-Type" not in headers:
        kwargs["headers"]["Content-Type"] = "application/json; charset=utf-8"


def _json_dumps_utf8_for_log(obj):
    """调试日志：JSON 明文字符串（不转义汉字为 \\uXXXX）。"""
    try:
        return json.dumps(obj, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(obj)


def get_debugtalk_functions():
    """返回 debugtalk 可调用函数字典，供场景引擎变量池注入。"""
    exclude = {"datetime", "timedelta"}
    return {k: v for k, v in _funcs.items() if k not in exclude}


def get_debugtalk_functions_meta():
    """返回 debugtalk 函数元信息列表 [{name, doc}]，供 API 与文档展示。"""
    # 排除标准库导入（如 datetime、timedelta），仅展示自定义函数
    exclude = {"datetime", "timedelta"}
    result = []
    for name, fn in _funcs.items():
        if name in exclude:
            continue
        doc = (getattr(fn, "__doc__") or "").strip()
        result.append({"name": name, "doc": doc})
    return result


def _is_multipart_content_type(ct):
    """判断 Content-Type 是否为合法的 multipart 开头。"""
    if not ct or not isinstance(ct, str):
        return False
    return str(ct).strip().lower().startswith("multipart/")


def _validate_file_param(key, value):
    """
    校验单个 file 参数：存在性、大小、信息完整性。
    无效时抛出 FileParamValidationError。
    """
    if not isinstance(value, dict) or value.get("type") != "File":
        return
    file_path = value.get("file_path") or value.get("file_url")
    file_name = value.get("file_name")
    if not file_path or not str(file_path).strip():
        raise FileParamValidationError(f"文件参数「{key}」缺少 file_path 或 file_url")
    try:
        abs_path = default_storage.path(file_path)
    except Exception as e:
        raise FileParamValidationError(f"文件参数「{key}」路径无效: {file_path}，错误: {e}")
    if not os.path.exists(abs_path):
        raise FileParamValidationError(f"文件参数「{key}」文件不存在: {file_path}")
    try:
        size = os.path.getsize(abs_path)
    except OSError as e:
        raise FileParamValidationError(f"文件参数「{key}」无法读取大小: {e}")
    if size > FILE_UPLOAD_MAX_SIZE:
        raise FileParamValidationError(
            f"文件参数「{key}」大小 {size} 字节超过限制 {FILE_UPLOAD_MAX_SIZE} 字节"
        )
    if not file_name or not str(file_name).strip():
        value["file_name"] = os.path.basename(file_path) if file_path else "file"


def _assert_value(comparator, actual, expected):
    """统一断言入口"""
    func = ASSERT_MAP.get(comparator)
    if not func:
        raise ValueError(f"Unsupported comparator: {comparator}")
    try:
        return func(actual, expected)
    except Exception as e:
        logger.error(f"Assertion error: {e}")
        return False

# 尝试导入 HTTPRunner，如果失败则记录错误但不中断执行
try:
    import httprunner

    # 尝试多种方式获取 HTTPRunner 版本
    if hasattr(httprunner, "__version__"):
        HTTPRUNNER_VERSION = httprunner.__version__
    elif hasattr(httprunner, "__version"):
        HTTPRUNNER_VERSION = httprunner.__version
    elif hasattr(httprunner, "version"):
        HTTPRUNNER_VERSION = httprunner.version
    else:
        # 尝试从包信息获取版本
        try:
            import pkg_resources

            HTTPRUNNER_VERSION = pkg_resources.get_distribution("httprunner").version
        except:
            HTTPRUNNER_VERSION = "unknown"

    # 尝试导入 HttpRunner 类
    try:
        from httprunner.runner import HttpRunner

        HTTPRUNNER_AVAILABLE = True
    except ImportError:
        # 尝试其他可能的导入路径
        try:
            from httprunner.api import HttpRunner

            HTTPRUNNER_AVAILABLE = True
        except ImportError:
            HTTPRUNNER_AVAILABLE = False
except ImportError:
    HTTPRUNNER_AVAILABLE = False
    HTTPRUNNER_VERSION = "not installed"

logger = logging.getLogger(__name__)
logger.info(f"HTTPRunner version: {HTTPRUNNER_VERSION}, Available: {HTTPRUNNER_AVAILABLE}")

# 文件上传大小限制（字节），默认 50MB
FILE_UPLOAD_MAX_SIZE = getattr(settings, "FILE_UPLOAD_MAX_SIZE", 50 * 1024 * 1024)


class FileParamValidationError(Exception):
    """文件参数校验失败的业务异常，包含明确错误信息。"""

    pass


def replace_variables(content, variables):
    """
    替换内容中的变量引用
    支持格式: ${variable_name} 或 $variable_name

    Args:
        content: 需要替换变量的内容，可以是字符串、字典、列表或其他基本类型
        variables: 变量字典，键为变量名，值为变量值

    Returns:
        替换变量后的内容
    """
    if not variables or variables is None:
        return content

    # 如果内容为None，直接返回None
    if content is None:
        return None

    # 处理字典类型
    if isinstance(content, dict):
        return {k: replace_variables(v, variables) for k, v in content.items()}

    # 处理列表类型
    elif isinstance(content, list):
        return [replace_variables(item, variables) for item in content]

    # 处理字符串类型
    elif isinstance(content, str):
        # 首先替换 ${variable} 格式的变量
        result = content

        # 使用正则表达式查找所有 ${variable} 格式的变量
        pattern = r'\${([a-zA-Z0-9_]+)}'

        # 查找所有匹配项
        for match in re.finditer(pattern, content):
            var_name = match.group(1)
            if var_name in variables:
                # 获取变量值并转换为字符串
                var_value = variables[var_name]
                if var_value is None:
                    var_value = ""
                elif not isinstance(var_value, str):
                    var_value = str(var_value)

                # 替换变量
                placeholder = f'${{{var_name}}}'
                result = result.replace(placeholder, var_value)

        # 然后替换 $variable 格式的变量
        # 使用更简单的方法，避免使用可变宽度的后向查找
        words = re.findall(r'\$([a-zA-Z0-9_]+)', result)
        for word in words:
            # 检查是否是变量名
            if word in variables:
                # 确保不是已经处理过的 ${var} 格式
                placeholder = f'${word}'
                if f'${{{word}}}' not in content:  # 避免替换已经处理过的 ${var} 格式
                    # 获取变量值并转换为字符串
                    var_value = variables[word]
                    if var_value is None:
                        var_value = ""
                    elif not isinstance(var_value, str):
                        var_value = str(var_value)

                    # 替换变量
                    result = result.replace(placeholder, var_value)

        # ---------- 2. 支持 ${func()} 语法 ----------
        # 1) ${func()}  -> 直接调用挂进来的函数
        pattern_func = r'\$\{([a-zA-Z0-9_]+)\(\)\}'
        for m in re.finditer(pattern_func, result):
            func_name = m.group(1)
            if func_name in _funcs:
                # 执行函数并把结果转字符串
                val = str(_funcs[func_name]())
                result = result.replace(m.group(0), val)

        # 2) ${var}      -> 普通变量（已存在逻辑）
        # 3) $var        -> 普通变量（已存在逻辑）
        return result

    # 处理其他类型（数字、布尔值等），直接返回原值
    else:
        return content



def _is_file_download(response):
    """检测 HTTP 响应是否为文件下载。

    判定条件（任一满足即为文件下载）：
    1. Content-Disposition 包含 attachment
    2. Content-Type 非 JSON/纯文本且非空白（如 application/octet-stream, application/zip 等）
    3. response.json() 失败且 Content-Type 含 application/ 但不含 json
    """
    content_type = (response.headers.get("Content-Type") or "").lower()
    content_disposition = (response.headers.get("Content-Disposition") or "").lower()

    # 条件1: Content-Disposition 明确标记为附件
    if "attachment" in content_disposition:
        return True

    # 条件2: 明确为二进制下载类型
    binary_markers = [
        "application/octet-stream", "application/zip", "application/gzip",
        "application/x-tar", "application/x-rar-compressed",
        "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument",
        "application/pdf",
    ]
    for marker in binary_markers:
        if marker in content_type:
            return True

    # 条件3: 非 JSON 响应（response.json() 失败）且不是纯文本
    if not content_type:
        return False  # 无 Content-Type，按原有 JSON/text 逻辑处理
    if any(t in content_type for t in ("application/json", "text/", "application/xml", "text/xml")):
        return False

    # 其他 application/* 非 JSON 类型 → 视为下载
    if content_type.startswith("application/"):
        return True

    return False


def execute_test_case(test_case, environment, variables=None):
    """
    Execute a single test case using direct HTTP request

    Args:
        test_case: TestCase object
        environment: Environment object
        variables: Dict of variables to use for parameter substitution
    """
    try:
        # 初始化变量字典
        if variables is None:
            variables = {}
        else:
            # 创建一个副本，避免修改原始变量字典
            variables = variables.copy()
            # ---------- 3. 把函数和提取变量一起塞进变量池 ----------
            # 1) 先挂 debugtalk 函数
            variables.update(_funcs)
            # 2) 再合并环境变量（已有）

        # 合并环境变量
        if hasattr(environment, 'variables') and environment.variables:
            try:
                env_vars = environment.variables
                if isinstance(env_vars, str):
                    env_vars = json.loads(env_vars)
                variables.update(variables_for_runtime(env_vars))
            except Exception as e:
                logger.error(f"Error merging environment variables: {e}")

        # 记录测试开始信息
        logger.info(
            f"Executing test case: {test_case.name} (ID: {test_case.id}) with environment: {environment.name} (ID: {environment.id})")
        logger.info(
            f"Request method: {test_case.request_method}, URL: {test_case.request_url}, Body format: {test_case.request_body_format}")

        # 记录使用的变量
        if variables:
            logger.info(f"Using variables: {variables}")

        start_time = time.time()

        # 直接使用 HTTP 请求执行测试
        result = _execute_with_requests(test_case, environment, variables)

        # 计算响应时间
        end_time = time.time()
        result["response_time"] = (end_time - start_time) * 1000  # 转换为毫秒

        # 在处理响应后，添加参数提取逻辑
        try:
            extracted_params = {}
            if hasattr(test_case, 'extract_params') and test_case.extract_params:
                try:
                    response_body = result['response_body']

                    # 确保响应体是JSON格式
                    if isinstance(response_body, str):
                        try:
                            response_json = json.loads(response_body)
                        except json.JSONDecodeError:
                            # 如果不是JSON，则使用文本响应
                            response_json = {"content": response_body}
                    else:
                        response_json = response_body

                    # 遍历需要提取的参数
                    for extract in test_case.extract_params:
                        try:
                            # 确保extract是字典格式
                            if isinstance(extract, str):
                                try:
                                    extract = json.loads(extract)
                                except json.JSONDecodeError:
                                    logger.error(f"Invalid extract parameter format: {extract}")
                                    continue

                            # 获取参数名和路径
                            param_name = extract.get('name')
                            param_path = extract.get('path')

                            if not param_name or not param_path:
                                logger.error(f"Invalid extract parameter: {extract}")
                                continue

                            # 使用JSONPath提取参数
                            jsonpath_expr = parse(param_path)
                            matches = [match.value for match in jsonpath_expr.find(response_json)]

                            if matches:
                                # 只取第一个匹配结果
                                extracted_params[param_name] = matches[0]
                                logger.info(f"Extracted parameter {param_name} = {matches[0]}")
                        except Exception as e:
                            # 处理提取错误
                            logger.error(
                                f"Error extracting parameter {extract.get('name', 'unknown')} using JSONPath {extract.get('path', 'unknown')}: {e}")
                except Exception as e:
                    # 处理 JSON 解析错误
                    logger.error(f"Error parsing response body for parameter extraction: {e}")

            # 将提取的参数添加到结果中
            result['extracted_params'] = extracted_params
        except Exception as e:
            logger.error(f"Error in parameter extraction process: {e}")
            result['extracted_params'] = {}

        return result

    except Exception as e:
        logger.exception(f"Error executing test case: {e}")
        return {
            "status": "error",
            "request_headers": {},
            "request_body": {},
            "response_time": 0,
            "response_status_code": None,
            "response_headers": {},
            "response_body": {},
            "error_message": str(e),
            "extracted_params": {},
            "is_file_download": False,
            "raw_response_body_b64": None,
        }


def _execute_with_requests(test_case, environment, variables=None):
    """
    Execute test case using direct HTTP requests

    Args:
        test_case: TestCase object
        environment: Environment object
        variables: Dict of variables to use for parameter substitution
    """
    try:
        # 构建完整 URL，并替换变量
        base_url = environment.base_url.rstrip('/')

        # 替换URL中的变量
        request_url = test_case.request_url
        if request_url:
            request_url = request_url.lstrip('/')
            request_url = replace_variables(request_url, variables)
        else:
            request_url = ""

        full_url = f"{base_url}/{request_url}"
        logger.info(f"Full URL after variable replacement: {full_url}")

        # 准备请求参数
        headers = {}
        if hasattr(test_case, 'request_headers') and test_case.request_headers:
            if isinstance(test_case.request_headers, str):
                try:
                    headers = json.loads(test_case.request_headers)
                except json.JSONDecodeError:
                    logger.error(f"Invalid headers format: {test_case.request_headers}")
            else:
                headers = test_case.request_headers.copy()

        # 替换请求头中的变量
        headers = replace_variables(headers, variables)

        timeout = test_case.timeout or 30

        kwargs = {
            "headers": headers,
            "timeout": timeout
        }

        # 保存原始请求头和请求体，用于结果记录
        original_headers = headers.copy()
        original_body = None
        request_body = None

        # 根据请求体格式处理请求数据
        if hasattr(test_case, 'request_body') and test_case.request_body and test_case.request_method in ['POST', 'PUT',
                                                                                                          'PATCH']:
            request_body = test_case.request_body

            # 如果请求体是字符串，尝试解析为JSON
            if isinstance(request_body, str):
                try:
                    request_body = json.loads(request_body)
                except json.JSONDecodeError:
                    # 如果不是JSON，保持原样
                    pass

            # 保存原始请求体（替换变量前）
            original_body = request_body

            # 替换请求体中的变量
            request_body = replace_variables(request_body, variables)
            print(f"##Request body after variable replacement: {request_body}")

            # 根据请求体格式设置请求参数
            if hasattr(test_case, 'request_body_format'):
                if test_case.request_body_format == 'json':
                    # 如果请求体是字典，直接使用
                    if isinstance(request_body, dict) or isinstance(request_body, list):
                        _set_request_json_utf8(kwargs, headers, request_body)
                    else:
                        # 否则尝试解析为JSON
                        try:
                            parsed = json.loads(request_body) if isinstance(request_body, str) else request_body
                        except json.JSONDecodeError:
                            kwargs["data"] = request_body
                        else:
                            if isinstance(parsed, (dict, list)):
                                _set_request_json_utf8(kwargs, headers, parsed)
                            else:
                                kwargs["data"] = _json_body_utf8_bytes(parsed)
                                if "Content-Type" not in headers:
                                    kwargs["headers"]["Content-Type"] = "application/json; charset=utf-8"

                    logger.debug(f"Request body (JSON): {_json_dumps_utf8_for_log(request_body)}")
                elif test_case.request_body_format == 'form-data':
                    multipart_fields = {}

                    # 处理上传的文件（优先使用upload_file字段）
                    if test_case.upload_file and test_case.upload_field_name:
                        file_path = test_case.upload_file.path  # 绝对路径
                        if os.path.exists(file_path):
                            multipart_fields[test_case.upload_field_name] = (
                                os.path.basename(file_path),  # 文件原始名称
                                open(file_path, 'rb'),
                                mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
                            )
                            logger.info(f"Added file to multipart: {test_case.upload_field_name}={file_path}")
                        else:
                            logger.warning(f"File not found: {file_path}")

                    # 处理 request_body 中的多 file 参数及其他 form-data 字段
                    if isinstance(request_body, dict):
                        for key, value in request_body.items():
                            if isinstance(value, dict) and value.get('type') == 'File':
                                _validate_file_param(key, value)
                                file_path = value.get('file_path') or value.get('file_url')
                                file_name = value.get('file_name') or (file_path.split('/')[-1] if file_path else 'file')
                                if file_path and key not in multipart_fields:
                                    abs_path = default_storage.path(file_path)
                                    multipart_fields[key] = (
                                        file_name,
                                        open(abs_path, 'rb'),
                                        mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
                                    )
                                    logger.info(f"Added file from storage: {key}={file_path}")
                            elif key != test_case.upload_field_name:  # 避免覆盖已处理的文件字段
                                multipart_fields[key] = str(value)
                    else:
                        try:
                            form_data = json.loads(request_body) if request_body else {}
                            for key, value in form_data.items():
                                if not (isinstance(value, dict) and value.get('type') == 'File'):
                                    multipart_fields[key] = str(value)
                        except json.JSONDecodeError:
                            logger.error("Invalid form-data JSON format")

                    # 将 multipart_fields 加入请求
                    if multipart_fields:
                        # 记录 multipart 字段详情，便于排查文件上传问题
                        for field_name, field_val in multipart_fields.items():
                            if isinstance(field_val, tuple) and len(field_val) >= 2:
                                fname = field_val[0] if field_val[0] else "(no filename)"
                                fsize = None
                                if hasattr(field_val[1], 'seek') and hasattr(field_val[1], 'tell'):
                                    pos = field_val[1].tell()
                                    field_val[1].seek(0, 2)
                                    fsize = field_val[1].tell()
                                    field_val[1].seek(pos)
                                logger.info(f"Multipart file field: name={field_name}, filename={fname}, size={fsize} bytes")
                            else:
                                logger.debug(f"Multipart text field: name={field_name}, value={str(field_val)[:100]}")
                        encoder = MultipartEncoder(fields=multipart_fields)
                        kwargs['data'] = encoder
                        # 始终使用 encoder 生成的 Content-Type（含正确 boundary），
                        # 不能用用户手动配置的 boundary，否则 body 和 header 不匹配
                        kwargs['headers']['Content-Type'] = encoder.content_type
            else:
                # 默认使用JSON格式
                if isinstance(request_body, dict) or isinstance(request_body, list):
                    _set_request_json_utf8(kwargs, headers, request_body)
                else:
                    try:
                        parsed = json.loads(request_body) if isinstance(request_body, str) else request_body
                    except json.JSONDecodeError:
                        kwargs["data"] = request_body
                    else:
                        if isinstance(parsed, (dict, list)):
                            _set_request_json_utf8(kwargs, headers, parsed)
                        else:
                            kwargs["data"] = _json_body_utf8_bytes(parsed)
                            if "Content-Type" not in headers:
                                kwargs["headers"]["Content-Type"] = "application/json; charset=utf-8"

                logger.debug(f"Request body (default JSON): {_json_dumps_utf8_for_log(request_body)}")

        # 发送请求
        logger.debug(f"Request method: {test_case.request_method}, Headers: {kwargs['headers']}")
        try:
            response = requests.request(
                method=test_case.request_method,
                url=full_url,
                **kwargs
            )
        finally:
            # 关闭 MultipartEncoder 里的文件句柄
            if test_case.request_body_format == 'form-data' and 'data' in kwargs:
                data = kwargs['data']
                if hasattr(data, 'fields'):
                    for name, file_tuple in data.fields.items():
                        if isinstance(file_tuple, tuple) and hasattr(file_tuple[1], 'close'):
                            file_tuple[1].close()

        # 处理响应
        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response headers: {dict(response.headers)}")

        is_download = False
        raw_response_b64 = None
        response_body = {}

        try:
            response_body = response.json()
            logger.debug("Response body parsed as JSON")
        except ValueError:
            # JSON 解析失败 → 可能为文件下载或纯文本
            if _is_file_download(response):
                is_download = True
                content_length = len(response.content)
                max_size = getattr(settings, 'SCENE_DOWNLOAD_MAX_SIZE', 50 * 1024 * 1024)
                if content_length <= max_size:
                    raw_response_b64 = base64.b64encode(response.content).decode('ascii')
                else:
                    logger.warning("File download too large (%d bytes), skipping base64 encoding", content_length)
                # response_body 仍保留文本摘要，供非文件类展示兼容
                response_body = {"content": response.text, "is_file_download": True}
                logger.debug("Response body identified as file download")
            else:
                response_body = {"content": response.text}
                logger.debug("Response body parsed as text")

        # 检查状态码是否符合预期
        success = response.status_code == test_case.expected_status_code

        # 验证其他规则
        validation_errors = []
        validators = []

        if hasattr(test_case, 'validation_rules') and test_case.validation_rules:
            try:
                validation_rules = json.loads(test_case.validation_rules) if isinstance(test_case.validation_rules,
                                                                                        str) else test_case.validation_rules
            except json.JSONDecodeError:
                validation_rules = []

            for rule in validation_rules:
                if not rule:  # 空规则直接跳过
                    continue

                # 兼容多种格式：
                #   标准: {"eq": ["$.data.id", 200]}
               #   AI:   {path: "$.code", comparator: "eq", expected: 200}
                #   原始:  {validator: "eq", path: "$.code", expected: 200, checked: true}
                keys = list(rule.keys())
                first_val = rule[keys[0]]
                if isinstance(first_val, list) and len(first_val) >= 2:
                    # 标准格式: {"eq": ["$.data.id", 200]}
                    comparator = keys[0].lower()
                    path, expected = first_val[0], first_val[1]
                elif "comparator" in rule or "validator" in rule:
                    # AI格式 {path, comparator, expected} 或 原始 {validator, path, expected}
                    comparator = (rule.get("comparator") or rule.get("validator") or "").lower()
                    path = rule.get("path", "")
                    expected = rule.get("expected", "")
                else:
                    # 兜底：取第一个key作为comparator
                    comparator = keys[0].lower()
                    if isinstance(first_val, (list, tuple)) and len(first_val) >= 2:
                        path, expected = first_val[0], first_val[1]
                    else:
                        # 格式不合法，跳过
                        continue

                if not comparator or not isinstance(path, str) or not path:
                    continue

                # 替换预期值里的变量
                expected = replace_variables(expected, variables)

                # 取出 actual 值
                if path == "status_code":
                    actual = response.status_code
                elif path.startswith("$."):
                    try:
                        matches = list(parse(path).find(response_body))
                        actual = matches[0].value if matches else None
                    except Exception as e:
                        logger.error(f"JSONPath error: {e}")
                        actual = None
                else:
                    actual = response.text if path in ("content", "text") else None

                # 执行断言
                passed = _assert_value(comparator, actual, expected)
                logger.info(f"=== ASSERT === comparator={comparator}, path={path}")
                logger.info(f"=== EXPECT (after replace) = {expected!r} | ACTUAL = {actual!r}")
                validators.append({
                    "check": path,
                    "comparator": comparator,
                    "expect": expected,
                    "check_value": actual,
                    "check_result": "pass" if passed else "failed"
                })
                if not passed:
                    validation_errors.append(f"{comparator}: {path} expect {expected}, got {actual}")
                    success = False

        # 确定测试状态
        status = "passed" if success else "failed"
        error_message = "\n".join(validation_errors) if validation_errors else ""

        return {
            "status": status,
            "request_headers": headers,  # 保存实际发送的请求头（含 Content-Type 等自动添加的头部）
            "request_body": request_body,  # 保存原始请求体
            "response_status_code": response.status_code,
            "response_headers": dict(response.headers),
            "response_body": response_body,
            "error_message": error_message,
            "validators": validators,
            "is_file_download": is_download,
            "raw_response_body_b64": raw_response_b64,
        }

    except requests.RequestException as e:
        logger.exception(f"HTTP request error: {e}")
        return {
            "status": "error",
            "request_headers": headers if 'headers' in locals() else {},
            "request_body": original_body if 'original_body' in locals() else {},
            "response_status_code": None,
            "response_headers": {},
            "response_body": {},
            "error_message": f"HTTP request error: {str(e)}",
            "is_file_download": False,
            "raw_response_body_b64": None,
        }
    except Exception as e:
        logger.exception(f"Unexpected error in direct HTTP request: {e}")
        return {
            "status": "error",
            "request_headers": headers if 'headers' in locals() else {},
            "request_body": original_body if 'original_body' in locals() else {},
            "response_status_code": None,
            "response_headers": {},
            "response_body": {},
            "error_message": f"Unexpected error: {str(e)}",
            "is_file_download": False,
            "raw_response_body_b64": None,
        }


def execute_test_suite(test_suite, default_environment, case_environments=None):
    """
    Execute a test suite (multiple test cases) using direct HTTP requests

    Args:
        test_suite: TestSuite object
        default_environment: Default Environment object to use
        case_environments: Dict mapping test case IDs to environment IDs
    """
    results = []
    case_environments = case_environments or {}
    extracted_variables = {}  # 存储提取的变量，用于后续测试用例

    # 获取套件中的所有测试用例，按顺序排列
    test_suite_cases = test_suite.testsuitecase_set.all().order_by('order')

    logger.info(
        f"Executing test suite: {test_suite.name} (ID: {test_suite.id}) with {test_suite_cases.count()} test cases")

    for test_suite_case in test_suite_cases:
        test_case = test_suite_case.test_case

        # 确定使用哪个环境
        environment = default_environment
        environment_id = default_environment.id

        # 首先检查测试套件用例是否有指定环境
        if hasattr(test_suite_case, 'environment') and test_suite_case.environment:
            environment = test_suite_case.environment
            environment_id = environment.id
        # 然后检查运行时是否指定了环境
        elif test_case.id in case_environments:
            environment_id = case_environments[test_case.id]
            from django.apps import apps
            Environment = apps.get_model('test_manager', 'Environment')
            try:
                environment = Environment.objects.get(id=environment_id)
            except Environment.DoesNotExist:
                logger.error(f"Environment with ID {environment_id} does not exist, using default environment")
                environment = default_environment
                environment_id = default_environment.id

        logger.info(
            f"Executing test case {test_case.name} (ID: {test_case.id}) from suite with environment: {environment.name} (ID: {environment.id})")
        logger.info(f"Using variables: {extracted_variables}")

        # 执行测试用例，传递之前提取的变量
        result = execute_test_case(test_case, environment, extracted_variables)
        result['test_case_id'] = test_case.id
        result['environment_id'] = environment_id

        # 存储提取的变量，用于后续测试用例
        if 'extracted_params' in result and result['extracted_params']:
            extracted_variables.update(result['extracted_params'])
            logger.info(f"Updated variables after test case: {extracted_variables}")

        results.append(result)
        logger.info(f"Test case {test_case.name} execution result: {result['status']}")

    logger.info(
        f"Test suite execution completed. Total: {len(results)}, Passed: {sum(1 for r in results if r['status'] == 'passed')}")

    return results
