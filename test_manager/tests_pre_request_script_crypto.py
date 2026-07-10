"""
前置脚本 CryptoJS 集成测试用例。

验证不同加密算法（MD5、SHA256、HMAC、AES、DES）在前置脚本中的执行效果。
可单独运行：python -m pytest test_manager/tests_pre_request_script_crypto.py -v
或：python -m unittest test_manager.tests_pre_request_script_crypto -v
"""
import hashlib
import hmac
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from test_manager.pre_request_script import (
    execute_pre_request_script,
    PreRequestScriptError,
    _unwrap_body_for_script,
    _strip_header_api_noise,
)


class TestUnwrapBodyForScript(unittest.TestCase):
    """Apifox body 展开逻辑（不依赖 js2py）。"""

    def test_json_raw_to_object(self):
        apifox = {
            "mode": "raw",
            "raw": '{"x": 1}',
            "urlencoded": [],
            "formdata": [],
        }
        self.assertEqual(_unwrap_body_for_script(apifox, "application/json"), {"x": 1})

    def test_form_urlencoded_to_flat_dict(self):
        apifox = {
            "mode": "urlencoded",
            "raw": "",
            "urlencoded": [
                {"key": "b", "value": "2", "disabled": False},
                {"key": "a", "value": "1", "disabled": False},
            ],
            "formdata": [],
        }
        self.assertEqual(_unwrap_body_for_script(apifox, "application/x-www-form-urlencoded"), {"b": "2", "a": "1"})

    def test_strip_header_api_noise(self):
        h = {"Content-Type": "application/json", "get": "x", "toObject": "y"}
        self.assertEqual(
            _strip_header_api_noise(h),
            {"Content-Type": "application/json"},
        )


class TestPreRequestScriptCrypto(unittest.TestCase):
    """前置脚本 CryptoJS 加密算法测试。"""

    def setUp(self):
        self.env_vars = {}
        self.headers = {}
        self.params = {}
        self.body = {}
        self.variables = {}

    def _run_script(self, script):
        """执行脚本并返回 (env, headers, params, body, vars, logs)。"""
        return execute_pre_request_script(
            script=script,
            env_vars=self.env_vars,
            request_headers=self.headers,
            request_params=self.params,
            request_body=self.body,
            variables=self.variables,
        )

    def test_md5(self):
        """MD5 哈希：验证常用 MD5 调用。"""
        script = """
        var hash = CryptoJS.MD5("hello").toString();
        pm.environment.set("md5_result", hash);
        """
        env, _, _, _, _, logs = self._run_script(script)
        self.assertIn("md5_result", env)
        # MD5("hello") = 5d41402abc4b2a76b9719d911017c592
        self.assertEqual(env["md5_result"], "5d41402abc4b2a76b9719d911017c592")

    def test_sha256(self):
        """SHA256 哈希：验证 SHA256 调用。"""
        script = """
        var hash = CryptoJS.SHA256("hello").toString(CryptoJS.enc.Hex);
        pm.environment.set("sha256_result", hash);
        """
        env, _, _, _, _, _ = self._run_script(script)
        self.assertIn("sha256_result", env)
        # SHA256("hello") = 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824
        self.assertEqual(
            env["sha256_result"],
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
        )

    def test_hmac_sha256(self):
        """HMAC-SHA256：验证签名生成。"""
        script = """
        var key = "secret";
        var msg = "message";
        var sig = CryptoJS.HmacSHA256(msg, key).toString(CryptoJS.enc.Hex);
        pm.environment.set("hmac_result", sig);
        """
        env, _, _, _, _, _ = self._run_script(script)
        self.assertIn("hmac_result", env)
        self.assertEqual(len(env["hmac_result"]), 64)  # SHA256 hex = 64 chars
        expected = hmac.new(b"secret", b"message", hashlib.sha256).hexdigest()
        self.assertEqual(env["hmac_result"], expected)

    def test_hmac_sha256_utf8_chinese_matches_python(self):
        """HMAC-SHA256（双字符串）：含中文时与 Python hmac 一致，便于与服务端验签对齐。"""
        script = """
        var msg = 'a=1&b={"x":"中文测试"}';
        var sig = CryptoJS.HmacSHA256(msg, "123456").toString(CryptoJS.enc.Hex);
        pm.environment.set("hmac_result", sig);
        """
        env, _, _, _, _, _ = self._run_script(script)
        raw = 'a=1&b={"x":"中文测试"}'
        expected = hmac.new(b"123456", raw.encode("utf-8"), hashlib.sha256).hexdigest()
        self.assertEqual(env["hmac_result"], expected)

    def test_hmac_sha256_numeric_key_stringifies_like_apifox_env(self):
        """密钥为 number（如环境 JSON 解析为数字）时与字符串密钥一致，避免回退到错误 CryptoJS。"""
        script = """
        var msg = 'x=中文';
        var sig = CryptoJS.HmacSHA256(msg, 123456).toString(CryptoJS.enc.Hex);
        pm.environment.set("hmac_result", sig);
        """
        env, _, _, _, _, _ = self._run_script(script)
        expected = hmac.new(b"123456", "x=中文".encode("utf-8"), hashlib.sha256).hexdigest()
        self.assertEqual(env["hmac_result"], expected)

    def test_platform_hmac_matches_pre_request_sign_es5_js(self):
        """
        同一签名字符串：平台前置脚本与 pre_request_sign_es5.js 中 generateHmacSha256Signature
        写法一致时，摘要与 Python/Node 标准 UTF-8 HMAC-SHA256 一致（即可与 Apifox 直接跑 JS 对齐）。
        """
        sign_str = (
            "Sa-App-Id=jxdx&Sa-Device-Type=null&Sa-Req-Time=1774254831412&reqData="
            '{"cusAddress":"这里是测试地址测试地址测试地址","orderNo":"Test1774254830530","userName":"apiautotest"}'
        )
        secret = "123456"
        expected = hmac.new(
            secret.encode("utf-8"),
            sign_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        script = """
function generateHmacSha256Signature(message, secret) {
    var hmac = CryptoJS.HmacSHA256(message, secret);
    return CryptoJS.enc.Hex.stringify(hmac);
}
var msg = """ + json.dumps(sign_str) + """;
pm.environment.set("sig", generateHmacSha256Signature(msg, """ + json.dumps(secret) + """));
"""
        env, _, _, _, _, _ = self._run_script(script)
        self.assertEqual(env.get("sig"), expected)

        node = shutil.which("node")
        if node:
            fd, path = tempfile.mkstemp(suffix=".txt", text=True)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(sign_str)
                js = (
                    "const fs=require('fs');const c=require('crypto');"
                    "const msg=fs.readFileSync(process.argv[1],'utf8');"
                    "const secret='123456';"
                    "process.stdout.write(c.createHmac('sha256',secret).update(msg,'utf8').digest('hex'));"
                )
                out = subprocess.run(
                    [node, "-e", js, path],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=os.path.dirname(__file__),
                )
                self.assertEqual(out.returncode, 0, msg=out.stderr)
                self.assertEqual(out.stdout.strip(), expected, "Node crypto 应与平台/ Python 一致")
            finally:
                try:
                    os.remove(path)
                except OSError:
                    pass

    def test_aes_encrypt_decrypt(self):
        """AES 加解密：验证 AES 加密与解密（使用固定 IV 以兼容 js2py 环境）。"""
        script = """
        var key = CryptoJS.enc.Utf8.parse("1234567890123456");
        var iv = CryptoJS.enc.Utf8.parse("1234567890123456");
        var plain = "hello world";
        var encrypted = CryptoJS.AES.encrypt(plain, key, {
            iv: iv,
            mode: CryptoJS.mode.CBC,
            padding: CryptoJS.pad.Pkcs7
        });
        var cipherHex = encrypted.ciphertext.toString(CryptoJS.enc.Hex);
        pm.environment.set("aes_cipher", cipherHex);
        var decrypted = CryptoJS.AES.decrypt(encrypted, key, {
            iv: iv,
            mode: CryptoJS.mode.CBC,
            padding: CryptoJS.pad.Pkcs7
        });
        pm.environment.set("aes_plain", decrypted.toString(CryptoJS.enc.Utf8));
        """
        env, _, _, _, _, _ = self._run_script(script)
        self.assertIn("aes_cipher", env)
        self.assertIn("aes_plain", env)
        self.assertEqual(env["aes_plain"], "hello world")

    def test_des_encrypt_decrypt(self):
        """DES 加解密：验证 DES 加密与解密。"""
        script = """
        var key = CryptoJS.enc.Utf8.parse("12345678");
        var plain = "secret";
        var encrypted = CryptoJS.DES.encrypt(plain, key, {
            mode: CryptoJS.mode.ECB,
            padding: CryptoJS.pad.Pkcs7
        });
        var decrypted = CryptoJS.DES.decrypt(encrypted, key, {
            mode: CryptoJS.mode.ECB,
            padding: CryptoJS.pad.Pkcs7
        });
        pm.environment.set("des_plain", decrypted.toString(CryptoJS.enc.Utf8));
        """
        env, _, _, _, _, _ = self._run_script(script)
        self.assertEqual(env["des_plain"], "secret")

    def test_pm_request_header_modification(self):
        """pm.request 修改：结合 CryptoJS 生成签名并写入请求头。"""
        script = """
        var ts = Date.now().toString();
        var sig = CryptoJS.MD5("key" + ts).toString();
        pm.request.headers.set("X-Timestamp", ts);
        pm.request.headers.set("X-Signature", sig);
        """
        _, headers, _, _, _, _ = self._run_script(script)
        self.assertIn("X-Timestamp", headers)
        self.assertIn("X-Signature", headers)
        self.assertEqual(len(headers["X-Signature"]), 32)  # MD5 hex = 32 chars
        self.assertRegex(headers["X-Timestamp"], r"^\d{13}$", "X-Timestamp 应为 13 位纯数字毫秒时间戳")

    def test_console_log_capture(self):
        """console 输出捕获：验证 console.log 被正确记录。"""
        script = """
        console.log("info message");
        console.warn("warn message");
        var x = CryptoJS.MD5("test").toString();
        console.log("hash:", x);
        """
        _, _, _, _, _, logs = self._run_script(script)
        self.assertGreaterEqual(len(logs), 3)
        levels = [l.get("level") for l in logs]
        self.assertIn("log", levels)
        self.assertIn("warn", levels)

    def test_syntax_error_raises(self):
        """语法错误：验证脚本语法错误时抛出 PreRequestScriptError。"""
        script = "var x = ;"  # 语法错误
        with self.assertRaises(PreRequestScriptError) as ctx:
            self._run_script(script)
        err_msg = str(ctx.exception)
        self.assertTrue("语法" in err_msg or "执行" in err_msg or "SyntaxError" in err_msg)

    def test_empty_script_returns_unchanged(self):
        """空脚本：验证空脚本直接返回原数据。"""
        env, headers, params, body, vars, logs = self._run_script("")
        self.assertEqual(env, self.env_vars)
        self.assertEqual(headers, self.headers)
        self.assertEqual(logs, [])

    def test_context_isolation(self):
        """上下文隔离：两次执行互不影响。"""
        script1 = "pm.environment.set('k', 'v1');"
        script2 = "pm.environment.set('k', 'v2');"
        env1, _, _, _, _, _ = self._run_script(script1)
        env2, _, _, _, _, _ = self._run_script(script2)
        self.assertEqual(env1["k"], "v1")
        self.assertEqual(env2["k"], "v2")

    def test_es5_object_assign_includes(self):
        """ES5 Object.assign + Array.includes：Polyfill 支持。"""
        script = """
        var o = Object.assign({}, {a: 1}, {b: 2});
        var arr = [1, 2, 3];
        pm.environment.set("assign", JSON.stringify(o));
        pm.environment.set("inc", arr.includes(2));
        """
        env, _, _, _, _, _ = self._run_script(script)
        self.assertEqual(env["assign"], '{"a":1,"b":2}')
        self.assertTrue(env["inc"])

    def test_date_now_millis_timestamp(self):
        """Date.now 兼容修复：确保生成 13 位纯数字毫秒时间戳。"""
        script = """
        function generateMillisTimestamp() {
            return Date.now().toString();
        }
        var timestamp = generateMillisTimestamp();
        pm.environment.set("timestamp", timestamp);
        """
        env, _, _, _, _, _ = self._run_script(script)
        self.assertIn("timestamp", env)
        ts = env["timestamp"]
        self.assertRegex(ts, r"^\d{13}$", "时间戳应为 13 位纯数字")
        self.assertEqual(len(ts), 13)

    def test_es5_for_loop(self):
        """ES5 for 循环：验证标准 for 循环执行。"""
        script = """
        var arr = [10, 20, 30];
        var sum = 0;
        for (var i = 0; i < arr.length; i++) {
            sum += arr[i];
        }
        pm.environment.set("sum", String(sum));
        """
        env, _, _, _, _, _ = self._run_script(script)
        self.assertIn("sum", env)
        self.assertEqual(env["sum"], "60")

    def test_es6_syntax_fails(self):
        """ES6 语法：验证箭头函数等 ES6 语法会报错。"""
        script = "var f = (a,b) => a+b; pm.environment.set('x', f(1,2));"
        with self.assertRaises(PreRequestScriptError) as ctx:
            self._run_script(script)
        err = str(ctx.exception)
        self.assertTrue("语法" in err or "执行" in err or "SyntaxError" in err or "Arrow" in err or "ECMA" in err)


if __name__ == "__main__":
    unittest.main()
