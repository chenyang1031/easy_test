"""
WebSocket 路由配置
"""
from django.urls import re_path
from . import ws_consumers

websocket_urlpatterns = [
    re_path(r'ws/ui-execution/$', ws_consumers.UIExecutionConsumer.as_asgi()),
    re_path(r'ws/ui-actuator/$', ws_consumers.UIActuatorConsumer.as_asgi()),
]
