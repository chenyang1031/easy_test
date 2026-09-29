"""
目标系统（saferycom）验证码自动登录模块

解决图片验证码导致 Token 刷新（har-to-easytesting 技能 Step 0）与
UI 自动化登录无法无人值守执行的问题。

原理（从前端 index-*.js 逆向确认，RuoYi-Vue-Plus apiEncrypt 方案）：
  1. GET  {base}/portal/system/captcha/image
     → {"code":200,"data":{"captchaEnabled":true,"uuid":"...","img":"<base64 PNG>"}}（不加密）
  2. ddddocr 本地 OCR 识读 4 位验证码，识别错误自动换新验证码重试（默认 3 次）
  3. POST {base}/portal/system/auth/login（isEncrypt）
     - 32 位随机字母数字 AES 密钥
     - encrypt-key 头 = RSA_PKCS1v15( base64(aes_key) )，RSA 公钥内置于前端
     - 请求体 = base64( AES-256-ECB-PKCS7( JSON(payload) ) )
     - payload = {username, password, captchaCode, captchaUuid, clientId, grantType:'password'}
  4. 响应带 encrypt-key 头时：RSA 私钥（同样内置前端）解出 base64(aes_key2)，
     再 AES-ECB 解密响应体得到 JSON
  5. 登录成功后 Token 存于目标系统 sessionStorage['Admin-Token']

独立用法（刷新 EasyTesting 环境 Token 前先验证登录可用）：
    python -m test_manager.captcha_login --target 181
密码到期时（报「您的密码已到期」）先改密再自动登录：
    python -m test_manager.captcha_login --target 181 --update-password <新密码>

UI 自动化用法见 test_manager/ui_automation/executor.py 的 _auto_login_if_configured：
在项目公共变量配置 app_username / app_password 即自动登录并注入 Token。
"""
import argparse
import base64
import json
import random
import string
import sys
import time
from dataclasses import dataclass, field

import requests
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA

# ========================== 目标系统常量（前端逆向所得） ==========================
CLIENT_ID = 'b9e4067b420d64a9d46384dd0e5e69f9'

# 前端内置 RSA 公钥：加密 AES 密钥 → encrypt-key 请求头
RSA_PUBLIC_KEY_B64 = (
    'MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCNpt6Z6A/BvZ7C6urCV8lYy6ur7tfbyTj5L+IRy'
    'UkRFCqcuXIi7A1rYvPndsF604T3YUuKEJwxNAA1rINMxVdrk9o5+FI39ugyBK13heruWtnZbtT/Eb'
    'PZcrCdGIe0fEq4B0yrOh14P8XraqOKBglQ4kESbPo/WZGps6KXwXtiwQIDAQAB'
)
# 前端内置 RSA 私钥：解密 encrypt-key 响应头 → AES 密钥 → 解密响应体
RSA_PRIVATE_KEY_B64 = (
    'MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBAITRUuEhGJSEbT9NtqSVbLiTEwkA2'
    '+R69YzwUT3twmSLhDsICIR9uWFFTS9tg00YlQbMty+SxgWxPGUkxt25rY06t6djsIJLWb318QEggb'
    'Meq9wNa3ejk2hciWgf45215O8Nbznqwf+xK6N9c1KCJQyP4bsKBTY0g5Tjs78Dc4cVAgMBAAECgYB'
    '8qaC6EH9qvxVvanj46Aug/uLJ+5VpUgPyIoqOrwBbsRwO8E5WVU9PvmVhE9A+58jRFgsGyyO0qhN+'
    '99L0wFflJoaQ14JgmO3DHH9oorkMl2CUQZ0XeDNud3fjtR6IgAZlXvEbUou+MW9Caqqi/SjCMpwbn'
    'CJ5/juMwhMLyomY4QJBAO8aBwJNS/V4S2h4AG6TsMvAoe9o33GVB8/B1InT83ySZkpAlfGx3M4JGE'
    'Ixv6dj9YjUR0Dr/CH4tvrhjNo34ikCQQCONFd6rnwgU3yfdz3jcWsVzJGzKjBUeVQKSp69U3cS86Z'
    'Eg5e30+ivUMGZuy47tgBrZyLwXTD/NpEpGYUktBMNAkAFZGrgDGo4IPxiYMJxu/bywWdlhNH1N80z'
    'TEXEzfjhyFNyPT6kcsRuCRp487JEziZNbawltKy8/2TxB4ErsrLxAkBbmgvf0xXSHPViI4WSRTUdz'
    'bDtIHgRcjZYisjGXEWPx7OK3tmUaMSyaerMBG87t3l9teoju2QcgiHvv6isg/LhAkEA1ysPVSFOpyL'
    '6XZmZ+K8j0LKFmC0nzXT/Rrd8sycR+Ev/+7/52nOLWfTCzwuJzVmtfNbemVDH7iFaOVHpiRYR3Q=='
)

CAPTCHA_PATH = '/portal/system/captcha/image'
LOGIN_PATH = '/portal/system/auth/login'
UPDATE_PWD_PATH = '/portal/system/auth/updatePwd'

CAPTCHA_WORDS = ('验证码', 'captcha')
CREDENTIAL_WORDS = ('密码', '账号', '用户名', 'credentials', 'password error')


class CaptchaLoginError(Exception):
    """自动登录失败。kind: captcha=验证码识读连续失败 / credentials=账号密码错误 /
    network=目标系统不可达 / other=其他"""

    def __init__(self, message, kind='other'):
        super().__init__(message)
        self.kind = kind


@dataclass
class LoginResult:
    token: str
    token_type: str = 'Bearer'
    raw: dict = field(default_factory=dict)

    @property
    def authorization(self):
        return f'{self.token_type} {self.token}'.strip()


# ========================== 加解密（对应前端 m4/_4/o6/Zn/s6/g4/E4） ==========================
def _generate_aes_key() -> str:
    """前端 x4()：32 位随机字母数字；Utf8 编码后即 32 字节 AES-256 密钥"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(random.choices(alphabet, k=32))


def _pkcs7_pad(data: bytes) -> bytes:
    pad = 16 - len(data) % 16
    return data + bytes([pad]) * pad


def _pkcs7_unpad(data: bytes) -> bytes:
    return data[:-data[-1]]


def aes_ecb_encrypt(plaintext: str, key: str) -> str:
    """前端 Zn()：AES-256-ECB-PKCS7，输出 base64"""
    cipher = AES.new(key.encode('utf-8'), AES.MODE_ECB)
    return base64.b64encode(cipher.encrypt(_pkcs7_pad(plaintext.encode('utf-8')))).decode()


def aes_ecb_decrypt(ciphertext_b64: str, key: bytes) -> str:
    """前端 E4()：AES-256-ECB-PKCS7 解密，输出 UTF-8 文本"""
    cipher = AES.new(key, AES.MODE_ECB)
    raw = base64.b64decode(ciphertext_b64)
    return _pkcs7_unpad(cipher.decrypt(raw)).decode('utf-8')


def rsa_encrypt_key(aes_key_b64: str) -> str:
    """前端 o6()：RSA PKCS1v15 加密 → encrypt-key 请求头"""
    pub = RSA.import_key(base64.b64decode(RSA_PUBLIC_KEY_B64))
    cipher = PKCS1_v1_5.new(pub)
    encrypted = cipher.encrypt(aes_key_b64.encode('utf-8'))
    return base64.b64encode(encrypted).decode()


def rsa_decrypt_key(encrypt_key_header: str) -> bytes:
    """前端 s6()+g4()：RSA 私钥解密 encrypt-key 响应头 → base64(aes_key) → 密钥字节"""
    priv = RSA.import_key(base64.b64decode(RSA_PRIVATE_KEY_B64))
    cipher = PKCS1_v1_5.new(priv)
    sentinel = b'\x00__decrypt_failed__'
    decrypted = cipher.decrypt(base64.b64decode(encrypt_key_header), sentinel)
    if decrypted == sentinel:
        raise CaptchaLoginError('encrypt-key 响应头解密失败', 'other')
    return base64.b64decode(decrypted.decode('utf-8'))


def encrypt_request(payload: dict):
    """返回 (加密请求体, 额外请求头)。对应前端请求拦截器 isEncrypt 分支"""
    aes_key = _generate_aes_key()
    headers = {'encrypt-key': rsa_encrypt_key(base64.b64encode(aes_key.encode('utf-8')).decode())}
    body = aes_ecb_encrypt(json.dumps(payload, ensure_ascii=False), aes_key)
    return body, headers


def decrypt_response(resp) -> dict:
    """对应前端响应拦截器：带 encrypt-key 头则解密，否则按普通 JSON 解析"""
    encrypt_key = resp.headers.get('encrypt-key')
    if encrypt_key:
        key = rsa_decrypt_key(encrypt_key)
        ciphertext = resp.text.strip().strip('"')
        return json.loads(aes_ecb_decrypt(ciphertext, key))
    return resp.json()


# ========================== 验证码 OCR ==========================
_ocr = None


def _get_ocr():
    """ddddocr 懒加载（beta 模型实测首次识读成功率约 83%，默认模型约 50%）"""
    global _ocr
    if _ocr is None:
        import ddddocr
        try:
            _ocr = ddddocr.DdddOcr(show_ad=False, beta=True)
        except TypeError:
            _ocr = ddddocr.DdddOcr()
    return _ocr


def solve_captcha(img_bytes: bytes) -> str:
    return _get_ocr().classification(img_bytes)


def _fetch_captcha(session, base_url, timeout=15, max_backoff=3):
    """获取验证码；服务端限流（访问过于频繁）时指数退避重试。

    Returns:
        (uuid, img_bytes)；验证码关闭时 (None, None)
    """
    for i in range(max_backoff + 1):
        resp = session.get(base_url + CAPTCHA_PATH, timeout=timeout)
        resp.raise_for_status()
        body = resp.json()
        if body.get('code') != 200:
            if '频繁' in str(body.get('msg', '')) and i < max_backoff:
                time.sleep(10 * (i + 1))
                continue
            raise CaptchaLoginError(f"验证码接口返回异常: {body.get('msg')}", 'other')
        data = body.get('data') or {}
        if data.get('captchaEnabled') is False:
            return None, None
        return data.get('uuid'), base64.b64decode(data['img'])
    raise CaptchaLoginError('验证码接口持续限流', 'other')


def _fetch_and_solve(session, base_url, code_len=4, timeout=15, verbose=True):
    """取验证码并 OCR；识读长度不足 code_len 时直接换图重取（不消耗登录请求）。"""
    for _ in range(5):
        cap_uuid, img_bytes = _fetch_captcha(session, base_url, timeout)
        if not cap_uuid:
            return None, ''  # 验证码已关闭
        code = solve_captcha(img_bytes)
        if code_len and len(code) != code_len:
            if verbose:
                print(f'[captcha_login] 识读结果「{code}」长度不足{code_len}位，换图重取')
            continue
        return cap_uuid, code
    return cap_uuid, code  # 连续异常识读也提交一次，交给服务端判定并走重试


# ========================== 登录流程 ==========================
def _new_session():
    session = requests.Session()
    session.headers.update({
        'Clientid': CLIENT_ID,
        'Content-Type': 'application/json;charset=utf-8',
        'Content-Language': 'zh_CN',
    })
    return session


def _extract_token(body: dict):
    """递归查找 token 字段（兼容 access_token / Admin-Token / 嵌套 clientId 结构）"""
    def _walk(node):
        if isinstance(node, dict):
            for k in ('access_token', 'admin_token', 'Admin-Token', 'token'):
                v = node.get(k)
                if isinstance(v, str) and len(v) > 20:
                    return v, ('Bearer' if k != 'token_type' else node.get('token_type', 'Bearer'))
            for v in node.values():
                found = _walk(v)
                if found:
                    return found
        elif isinstance(node, list):
            for item in node:
                found = _walk(item)
                if found:
                    return found
        return None

    found = _walk(body)
    if found:
        return found[0], found[1]
    return None, None


def login(base_url, username, password, retries=3, timeout=15, verbose=True, log_fn=None):
    """验证码自动登录。

    验证码识读错误会自动换新验证码重试；账号密码错误立即抛出不再重试。

    Returns:
        LoginResult: token / authorization 头
    Raises:
        CaptchaLoginError: kind=captcha/credentials/network/other
    """
    base_url = base_url.rstrip('/')
    _emit = log_fn if callable(log_fn) else print
    session = _new_session()
    last_body = {}
    last_err = None

    for attempt in range(1, retries + 1):
        try:
            cap_uuid, code = _fetch_and_solve(session, base_url, timeout=timeout, verbose=verbose)
            if verbose and cap_uuid:
                _emit(f'[captcha_login] 第{attempt}次 OCR 识读验证码: {code}')
            payload = {
                'username': username,
                'password': password,
                'captchaCode': code,
                'captchaUuid': cap_uuid,
                'clientId': CLIENT_ID,
                'grantType': 'password',
            }
            body, extra_headers = encrypt_request(payload)
            resp = session.post(base_url + LOGIN_PATH, data=body.encode('utf-8'),
                                headers=extra_headers, timeout=timeout)
            resp.raise_for_status()
            result = decrypt_response(resp)
            last_body = result
            if result.get('code') == 200:
                token, token_type = _extract_token(result)
                if token:
                    if verbose:
                        _emit(f'[captcha_login] 登录成功，Token 前 20 字符: {token[:20]}...')
                    return LoginResult(token=token, token_type=token_type or 'Bearer', raw=result)
                raise CaptchaLoginError(f'登录响应 200 但未找到 token 字段: {json.dumps(result)[:200]}', 'other')

            msg = str(result.get('msg', ''))
            if '到期' in msg or '过期' in msg:
                raise CaptchaLoginError(f'密码已到期需修改（账号正确，先调 update_password 后重新登录）: {msg}', 'pwd_expired')
            if any(w in msg for w in CREDENTIAL_WORDS):
                raise CaptchaLoginError(f'账号或密码错误: {msg}', 'credentials')
            if any(w in msg for w in CAPTCHA_WORDS):
                if verbose:
                    _emit(f'[captcha_login] 验证码被拒（{msg}），换新验证码重试')
                continue
            # 未知业务错误：多半与验证码无关，重试一次后放弃
            if verbose:
                _emit(f'[captcha_login] 登录返回: code={result.get("code")} msg={msg}')
            last_err = CaptchaLoginError(f'登录失败: {msg or result}', 'other')
        except CaptchaLoginError:
            raise
        except requests.exceptions.ConnectionError as e:
            last_err = CaptchaLoginError(f'目标系统不可达: {base_url}（{e.__class__.__name__}）', 'network')
            break  # 网络不通重试无意义
        except requests.exceptions.RequestException as e:
            last_err = CaptchaLoginError(f'请求异常: {e}', 'network')
            continue
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            last_err = CaptchaLoginError(f'响应解析失败: {e}', 'other')
            continue
        time.sleep(0.3)

    if isinstance(last_err, CaptchaLoginError):
        raise last_err
    raise CaptchaLoginError(
        f'验证码识读连续 {retries} 次失败，最后响应: {json.dumps(last_body, ensure_ascii=False)[:200]}',
        'captcha')


def update_password(base_url, username, old_password, new_password, retries=3, timeout=15, verbose=True):
    """密码到期/自助改密（对应前端 updatePwd 页面 → /system/auth/updatePwd）。

    免登录，需验证码；登录时若报「密码已到期」，先调本函数再重新 login。
    """
    base_url = base_url.rstrip('/')
    session = _new_session()
    last_msg = ''

    for attempt in range(1, retries + 1):
        try:
            cap_uuid, code = _fetch_and_solve(session, base_url, timeout=timeout, verbose=verbose)
            if verbose and cap_uuid:
                print(f'[captcha_login] 第{attempt}次 OCR 识读验证码: {code}')
            payload = {
                'userName': username,
                'oldPassword': old_password,
                'newPassword': new_password,
                'captchaCode': code,
                'captchaUuid': cap_uuid,
            }
            body, extra_headers = encrypt_request(payload)
            resp = session.post(base_url + UPDATE_PWD_PATH, data=body.encode('utf-8'),
                                headers=extra_headers, timeout=timeout)
            resp.raise_for_status()
            result = decrypt_response(resp)
            last_msg = str(result.get('msg', ''))
            if result.get('code') == 200:
                if verbose:
                    print(f'[captcha_login] 密码修改成功')
                return True
            if any(w in last_msg for w in CAPTCHA_WORDS):
                if verbose:
                    print(f'[captcha_login] 验证码被拒（{last_msg}），换新验证码重试')
                continue
            raise CaptchaLoginError(f'修改密码失败: {last_msg or result}', 'other')
        except CaptchaLoginError:
            raise
        except requests.exceptions.ConnectionError as e:
            raise CaptchaLoginError(f'目标系统不可达: {base_url}（{e.__class__.__name__}）', 'network')
        except requests.exceptions.RequestException as e:
            last_msg = f'请求异常: {e}'
            continue

    raise CaptchaLoginError(f'验证码识读连续 {retries} 次失败，最后消息: {last_msg}', 'captcha')


# ========================== CLI ==========================
# 已知环境及当前密码（2026-09-28 181 侧密码到期改密续期，后按用户要求改回 Admin123#）
KNOWN_TARGETS = {
    '181': {'base': 'http://58.215.200.58:19200', 'password': 'Admin123#'},
    '181-internal': {'base': 'http://192.168.0.181:18080', 'password': 'Admin123#'},
    '191': {'base': 'http://192.168.0.191:18081', 'password': 'Admin123#'},
}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='saferycom 目标系统验证码自动登录（ddddocr OCR + AES/RSA 加密复现）')
    parser.add_argument('--target', choices=sorted(KNOWN_TARGETS), help='已知环境代号')
    parser.add_argument('--base', help='目标系统基础地址，如 http://58.215.200.58:19200')
    parser.add_argument('--username', default='apiautotest')
    parser.add_argument('--password', help='不提供时使用目标环境的记录密码')
    parser.add_argument('--retries', type=int, default=3, help='验证码识读重试次数（默认3）')
    parser.add_argument('--save-captcha', help='保存最后一次验证码图片到指定路径（调试用）')
    parser.add_argument('--update-password', help='先把密码改为指定新密码（处理「密码已到期」），再登录验证')
    args = parser.parse_args(argv)

    target = KNOWN_TARGETS.get(args.target, {})
    base = (args.base or target.get('base', '')).rstrip('/')
    if not base:
        parser.error('请通过 --target 或 --base 指定目标系统')
    password = args.password or target.get('password')
    if not password:
        parser.error('该环境无记录密码，请通过 --password 提供')

    try:
        if args.update_password:
            update_password(base, args.username, password, args.update_password,
                            retries=args.retries)
            password = args.update_password
        if args.save_captcha:
            session = _new_session()
            _, img = _fetch_captcha(session, base)
            with open(args.save_captcha, 'wb') as f:
                f.write(img)
            print(f'验证码图片已保存: {args.save_captcha}')

        result = login(base, args.username, password, retries=args.retries)
        print(f'\n环境: {base}')
        print(f'账号: {args.username}')
        print(f'Authorization: {result.authorization}')
        print('（可直接用于 EasyTesting 环境变量 authorization / UI 自动化 Token 注入）')
        return 0
    except CaptchaLoginError as e:
        print(f'登录失败[{e.kind}]: {e}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
