"""
181/191 目标系统 — 验证码自动登录 + EasyTesting 环境 Token 自动刷新

har-to-easytesting 技能 Step 0（Token Refresh）的无人值守实现。
验证码 OCR 识读、AES-ECB/RSA 加密复现、密码到期改密，全部封装在
test_manager/captcha_login.py（可独立 CLI 运行，见其模块注释）。

运行方式（必须经 Django 上下文以 ORM 写环境表）：
    venv/Scripts/python.exe manage.py shell -c "exec(open('login_captcha_tool.py', encoding='utf-8').read())"

可选环境变量：
    LOGIN_ENV=181|191|all   选择目标环境，默认 181

账号线索备忘（apiautotest 为两环境共用测试账号）：
    181 外网 http://58.215.200.58:19200（内网 192.168.0.181:18080 当前不通）
    2026-09-28 181 侧密码曾到期，已改密续期后又按用户要求改回 Admin123#（两环境现同密码）
"""
import json
import os

import requests

from test_manager.captcha_login import CaptchaLoginError, login
from test_manager.models import Environment

OUT_FILE = 'login_captcha_tool_result.txt'

TARGETS = {
    '181': {'env_id': 1, 'name': '演示环境181',
            'login_base': 'http://58.215.200.58:19200',
            'username': 'apiautotest', 'password': 'Admin123#'},
    '191': {'env_id': 2, 'name': '公司环境191',
            'login_base': 'http://192.168.0.191:18081',
            'username': 'apiautotest', 'password': 'Admin123#'},
}

out_lines = []


def say(msg=''):
    print(msg)
    out_lines.append(str(msg))


def refresh_env(target):
    """登录目标系统并把新 Token 写入对应 EasyTesting 环境变量"""
    env_id = target['env_id']
    say(f"== {target['name']}（环境{env_id}）==")
    say(f"  登录地址: {target['login_base']}  账号: {target['username']}")

    try:
        result = login(target['login_base'], target['username'], target['password'])
    except CaptchaLoginError as e:
        say(f'  !! 自动登录失败[{e.kind}]: {e}')
        if e.kind == 'pwd_expired':
            say('  !! 处理办法: python -m test_manager.captcha_login --target <env> '
                '--username <账号> --password <旧密码> --update-password <新密码>')
        return False
    except requests.exceptions.RequestException as e:
        say(f'  !! 网络不可达: {e.__class__.__name__}（跳过）')
        return False

    env = Environment.objects.get(id=env_id)
    variables = env.variables or {}
    variables['authorization'] = result.authorization
    env.variables = variables
    env.save(update_fields=['variables'])
    say(f'  ★ 登录成功，环境 {env_id} 的 authorization 已刷新（Token 前20字符: {result.token[:20]}...）')
    return True


def main():
    choice = os.environ.get('LOGIN_ENV', '181').lower()
    keys = list(TARGETS) if choice == 'all' else [choice]
    ok = []
    for k in keys:
        if refresh_env(TARGETS[k]):
            ok.append(k)
    say('')
    say('========== 完成 ==========')
    say(f'刷新成功环境: {", ".join(ok) if ok else "无"}')
    say('此后接口测试场景直接使用 {{env.authorization}}，Token 过期重跑本脚本即可')


main()
with open(OUT_FILE, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out_lines))
