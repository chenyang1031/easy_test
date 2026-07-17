"""
WebSocket Consumer - UI 自动化执行进度实时推送
"""
import json
import logging
from channels.generic.websocket import AsyncWebSocketConsumer

logger = logging.getLogger('test_manager.ui_automation')


class UIExecutionConsumer(AsyncWebSocketConsumer):
    """
    UI 自动化执行 WebSocket Consumer

    客户端连接后可订阅执行进度，实时接收步骤执行状态。

    URL: ws://host/ws/ui-execution/
    """

    async def connect(self):
        self.room_group_name = 'ui_execution'
        # 加入群组
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        logger.info(f"WebSocket 连接已建立: {self.channel_name}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        logger.info(f"WebSocket 连接已关闭: {self.channel_name}")

    async def receive(self, text_data):
        """接收客户端消息"""
        try:
            data = json.loads(text_data)
            msg_type = data.get('type', '')

            if msg_type == 'subscribe_batch':
                # 订阅特定批次的执行进度
                batch_id = data.get('batch_id')
                if batch_id:
                    group_name = f'ui_batch_{batch_id}'
                    await self.channel_layer.group_add(group_name, self.channel_name)
                    await self.send(text_data=json.dumps({
                        'type': 'subscribed',
                        'batch_id': batch_id,
                    }))

            elif msg_type == 'subscribe_record':
                record_id = data.get('record_id')
                if record_id:
                    group_name = f'ui_record_{record_id}'
                    await self.channel_layer.group_add(group_name, self.channel_name)

            elif msg_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': '无效的 JSON 格式',
            }))

    # ============================================================
    # 群组消息处理器（由 channel_layer.group_send 触发）
    # ============================================================

    async def execution_progress(self, event):
        """转发执行进度到客户端"""
        await self.send(text_data=json.dumps({
            'type': 'execution_progress',
            'data': event['data'],
        }))

    async def execution_complete(self, event):
        """转发执行完成消息"""
        await self.send(text_data=json.dumps({
            'type': 'execution_complete',
            'data': event['data'],
        }))

    async def execution_error(self, event):
        """转发执行错误"""
        await self.send(text_data=json.dumps({
            'type': 'execution_error',
            'data': event['data'],
        }))

    async def batch_update(self, event):
        """转发批次更新"""
        await self.send(text_data=json.dumps({
            'type': 'batch_update',
            'data': event['data'],
        }))


class UIActuatorConsumer(AsyncWebSocketConsumer):
    """
    执行器 WebSocket Consumer

    远程执行器通过此 WebSocket 连接注册并接收任务。

    URL: ws://host/ws/ui-actuator/
    """

    async def connect(self):
        self.actuator_id = None
        await self.accept()

    async def disconnect(self, close_code):
        if self.actuator_id:
            from .ws_models import ws_manager
            ws_manager.unregister(self.actuator_id)

            # 更新数据库中的执行器状态
            try:
                from .models import UiActuator
                await self._update_actuator_status(self.actuator_id, 'offline')
            except Exception:
                pass

    async def receive(self, text_data):
        from .ws_models import ws_manager, WSMessageType

        try:
            data = json.loads(text_data)
            msg_type = data.get('type', '')

            if msg_type == WSMessageType.EXECUTOR_REGISTER.value:
                self.actuator_id = data.get('actuator_id')
                if self.actuator_id:
                    ws_manager.register(self.actuator_id, self)
                    # 更新数据库状态
                    try:
                        from .models import UiActuator
                        await self._update_actuator_status(self.actuator_id, 'online')
                    except Exception:
                        pass
                    await self.send(text_data=json.dumps({
                        'type': 'registered',
                        'actuator_id': self.actuator_id,
                    }))

            elif msg_type == WSMessageType.HEARTBEAT.value:
                await self.send(text_data=json.dumps({
                    'type': 'heartbeat_ack',
                }))
                # 更新心跳时间
                if self.actuator_id:
                    try:
                        from .models import UiActuator
                        from django.utils import timezone
                        await self._update_heartbeat(self.actuator_id)
                    except Exception:
                        pass

            elif msg_type == WSMessageType.EXECUTION_PROGRESS.value:
                # 转发执行进度到 UI 客户端
                from channels.layers import get_channel_layer
                channel_layer = get_channel_layer()
                record_id = data.get('record_id')
                if record_id:
                    await channel_layer.group_send(
                        f'ui_record_{record_id}',
                        {
                            'type': 'execution_progress',
                            'data': data.get('data', {}),
                        }
                    )

            elif msg_type == WSMessageType.EXECUTION_COMPLETE.value:
                from channels.layers import get_channel_layer
                channel_layer = get_channel_layer()
                record_id = data.get('record_id')
                if record_id:
                    await channel_layer.group_send(
                        f'ui_record_{record_id}',
                        {
                            'type': 'execution_complete',
                            'data': data.get('data', {}),
                        }
                    )

        except json.JSONDecodeError:
            pass

    async def _update_actuator_status(self, actuator_id, status):
        from channels.db import database_sync_to_async
        from .models import UiActuator
        from django.utils import timezone

        @database_sync_to_async
        def _update():
            UiActuator.objects.filter(pk=actuator_id).update(
                status=status,
                last_heartbeat=timezone.now(),
            )
        await _update()

    async def _update_heartbeat(self, actuator_id):
        from channels.db import database_sync_to_async
        from .models import UiActuator
        from django.utils import timezone

        @database_sync_to_async
        def _update():
            UiActuator.objects.filter(pk=actuator_id).update(
                last_heartbeat=timezone.now(),
                status='online',
            )
        await _update()
