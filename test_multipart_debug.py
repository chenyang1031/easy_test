"""
测试 multipart 文件上传：模拟执行引擎的 multipart 构建逻辑。
用法: python manage.py shell < test_multipart_debug.py
"""
import os
import sys
import mimetypes
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "EasyTesting.settings")

import django
django.setup()

from django.core.files.storage import default_storage

# --- 配置 ---
FILE_PATH = "api_asset_files/2026/07/15/api_asset_1784103373695.mp3"
FILE_NAME = "zhuangwei.mp3"
LOCAL_DEBUG_URL = "http://127.0.0.1:8000/api/v1/debug/multipart/"
TARGET_URL = "http://192.168.0.191:18081/portal/badge/device/import"

# 读取文件
abs_path = default_storage.path(FILE_PATH)
print(f"文件绝对路径: {abs_path}")
print(f"文件存在: {os.path.exists(abs_path)}")
print(f"文件大小: {os.path.getsize(abs_path)} bytes")

mime_type = mimetypes.guess_type(abs_path)[0] or "application/octet-stream"
print(f"MIME 类型: {mime_type}")

# 构建 multipart_fields（与执行引擎完全一致）
multipart_fields = {
    "chunkFlag": "0",
    "deviceId": "1793229787216920672",
    "startTime": "2026-07-06 13:32:34",
    "file": (
        FILE_NAME,
        open(abs_path, "rb"),
        mime_type,
    ),
}

print("\n" + "=" * 60)
print(f"测试 1: 发送到本地调试端点 {LOCAL_DEBUG_URL}")
print("=" * 60)

encoder = MultipartEncoder(fields=multipart_fields)
print(f"Content-Type: {encoder.content_type}")
print(f"Content-Length: {encoder.len}")

# 保存 body 前 2000 字节到文件供检查
body_bytes = encoder.to_string()
snippet_path = os.path.join(os.path.dirname(__file__), "multipart_body_snippet.txt")
with open(snippet_path, "wb") as f:
    f.write(body_bytes[:3000])
print(f"Body 前 3000 字节已保存到: {snippet_path}")
print(f"Body 总大小: {len(body_bytes)} bytes")

# 打印 body 前 500 字节（可读）
sys.stdout.buffer.write(b"\n--- Body snippet (first 500 bytes) ---\n")
sys.stdout.buffer.write(body_bytes[:500])
sys.stdout.buffer.write(b"\n--- End ---\n\n")
sys.stdout.flush()

# 重新构建 encoder（已被 to_string 消费）
multipart_fields["file"] = (FILE_NAME, open(abs_path, "rb"), mime_type)
encoder2 = MultipartEncoder(fields=multipart_fields)

try:
    resp = requests.post(
        LOCAL_DEBUG_URL,
        data=encoder2,
        headers={"Content-Type": encoder2.content_type},
        timeout=10,
    )
    print(f"状态码: {resp.status_code}")
    print(f"响应: {resp.text}")
except Exception as e:
    print(f"请求失败: {e}")

# 关闭文件
for k, v in multipart_fields.items():
    if isinstance(v, tuple) and hasattr(v[1], "close"):
        v[1].close()

print("\n" + "=" * 60)
print("测试 2: 直接发送到目标 API（可选）")
print("=" * 60)
print(f"如需测试目标服务器，取消下面注释")
print(f"# TARGET_URL = {TARGET_URL}")
# 取消注释即可测试
# multipart_fields["file"] = (FILE_NAME, open(abs_path, "rb"), mime_type)
# encoder3 = MultipartEncoder(fields=multipart_fields)
# headers = {
#     "Content-Type": encoder3.content_type,
#     "Authorization": "Bearer <your_token>",
#     "clientId": "b9e4067b420d64a9d46384dd0e5e69f9",
#     "Content-Language": "zh_CN",
# }
# resp = requests.post(TARGET_URL, data=encoder3, headers=headers, timeout=30)
# print(f"状态码: {resp.status_code}")
# print(f"响应: {resp.text}")

print("\n完成!")
