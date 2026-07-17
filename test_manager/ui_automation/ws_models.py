"""
WebSocket 模型 - 用于执行器(actuator)-服务器通信的状态管理
"""
import logging
from enum import Enum

logger = logging.getLogger('test_manager.ui_automation')


class WSMessageType(str, Enum):
    """WebSocket 消息类型"""
    # 执行器 -> 服务器
    HEARTBEAT = 'heartbeat'
    EXECUTOR_REGISTER = 'executor_register'
    EXECUTION_PROGRESS = 'execution_progress'
    EXECUTION_COMPLETE = 'execution_complete'
    EXECUTION_ERROR = 'execution_error'
    SCREENSHOT_UPLOAD = 'screenshot_upload'

    # 服务器 -> 执行器
    START_EXECUTION = 'start_execution'
    STOP_EXECUTION = 'stop_execution'
    CANCEL_EXECUTION = 'cancel_execution'
    PING = 'ping'


class WSConnectionManager:
    """
    WebSocket 连接管理器（内存级）

    管理执行器(actuator)的 WebSocket 连接。
    用于 actuator-executor 架构中，服务器向远程执行器分发任务。
    """

    def __init__(self):
        self._connections = {}  # actuator_id -> channel_layer / websocket
        self._execution_map = {}  # record_id -> actuator_id

    def register(self, actuator_id, channel):
        """注册执行器连接"""
        self._connections[actuator_id] = channel
        logger.info(f"执行器已注册: {actuator_id}")

    def unregister(self, actuator_id):
        """注销执行器连接"""
        self._connections.pop(actuator_id, None)
        logger.info(f"执行器已注销: {actuator_id}")

    def is_online(self, actuator_id):
        """检查执行器是否在线"""
        return actuator_id in self._connections

    def get_online_count(self):
        """获取在线执行器数量"""
        return len(self._connections)

    def assign_execution(self, record_id, actuator_id):
        """将执行记录分配给执行器"""
        self._execution_map[record_id] = actuator_id

    def get_actuator_for_execution(self, record_id):
        """获取执行记录对应的执行器"""
        return self._execution_map.get(record_id)

    async def send_to_actuator(self, actuator_id, message_type, data):
        """向指定执行器发送消息"""
        channel = self._connections.get(actuator_id)
        if not channel:
            logger.warning(f"执行器 {actuator_id} 不在线")
            return False

        try:
            import json
            message = json.dumps({
                'type': message_type.value if isinstance(message_type, WSMessageType) else message_type,
                'data': data,
            })
            await channel.send(message)
            return True
        except Exception as e:
            logger.error(f"发送消息到执行器失败: {e}")
            return False

    async def broadcast(self, message_type, data):
        """广播消息到所有执行器"""
        for actuator_id in list(self._connections.keys()):
            await self.send_to_actuator(actuator_id, message_type, data)


# 全局连接管理器实例
ws_manager = WSConnectionManager()
