"""
ASGI config for EasyTesting project.

支持 HTTP + WebSocket（需安装 channels + channels_redis）。
如果 channels 未安装，回退为标准 WSGI/ASGI 模式。
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "EasyTesting.settings")

try:
    from channels.routing import ProtocolTypeRouter, URLRouter
    from django.core.asgi import get_asgi_application

    django_asgi_app = get_asgi_application()

    from test_manager.ui_automation.routing import websocket_urlpatterns as ui_ws_patterns
    from test_manager.app_automation.routing import websocket_urlpatterns as app_ws_patterns

    combined_ws_patterns = ui_ws_patterns + app_ws_patterns

    application = ProtocolTypeRouter({
        "http": django_asgi_app,
        "websocket": URLRouter(combined_ws_patterns),
    })
except ImportError:
    # channels 未安装，使用标准 ASGI
    from django.core.asgi import get_asgi_application
    application = get_asgi_application()
