"""
环境前置脚本执行模块。

统一使用 js2py (ES5.1) + CryptoJS 执行前置脚本，全平台（Windows/Linux/Mac）一致。
仅支持 ES5.1 语法，不支持 ES6+（箭头函数、const/let、解构、for...of、对象展开等）。

执行流程：
1. 注入 ES5 Polyfill（Object.assign、includes、forEach、map、filter、trim 等）
2. 注入 CryptoJS 4.2.0（修复 UMD 导出）
3. 对 CryptoJS.HmacSHA256：message 与 key 均为 JS 原始 string 或 number 时，改用 Python hmac（UTF-8），与 Node/服务端一致（避免 number 型密钥走 CryptoJS 导致中文摘要错误）
4. 修复 js2py 环境缺失的全局对象：window、console、Uint32Array、crypto
5. 执行用户脚本

提供 pm 对象（兼容 Postman/Apifox）：
- pm.environment: 读写环境变量
- pm.variables: 临时变量存储
- pm.collectionVariables: 集合级变量
- pm.request: 修改请求头、请求参数、请求体（body 为展开后的数据；headers 与 _req.headers 同引用，支持 [] 下标）
- CryptoJS: MD5、AES、DES、HMAC 等
- console: log、warn、error（输出可被捕获）

约束：脚本禁止网络请求、文件操作，超时时间≤1000ms。
"""
import copy
import hashlib
import hmac
import json
import logging
import os
import re

logger = logging.getLogger(__name__)

try:
    import js2py
    HAS_JS2PY = True
except ImportError:
    HAS_JS2PY = False


class PreRequestScriptError(Exception):
    """前置脚本执行异常。"""


def _coerce_hmac_utf8_string_arg(val):
    """
    将 js2py 传入的 JS 值转为 Python str，用于 UTF-8 字节级 HMAC。
    PyJsString 经 str() 会得到带引号的错误表示，需优先 to_python()。
    环境变量中的纯数字密钥在 JSON 中常为 number，会以 int/float 传入 Python。
    """
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        if val.is_integer():
            return str(int(val))
        return str(val)
    if hasattr(val, "to_python"):
        try:
            out = val.to_python()
            if isinstance(out, str):
                return out
            if out is None:
                return ""
            return str(out)
        except Exception:
            pass
    return str(val)


def _py_hmac_sha256_hex_utf8(message, key):
    """
    与 Node crypto / 常见服务端一致的 HMAC-SHA256（UTF-8 密钥与明文），返回小写十六进制。
    供注入到 JS 全局 __py_hmac_sha256_hex_utf8，仅在被 CryptoJS 包装层调用。
    """
    sm = _coerce_hmac_utf8_string_arg(message)
    sk = _coerce_hmac_utf8_string_arg(key)
    return hmac.new(sk.encode("utf-8"), sm.encode("utf-8"), hashlib.sha256).hexdigest()


def _py_md5_hex(data):
    """Python 原生 MD5，返回小写十六进制。供 CryptoJS.MD5 加速。"""
    s = _coerce_hmac_utf8_string_arg(data)
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def _py_sha256_hex(data):
    """Python 原生 SHA256，返回小写十六进制。供 CryptoJS.SHA256 加速。"""
    s = _coerce_hmac_utf8_string_arg(data)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ============ ES5 Polyfill（内置，无需外部依赖）============
_ES5_POLYFILL = """
(function() {
    if (typeof Object.assign !== 'function') {
        Object.assign = function(target) {
            if (target == null) throw new TypeError('Cannot convert undefined or null to object');
            var to = Object(target);
            for (var i = 1; i < arguments.length; i++) {
                var next = arguments[i];
                if (next != null) {
                    for (var key in next) {
                        if (Object.prototype.hasOwnProperty.call(next, key)) to[key] = next[key];
                    }
                }
            }
            return to;
        };
    }
    if (!Array.prototype.includes) {
        Array.prototype.includes = function(search, from) {
            var len = this.length;
            var fromIdx = from | 0;
            for (var i = fromIdx; i < len; i++) {
                if (this[i] === search) return true;
            }
            return false;
        };
    }
    if (!String.prototype.includes) {
        String.prototype.includes = function(search, start) {
            if (typeof start !== 'number') start = 0;
            return this.indexOf(search, start) !== -1;
        };
    }
    if (!String.prototype.trim) {
        String.prototype.trim = function() {
            return this.replace(/^\\s+|\\s+$/g, '');
        };
    }
    if (!Array.prototype.forEach) {
        Array.prototype.forEach = function(cb, thisArg) {
            for (var i = 0; i < this.length; i++) {
                if (i in this) cb.call(thisArg, this[i], i, this);
            }
        };
    }
    if (!Array.prototype.map) {
        Array.prototype.map = function(cb, thisArg) {
            var out = [], len = this.length;
            for (var i = 0; i < len; i++) {
                if (i in this) out[i] = cb.call(thisArg, this[i], i, this);
            }
            return out;
        };
    }
    if (!Array.prototype.filter) {
        Array.prototype.filter = function(cb, thisArg) {
            var out = [];
            for (var i = 0; i < this.length; i++) {
                if (i in this && cb.call(thisArg, this[i], i, this)) out.push(this[i]);
            }
            return out;
        };
    }
    if (!Array.prototype.find) {
        Array.prototype.find = function(cb, thisArg) {
            for (var i = 0; i < this.length; i++) {
                if (i in this && cb.call(thisArg, this[i], i, this)) return this[i];
            }
            return undefined;
        };
    }
    if (!Array.prototype.findIndex) {
        Array.prototype.findIndex = function(cb, thisArg) {
            for (var i = 0; i < this.length; i++) {
                if (i in this && cb.call(thisArg, this[i], i, this)) return i;
            }
            return -1;
        };
    }
    if (typeof Array.from !== 'function') {
        Array.from = function(arrLike) {
            if (arrLike == null) throw new TypeError('Array.from requires an array-like object');
            var items = Object(arrLike);
            var len = items.length >>> 0;
            var A = [];
            for (var k = 0; k < len; k++) A[k] = items[k];
            A.length = len;
            return A;
        };
    }
})();
"""

# ============ 全局对象修复（window、console、Uint32Array、crypto、Date.now）============
_GLOBAL_FIXES = """
(function() {
    var g = typeof globalThis !== 'undefined' ? globalThis : (typeof self !== 'undefined' ? self : (typeof global !== 'undefined' ? global : this));
    if (typeof window === 'undefined') g.window = g;
    if (typeof self === 'undefined') g.self = g;
    if (typeof Date !== 'undefined' && Date.now) {
        var _dateNowVal = Date.now();
        if (typeof _dateNowVal !== 'number') {
            Date.now = function() { return (new Date()).getTime(); };
        }
    }
    if (typeof Uint32Array === 'undefined') {
        g.Uint32Array = function(len) {
            var arr = [];
            for (var i = 0; i < len; i++) arr[i] = 0;
            arr.length = len;
            return arr;
        };
    }
    if (typeof Uint8Array === 'undefined') {
        g.Uint8Array = function(len) {
            var arr = [];
            for (var i = 0; i < len; i++) arr[i] = 0;
            arr.length = len;
            return arr;
        };
    }
    if (typeof crypto === 'undefined' || typeof crypto.getRandomValues !== 'function') {
        var _fakeCrypto = {
            getRandomValues: function(arr) {
                if (arr && typeof arr.length !== 'undefined') {
                    for (var i = 0; i < arr.length; i++) {
                        arr[i] = Math.floor(Math.random() * 4294967296);
                    }
                    return arr;
                }
                return arr;
            }
        };
        g.crypto = _fakeCrypto;
    }
})();
"""


def _load_crypto_js():
    """加载 CryptoJS 库（MD5、AES、DES、HMAC 等）。"""
    lib_path = os.path.join(os.path.dirname(__file__), "pre_request_script_libs", "crypto-js.min.js")
    if os.path.isfile(lib_path):
        with open(lib_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    return ""


def _fix_es6_default_params(js_code):
    """
    将 ES6 函数默认参数转为 ES5 手动赋值，供 js2py 兼容。
    例: function(t,e=!0){...} → function(t,e){if(e===undefined)e=!0;...}
    """
    def _replace(match):
        params_str = match.group(1)
        if "=" not in params_str:
            return match.group(0)
        params = [p.strip() for p in params_str.split(",")]
        new_params = []
        defaults = []
        for p in params:
            if "=" in p:
                name, default = p.split("=", 1)
                name = name.strip()
                default = default.strip()
                new_params.append(name)
                defaults.append((name, default))
            else:
                new_params.append(p)
        new_params_str = ",".join(new_params)
        result = "function({}){{".format(new_params_str)
        for name, default in defaults:
            result += "if({}===undefined){}=({});".format(name, name, default)
        return result

    return re.sub(r"function\(([^)]+)\)\s*\{", _replace, js_code)


def _prepare_crypto_js_for_js2py(crypto_js_raw):
    """
    为 js2py 环境准备 CryptoJS 代码。
    - UMD 导出适配：将 this 改为显式容器 __cryptoContainer，确保正确挂载。
    - 移除 ES6 默认参数，转为 ES5 兼容写法。
    """
    if not crypto_js_raw or not crypto_js_raw.strip():
        return "var CryptoJS = {};"

    crypto_js_raw = _fix_es6_default_params(crypto_js_raw)

    adapted = re.sub(r"\}\(this\s*,\s*\(function\s*\(\s*\)\s*\{", "}(__cryptoContainer,(function(){", crypto_js_raw)
    if adapted == crypto_js_raw:
        adapted = crypto_js_raw.replace("}(this,(", "}(__cryptoContainer,(")

    return "var __cryptoContainer = {};" + adapted


def _build_apifox_body(body, content_type="application/json"):
    """将内部 body 格式转为 Apifox 兼容结构。"""
    if body is None or (isinstance(body, dict) and not body):
        return {"mode": "raw", "raw": "", "urlencoded": [], "formdata": []}

    if not isinstance(body, dict):
        return {"mode": "raw", "raw": json.dumps(body, ensure_ascii=False) if body else "", "urlencoded": [], "formdata": []}

    if content_type and "form-data" in content_type.lower():
        formdata = []
        for k, v in body.items():
            if isinstance(v, dict) and v.get("type") == "File":
                formdata.append({"key": k, "value": "", "type": "file", "src": v.get("file_path", ""), "disabled": False})
            else:
                formdata.append({"key": k, "value": str(v) if v is not None else "", "type": "text", "disabled": False})
        return {"mode": "formdata", "raw": "", "urlencoded": [], "formdata": formdata}

    if content_type and "x-www-form-urlencoded" in content_type.lower():
        urlencoded = []
        for k, v in body.items():
            if not (isinstance(v, dict) and v.get("type") == "File"):
                urlencoded.append({"key": k, "value": str(v) if v is not None else "", "disabled": False})
        return {"mode": "urlencoded", "raw": "", "urlencoded": urlencoded, "formdata": []}

    return {"mode": "raw", "raw": json.dumps(body, ensure_ascii=False), "urlencoded": [], "formdata": []}


def _parse_apifox_body_back(apifox_body):
    """将 Apifox body 结构转回内部格式。"""
    if not apifox_body or not isinstance(apifox_body, dict):
        return {}
    mode = apifox_body.get("mode", "raw")
    if mode == "urlencoded":
        result = {}
        for item in apifox_body.get("urlencoded") or []:
            if isinstance(item, dict) and item.get("key") and not item.get("disabled"):
                result[item["key"]] = item.get("value", "")
        return result
    if mode == "formdata":
        result = {}
        for item in apifox_body.get("formdata") or []:
            if isinstance(item, dict) and item.get("key") and not item.get("disabled"):
                if item.get("type") == "file":
                    result[item["key"]] = {"type": "File", "file_path": item.get("src", "")}
                else:
                    result[item["key"]] = item.get("value", "")
        return result
    raw = apifox_body.get("raw", "")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {"_raw": raw}


def _unwrap_body_for_script(body, content_type="application/json"):
    """
    将内部 Apifox 结构（mode/raw/urlencoded/formdata）转为脚本里常见的「可直接用」形态：
    - JSON：解析为对象（或原始字符串若解析失败）
    - 表单：扁平为 { key: value } 对象

    这样 pm.request.body 通过 getter 暴露时，与 req.body 为 string/object 的写法一致，
    而不会拿到 { mode, raw, ... } 或 { get, set, toObject } 包装对象。
    """
    if body is None:
        return None
    ct = (content_type or "").strip().lower()
    if not (isinstance(body, dict) and body.get("mode")):
        return body
    mode = body.get("mode")
    if mode == "raw":
        raw = body.get("raw") or ""
        if not str(raw).strip():
            if "json" in ct or "/json" in ct or ct.endswith("+json"):
                return {}
            return raw
        if "json" in ct or "/json" in ct or ct.endswith("+json"):
            try:
                return json.loads(raw)
            except Exception:
                return raw
        return raw
    if mode == "urlencoded":
        out = {}
        for item in body.get("urlencoded") or []:
            if isinstance(item, dict) and item.get("key") and not item.get("disabled"):
                out[item["key"]] = item.get("value", "")
        return out
    if mode == "formdata":
        out = {}
        for item in body.get("formdata") or []:
            if isinstance(item, dict) and item.get("key") and not item.get("disabled"):
                if item.get("type") == "file":
                    continue
                out[item["key"]] = item.get("value", "")
        return out
    return body


# js2py 对大字符串处理性能可接受的上限阈值
# 超过此大小的 body raw 会被截断后传入脚本环境
_MAX_BODY_FOR_SCRIPT = 5 * 1024 * 1024       # 5 MB
# 超过此大小的环境变量值会被截断（保留空间避免 js2py 内部 re 模块超时）
_MAX_ENV_VAL_FOR_SCRIPT = 512 * 1024          # 512 KB


def _truncate_request_data_for_script(request_data):
    """截断过大的 body raw 字段，防止超长字符串注入 js2py 导致性能问题。"""
    if not request_data or not isinstance(request_data, dict):
        return request_data
    body = request_data.get("body")
    if not isinstance(body, dict):
        return request_data
    raw = body.get("raw")
    if isinstance(raw, str) and len(raw) > _MAX_BODY_FOR_SCRIPT:
        body = dict(body)
        body["raw"] = raw[:_MAX_BODY_FOR_SCRIPT] + "\n/* ... truncated for script ... */"
        request_data = dict(request_data)
        request_data["body"] = body
        logger.warning(
            "请求体 raw 大小 %d 字节超过阈值 %d 字节，已被截断传入脚本",
            len(raw), _MAX_BODY_FOR_SCRIPT,
        )
    return request_data


def _truncate_env_vars_for_script(env_vars):
    """截断过大的环境变量值，并将所有值转为字符串以避免 js2py/re 正则报错。"""
    if not env_vars or not isinstance(env_vars, dict):
        return env_vars
    out = {}
    truncated_keys = []
    for k, v in env_vars.items():
        if isinstance(v, str):
            if len(v) > _MAX_ENV_VAL_FOR_SCRIPT:
                out[k] = v[:_MAX_ENV_VAL_FOR_SCRIPT] + "...[truncated]"
                truncated_keys.append(k)
            else:
                out[k] = v
        elif isinstance(v, (dict, list)):
            s = json.dumps(v, ensure_ascii=False)
            if len(s) > _MAX_ENV_VAL_FOR_SCRIPT:
                out[k] = "[truncated]"
                truncated_keys.append(k)
            else:
                out[k] = v
        else:
            # 非字符串标量（int/bool/float/None）全部转 string，避免 js2py 内部 re 正则报错
            out[k] = str(v) if v is not None else ""
    if truncated_keys:
        logger.warning(
            "环境变量 %s 的值超过阈值 %d 字节，已截断传入脚本",
            truncated_keys, _MAX_ENV_VAL_FOR_SCRIPT,
        )
    return out


def _build_full_script(script, env_vars, request_data, variables, collection_vars):
    """
    构建完整 JS 代码，执行流程：
    1. ES5 Polyfill
    2. CryptoJS + 全局修复
    3. pm 对象 + 执行用户脚本（仅支持 ES5.1）
    """
    request_data = _truncate_request_data_for_script(request_data or {})
    env_vars = _truncate_env_vars_for_script(env_vars or {})
    env_json = json.dumps(env_vars, ensure_ascii=False)
    req_json = json.dumps(request_data, ensure_ascii=False)
    var_json = json.dumps(variables or {}, ensure_ascii=False)
    coll_json = json.dumps(collection_vars or {}, ensure_ascii=False)

    # 用户脚本：仅支持 ES5.1，不做 ES6+ 转译
    # 转义用户脚本中的块注释符号，防止破坏外层 block comment 包裹
    user_script_raw = (script or "").replace("/*", "/ *").replace("*/", "* /")
    user_script_escaped = json.dumps(user_script_raw, ensure_ascii=False)

    crypto_js_raw = _load_crypto_js()
    crypto_js = _prepare_crypto_js_for_js2py(crypto_js_raw)

    return f"""
(function() {{
    function _unescapeBmpInString(strVal) {{
        if (typeof strVal !== 'string') return strVal;
        var cur = strVal;
        var i, next;
        for (i = 0; i < 64; i++) {{
            next = cur.replace(/\\\\u([0-9a-fA-F]{{4}})/g, function(m, g) {{
                return String.fromCharCode(parseInt(g, 16));
            }});
            if (next === cur) break;
            cur = next;
        }}
        return cur;
    }}
    function _fmtConsoleArg(x) {{
        if (x === null || x === undefined) return String(x);
        if (typeof x === 'object') {{
            try {{
                return _unescapeBmpInString(JSON.stringify(x));
            }} catch (e) {{
                return String(x);
            }}
        }}
        if (typeof x === 'string') {{
            return _unescapeBmpInString(x);
        }}
        return String(x);
    }}
    var _env = {env_json};
    var _req = {req_json};
    var _vars = {var_json};
    var _coll = {coll_json};
    var _logs = [];

    var console = {{
        log: function() {{ var s = Array.prototype.slice.call(arguments).map(_fmtConsoleArg).join(' '); _logs.push({{ level: 'log', msg: s }}); }},
        warn: function() {{ var s = Array.prototype.slice.call(arguments).map(_fmtConsoleArg).join(' '); _logs.push({{ level: 'warn', msg: s }}); }},
        error: function() {{ var s = Array.prototype.slice.call(arguments).map(_fmtConsoleArg).join(' '); _logs.push({{ level: 'error', msg: s }}); }}
    }};

    {_ES5_POLYFILL}
    {_GLOBAL_FIXES}
    {crypto_js}
    var CryptoJS = (typeof __cryptoContainer !== 'undefined' && __cryptoContainer.CryptoJS) || CryptoJS || {{}};
    (function() {{
        if (!CryptoJS || !CryptoJS.HmacSHA256 || !CryptoJS.enc || !CryptoJS.enc.Hex || !CryptoJS.enc.Hex.parse) return;
        var _origHmacSHA256 = CryptoJS.HmacSHA256;
        CryptoJS.HmacSHA256 = function(message, key) {{
            var mStr = typeof message === 'string' || typeof message === 'number';
            var kStr = typeof key === 'string' || typeof key === 'number';
            if (mStr && kStr) {{
                var ms = typeof message === 'string' ? message : String(message);
                var ks = typeof key === 'string' ? key : String(key);
                var hex = __py_hmac_sha256_hex_utf8(ms, ks);
                return CryptoJS.enc.Hex.parse(hex);
            }}
            return _origHmacSHA256.apply(CryptoJS, arguments);
        }};
    }})();

    (function() {{
        if (!CryptoJS || !CryptoJS.MD5 || !CryptoJS.enc || !CryptoJS.enc.Hex || !CryptoJS.enc.Hex.parse) return;
        var _origMD5 = CryptoJS.MD5;
        CryptoJS.MD5 = function(message) {{
            if (typeof message === 'string' || typeof message === 'number') {{
                var ms = typeof message === 'string' ? message : String(message);
                return CryptoJS.enc.Hex.parse(__py_md5_hex(ms));
            }}
            return _origMD5.call(CryptoJS, message);
        }};
    }})();

    (function() {{
        if (!CryptoJS || !CryptoJS.SHA256 || !CryptoJS.enc || !CryptoJS.enc.Hex || !CryptoJS.enc.Hex.parse) return;
        var _origSHA256 = CryptoJS.SHA256;
        CryptoJS.SHA256 = function(message) {{
            if (typeof message === 'string' || typeof message === 'number') {{
                var ms = typeof message === 'string' ? message : String(message);
                return CryptoJS.enc.Hex.parse(__py_sha256_hex(ms));
            }}
            return _origSHA256.call(CryptoJS, message);
        }};
    }})();

    var pm = {{
        environment: {{
            get: function(k) {{ return _env[k] !== undefined ? _env[k] : undefined; }},
            set: function(k, v) {{ _env[k] = v; }},
            unset: function(k) {{ delete _env[k]; }},
            toObject: function() {{ return Object.assign({{}}, _env); }}
        }},
        variables: {{
            get: function(k) {{ return _vars[k] !== undefined ? _vars[k] : undefined; }},
            set: function(k, v) {{ _vars[k] = v; }},
            unset: function(k) {{ delete _vars[k]; }},
            toObject: function() {{ return Object.assign({{}}, _vars); }}
        }},
        collectionVariables: {{
            get: function(k) {{ return _coll[k] !== undefined ? _coll[k] : undefined; }},
            set: function(k, v) {{ _coll[k] = v; _vars[k] = v; }},
            unset: function(k) {{ delete _coll[k]; delete _vars[k]; }},
            toObject: function() {{ return Object.assign({{}}, _coll); }}
        }},
        request: (function() {{
            var R = {{
                url: {{ toString: function() {{ return _req.url || ''; }} }},
                method: _req.method || 'GET',
                headers: (function() {{
                    var h = _req.headers;
                    if (!h) {{ _req.headers = {{}}; h = _req.headers; }}
                    if (typeof h.get !== 'function') {{
                        var _defHdr = function(name, fn) {{
                            Object.defineProperty(h, name, {{
                                value: fn,
                                enumerable: false,
                                configurable: true,
                                writable: true
                            }});
                        }};
                        _defHdr('get', function(k) {{ return (_req.headers || {{}})[k]; }});
                        _defHdr('set', function(k, v) {{ if (!_req.headers) _req.headers = {{}}; _req.headers[k] = v; }});
                        _defHdr('unset', function(k) {{ if (_req.headers) delete _req.headers[k]; }});
                        _defHdr('has', function(k) {{ return k in (_req.headers || {{}}); }});
                        _defHdr('remove', function(k) {{ if (_req.headers) delete _req.headers[k]; }});
                        _defHdr('add', function(obj) {{
                            var k = obj && (obj.key || obj.name);
                            var v = obj && (obj.value !== undefined ? obj.value : '');
                            if (k && !obj.disabled) {{ if (!_req.headers) _req.headers = {{}}; _req.headers[k] = v; }}
                        }});
                        _defHdr('toObject', function() {{ return Object.assign({{}}, _req.headers || {{}}); }});
                    }}
                    return h;
                }})(),
                params: {{
                    get: function(k) {{ return (_req.params || {{}})[k]; }},
                    set: function(k, v) {{ if (!_req.params) _req.params = {{}}; _req.params[k] = v; }},
                    unset: function(k) {{ if (_req.params) delete _req.params[k]; }},
                    toObject: function() {{ return Object.assign({{}}, _req.params || {{}}); }}
                }}
            }};
            Object.defineProperty(R, 'body', {{
                get: function() {{ return _req.body; }},
                set: function(v) {{ _req.body = v; }},
                enumerable: true,
                configurable: true
            }});
            return R;
        }})(),
        test: function(name, fn) {{ try {{ if (typeof fn === 'function') fn(); }} catch(e) {{ _logs.push({{ level: 'error', msg: 'pm.test failed: ' + (e.message || e) }}); }} }},
        expect: {{ fail: function(msg) {{ throw new Error(msg || 'expect.fail'); }} }}
    }};

    var __pm_result__ = {{ env: _env, request: _req, variables: _vars, collectionVariables: _coll, logs: _logs }};
    var _userScript = {user_script_escaped};
    try {{
        (function(CryptoJS, pm, console) {{
            "use strict";
            eval(_userScript);
        }})(typeof CryptoJS !== 'undefined' ? CryptoJS : {{}}, pm, console);
    }} catch (e) {{
        __pm_result__.error = e.message || String(e);
        _logs.push({{ level: 'error', msg: (e.message || e) }});
        throw e;
    }}
    return __pm_result__;
}})();
"""


def _js_result_to_python(obj):
    """将 js2py 返回的 JsObject / JsObjectWrapper 等递归转为 Python 原生类型，便于 json 序列化。"""
    if obj is None:
        return None
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        return obj
    if isinstance(obj, str):
        return obj
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    if isinstance(obj, dict):
        return {str(k): _js_result_to_python(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_js_result_to_python(x) for x in obj]
    _tn = type(obj).__name__
    if _tn in ("JsObjectWrapper", "JsObject", "JsArrayWrapper", "JsArray"):
        if hasattr(obj, "to_dict"):
            try:
                return _js_result_to_python(obj.to_dict())
            except Exception:
                pass
        if hasattr(obj, "to_list"):
            try:
                return _js_result_to_python(obj.to_list())
            except Exception:
                pass
    if hasattr(obj, "keys") and callable(getattr(obj, "keys", None)):
        try:
            return {str(k): _js_result_to_python(obj[k]) for k in obj.keys()}
        except Exception:
            pass
    if hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes)):
        try:
            return [_js_result_to_python(x) for x in obj]
        except Exception:
            pass
    try:
        return str(obj)
    except Exception:
        return None


def _strip_header_api_noise(headers):
    """去掉误混入的 Postman 风格 API 键名，防止进入 HTTP 请求。"""
    if not isinstance(headers, dict):
        return headers
    noise = frozenset({"get", "set", "unset", "has", "remove", "add", "toObject"})
    return {k: v for k, v in headers.items() if k not in noise}


def execute_pre_request_script(
    script,
    env_vars,
    request_headers,
    request_params,
    request_body,
    variables=None,
    collection_variables=None,
    request_url="",
    request_method="GET",
    content_type="application/json",
    timeout_ms=1000,
):
    """
    执行前置脚本（统一 js2py + Polyfill + CryptoJS），返回更新后的
    (env_vars, request_headers, request_params, request_body, variables, logs)。

    执行流程：Polyfill → CryptoJS → 全局修复 → 执行用户脚本。
    仅支持 ES5.1 语法，不支持 ES6+。若执行报错，建议使用 AI 工具将脚本转换为 ES5.1。

    :param script: JS 脚本内容
    :param env_vars: 环境变量 dict
    :param request_headers: 请求头 dict
    :param request_params: 请求参数 dict
    :param request_body: 请求体
    :param variables: 临时变量 dict
    :param collection_variables: 集合变量 dict
    :param request_url: 请求 URL
    :param request_method: HTTP 方法
    :param content_type: Content-Type
    :param timeout_ms: 超时毫秒（保留参数兼容）
    :return: (env_vars, request_headers, request_params, request_body, variables, logs)
    :raises PreRequestScriptError: 脚本语法错误、执行异常等
    """
    if not script or not str(script).strip():
        return env_vars, request_headers, request_params, request_body, variables or {}, []

    if not HAS_JS2PY:
        raise PreRequestScriptError("js2py 未安装，请运行: pip install js2py")

    body_for_script = request_body
    if isinstance(request_body, dict) and "mode" not in request_body:
        body_for_script = _build_apifox_body(request_body, content_type)

    request_data = {
        "url": str(request_url or ""),
        "method": str(request_method or "GET").upper(),
        "headers": copy.deepcopy(request_headers or {}),
        "params": copy.deepcopy(request_params or {}),
        "body": body_for_script,
    }
    env_vars = copy.deepcopy(env_vars or {})
    variables = copy.deepcopy(variables or {})
    collection_variables = copy.deepcopy(collection_variables or {})

    full_script = _build_full_script(script, env_vars, request_data, variables, collection_variables)

    try:
        _ctx = js2py.EvalJs()
        _ctx.__py_hmac_sha256_hex_utf8 = _py_hmac_sha256_hex_utf8
        _ctx.__py_md5_hex = _py_md5_hex
        _ctx.__py_sha256_hex = _py_sha256_hex
        result = _ctx.eval(full_script)
    except SyntaxError as e:
        raise PreRequestScriptError(f"脚本语法错误: {e}")
    except Exception as e:
        err_msg = str(e)
        if "CryptoJS" in err_msg or "crypto" in err_msg.lower():
            raise PreRequestScriptError(f"CryptoJS 调用异常: {err_msg}")
        raise PreRequestScriptError(f"脚本执行失败: {err_msg}")

    result = _js_result_to_python(result)
    if not result or not isinstance(result, dict):
        return env_vars, request_headers, request_params, request_body, variables, []

    req = result.get("request") or {}
    logs = result.get("logs") or []
    out_body = req.get("body")
    if isinstance(out_body, dict) and "mode" in out_body:
        out_body = _parse_apifox_body_back(out_body)
    if isinstance(out_body, dict) and "_raw" in out_body and len(out_body) == 1:
        out_body = out_body["_raw"]
    out_vars = result.get("variables") or variables
    out_coll = result.get("collectionVariables") or {}
    if isinstance(out_coll, dict):
        out_vars = dict(out_vars) if out_vars else {}
        out_vars.update(out_coll)

    out_headers = req.get("headers") or request_headers
    if isinstance(out_headers, dict):
        out_headers = _strip_header_api_noise(out_headers)

    return (
        result.get("env") or env_vars,
        out_headers,
        req.get("params") or request_params,
        out_body if out_body is not None else request_body,
        out_vars,
        logs,
    )


def execute_pre_request_script_via_subprocess(
    script,
    env_vars,
    request_headers,
    request_params,
    request_body,
    variables=None,
    request_url="",
    request_method="GET",
    content_type="application/json",
    timeout_ms=1000,
):
    """通过子进程执行前置脚本，避免脚本异常导致主进程退出。"""
    import subprocess
    import sys
    from django.conf import settings

    payload = {
        "mode": "execute",
        "script": script,
        "env_vars": env_vars or {},
        "request_headers": request_headers or {},
        "request_params": request_params or {},
        "request_body": request_body if isinstance(request_body, (dict, str)) else {},
        "variables": variables or {},
        "request_url": request_url or "",
        "request_method": request_method or "GET",
        "content_type": content_type or "application/json",
        "timeout_ms": timeout_ms,
    }
    proc_env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "test_manager.pre_request_script_runner"],
            input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            capture_output=True,
            timeout=15,
            cwd=str(settings.BASE_DIR),
            env=proc_env,
        )
    except subprocess.TimeoutExpired:
        raise PreRequestScriptError("脚本执行超时（15秒）")
    except Exception as e:
        raise PreRequestScriptError(f"子进程启动失败: {e}")

    out = proc.stdout.decode("utf-8", errors="replace")
    stderr_text = proc.stderr.decode("utf-8", errors="replace").strip()

    try:
        data = json.loads(out) if out.strip() else {}
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        data = {}

    if proc.returncode != 0:
        err = data.get("error") or stderr_text
        if not err:
            err = "脚本执行进程异常退出"
        raise PreRequestScriptError(err)

    if not data.get("success"):
        raise PreRequestScriptError(data.get("error", "脚本执行失败"))

    return (
        data.get("env") or env_vars,
        data.get("headers") or request_headers,
        data.get("params") or request_params,
        data.get("body") if data.get("body") is not None else request_body,
        data.get("variables") or variables or {},
        data.get("logs") or [],
    )


def test_pre_request_script(script, env_vars=None, request_url="", request_method="GET", timeout_ms=1000):
    """
    测试前置脚本（模拟执行），返回变量变更日志和 console 输出。
    用于前端「测试脚本」功能。
    """
    env_vars = copy.deepcopy(env_vars or {})
    request_headers = {"Content-Type": "application/json"}
    request_params = {}
    request_body = {}
    variables = {}

    try:
        new_env, new_headers, new_params, new_body, new_vars, console_logs = execute_pre_request_script(
            script=script,
            env_vars=env_vars,
            request_headers=request_headers,
            request_params=request_params,
            request_body=request_body,
            variables=variables,
            request_url=request_url or "https://api.example.com/path?foo=bar",
            request_method=request_method or "GET",
            timeout_ms=timeout_ms,
        )
    except PreRequestScriptError as e:
        return {"success": False, "logs": [], "console": [], "error": str(e)}

    logs = []
    for k, v in (new_env or {}).items():
        old = env_vars.get(k)
        if old != v:
            logs.append({"type": "environment", "key": k, "old": old, "new": v})
    for k, v in (new_headers or {}).items():
        old = request_headers.get(k)
        if old != v:
            logs.append({"type": "header", "key": k, "old": old, "new": v})
    for k, v in (new_params or {}).items():
        old = request_params.get(k)
        if old != v:
            logs.append({"type": "param", "key": k, "old": old, "new": v})
    for k, v in (new_vars or {}).items():
        old = variables.get(k)
        if old != v:
            logs.append({"type": "variable", "key": k, "old": old, "new": v})

    console_out = [{"level": item.get("level", "log"), "msg": item.get("msg", "")} for item in (console_logs or [])]

    return {"success": True, "logs": logs, "console": console_out, "error": None}
