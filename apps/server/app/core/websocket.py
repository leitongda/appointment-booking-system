"""
WebSocket 连接管理器
支持 Redis Pub/Sub 实现多实例广播
"""
import json
import asyncio
import logging
from typing import Dict, Set, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from fastapi import WebSocket, WebSocketDisconnect

from app.core.redis import get_redis

logger = logging.getLogger(__name__)


class WSMessageType(str, Enum):
    """WebSocket 消息类型"""
    # 系统消息
    CONNECTED = "CONNECTED"
    HEARTBEAT = "HEARTBEAT"
    ERROR = "ERROR"
    
    # 预约相关
    PATIENT_SIGNED_IN = "PATIENT_SIGNED_IN"      # 患者签到
    PATIENT_CALLED = "PATIENT_CALLED"            # 叫号
    PATIENT_PASSED = "PATIENT_PASSED"            # 过号
    PATIENT_RECALLED = "PATIENT_RECALLED"        # 重呼
    PATIENT_COMPLETED = "PATIENT_COMPLETED"      # 就诊完成
    PATIENT_NO_SHOW = "PATIENT_NO_SHOW"          # 爽约
    QUEUE_UPDATED = "QUEUE_UPDATED"              # 队列更新
    NEW_APPOINTMENT = "NEW_APPOINTMENT"          # 新预约
    
    # 排班相关
    SCHEDULE_SUSPENDED = "SCHEDULE_SUSPENDED"    # 排班停诊
    LEAVE_REQUEST_REVIEWED = "LEAVE_REQUEST_REVIEWED"  # 请假审核结果
    
    # 系统通知
    SYSTEM_MESSAGE = "SYSTEM_MESSAGE"            # 系统消息


@dataclass
class WSMessage:
    """WebSocket 消息结构"""
    type: WSMessageType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_json(self) -> str:
        return json.dumps({
            "type": self.type.value if isinstance(self.type, WSMessageType) else self.type,
            "data": self.data,
            "timestamp": self.timestamp
        }, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, data: str) -> "WSMessage":
        obj = json.loads(data)
        return cls(
            type=obj.get("type", ""),
            data=obj.get("data", {}),
            timestamp=obj.get("timestamp", "")
        )


class ConnectionManager:
    """
    WebSocket 连接管理器
    
    支持：
    - 按医生 ID 管理连接
    - Redis Pub/Sub 多实例广播
    - 心跳检测
    """
    
    # Redis 频道前缀
    CHANNEL_PREFIX = "ws:doctor:"
    CHANNEL_BROADCAST = "ws:broadcast"
    
    def __init__(self):
        # 本地连接映射：doctor_id -> Set[WebSocket]
        self._connections: Dict[str, Set[WebSocket]] = {}
        # 心跳任务
        self._heartbeat_task: Optional[asyncio.Task] = None
        # Pub/Sub 订阅任务
        self._pubsub_task: Optional[asyncio.Task] = None
        self._pubsub = None
        self._running = False
    
    async def start(self):
        """启动连接管理器"""
        if self._running:
            return
        
        self._running = True
        
        # 启动心跳任务
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        # 启动 Redis Pub/Sub 监听
        self._pubsub_task = asyncio.create_task(self._pubsub_listener())
        
        logger.info("WebSocket 连接管理器已启动")
    
    async def stop(self):
        """停止连接管理器"""
        self._running = False
        
        # 取消心跳任务
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # 取消 Pub/Sub 任务
        if self._pubsub_task:
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass
        
        # 关闭 Pub/Sub 连接
        if self._pubsub:
            await self._pubsub.close()
        
        # 关闭所有连接
        for doctor_id, connections in self._connections.items():
            for ws in connections:
                try:
                    await ws.close()
                except Exception:
                    pass
        
        self._connections.clear()
        logger.info("WebSocket 连接管理器已停止")
    
    async def connect(self, websocket: WebSocket, doctor_id: str):
        """
        接受新的 WebSocket 连接
        """
        await websocket.accept()
        
        if doctor_id not in self._connections:
            self._connections[doctor_id] = set()
        
        self._connections[doctor_id].add(websocket)
        
        logger.info(f"医生 {doctor_id} 建立 WebSocket 连接，当前连接数: {len(self._connections[doctor_id])}")
        
        # 发送连接成功消息
        await self._send_to_websocket(
            websocket,
            WSMessage(type=WSMessageType.CONNECTED, data={"doctor_id": doctor_id})
        )
    
    async def disconnect(self, websocket: WebSocket, doctor_id: str):
        """
        断开 WebSocket 连接
        """
        if doctor_id in self._connections:
            self._connections[doctor_id].discard(websocket)
            
            if not self._connections[doctor_id]:
                del self._connections[doctor_id]
        
        logger.info(f"医生 {doctor_id} 断开 WebSocket 连接")
    
    async def send_to_doctor(self, doctor_id: str, message: WSMessage):
        """
        发送消息给指定医生（本地 + Redis 广播）
        """
        # 先发送本地连接
        await self._send_local(doctor_id, message)
        
        # 通过 Redis 广播到其他实例
        await self._publish_to_redis(doctor_id, message)
    
    async def broadcast_to_all(self, message: WSMessage):
        """
        广播消息给所有在线医生
        """
        # 发送到所有本地连接
        for doctor_id in self._connections.keys():
            await self._send_local(doctor_id, message)
        
        # 通过 Redis 广播
        await self._publish_to_redis_broadcast(message)
    
    async def _send_local(self, doctor_id: str, message: WSMessage):
        """
        发送消息到本地连接
        """
        if doctor_id not in self._connections:
            return
        
        dead_connections = set()
        
        for websocket in self._connections[doctor_id]:
            try:
                await self._send_to_websocket(websocket, message)
            except Exception as e:
                logger.warning(f"发送消息失败: {e}")
                dead_connections.add(websocket)
        
        # 清理失效连接
        for ws in dead_connections:
            self._connections[doctor_id].discard(ws)
    
    async def _send_to_websocket(self, websocket: WebSocket, message: WSMessage):
        """
        发送消息到单个 WebSocket
        """
        await websocket.send_text(message.to_json())
    
    async def _publish_to_redis(self, doctor_id: str, message: WSMessage):
        """
        通过 Redis Pub/Sub 发布消息（指定医生）
        """
        try:
            redis = await get_redis()
            channel = f"{self.CHANNEL_PREFIX}{doctor_id}"
            await redis.publish(channel, message.to_json())
        except Exception as e:
            logger.error(f"Redis 发布消息失败: {e}")
    
    async def _publish_to_redis_broadcast(self, message: WSMessage):
        """
        通过 Redis Pub/Sub 广播消息
        """
        try:
            redis = await get_redis()
            await redis.publish(self.CHANNEL_BROADCAST, message.to_json())
        except Exception as e:
            logger.error(f"Redis 广播消息失败: {e}")
    
    async def _pubsub_listener(self):
        """
        Redis Pub/Sub 监听器
        接收其他实例发来的消息并转发给本地连接
        """
        try:
            redis = await get_redis()
            self._pubsub = redis.pubsub()
            
            # 订阅广播频道
            await self._pubsub.subscribe(self.CHANNEL_BROADCAST)
            
            logger.info("Redis Pub/Sub 监听器已启动")
            
            while self._running:
                try:
                    # 动态订阅当前在线医生的频道
                    current_channels = set()
                    for doctor_id in self._connections.keys():
                        channel = f"{self.CHANNEL_PREFIX}{doctor_id}"
                        current_channels.add(channel)
                    
                    # 订阅新频道
                    subscribed = set(self._pubsub.channels.keys()) if hasattr(self._pubsub, 'channels') else set()
                    for channel in current_channels - subscribed:
                        await self._pubsub.subscribe(channel)
                    
                    # 读取消息（非阻塞）
                    message = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
                    
                    if message and message["type"] == "message":
                        channel = message["channel"]
                        data = message["data"]
                        
                        try:
                            ws_message = WSMessage.from_json(data)
                            
                            if channel == self.CHANNEL_BROADCAST:
                                # 广播消息：发送给所有本地连接
                                for doctor_id in self._connections.keys():
                                    await self._send_local(doctor_id, ws_message)
                            elif channel.startswith(self.CHANNEL_PREFIX):
                                # 指定医生消息
                                doctor_id = channel[len(self.CHANNEL_PREFIX):]
                                await self._send_local(doctor_id, ws_message)
                        except Exception as e:
                            logger.error(f"处理 Pub/Sub 消息失败: {e}")
                    
                    await asyncio.sleep(0.01)  # 避免 CPU 占用过高
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Pub/Sub 监听器错误: {e}")
                    await asyncio.sleep(1)  # 出错后等待重试
                    
        except Exception as e:
            logger.error(f"Pub/Sub 监听器启动失败: {e}")
    
    async def _heartbeat_loop(self):
        """
        心跳循环，定期发送心跳包检测连接存活
        """
        while self._running:
            try:
                await asyncio.sleep(30)  # 每 30 秒发送一次心跳
                
                for doctor_id, connections in list(self._connections.items()):
                    dead_connections = set()
                    
                    for websocket in connections:
                        try:
                            await websocket.send_text(
                                WSMessage(type=WSMessageType.HEARTBEAT).to_json()
                            )
                        except Exception:
                            dead_connections.add(websocket)
                    
                    # 清理失效连接
                    for ws in dead_connections:
                        connections.discard(ws)
                        logger.info(f"清理医生 {doctor_id} 的失效连接")
                    
                    if not connections:
                        del self._connections[doctor_id]
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳循环错误: {e}")
    
    def get_online_doctors(self) -> list[str]:
        """获取所有在线医生 ID"""
        return list(self._connections.keys())
    
    def is_doctor_online(self, doctor_id: str) -> bool:
        """检查医生是否在线"""
        return doctor_id in self._connections and len(self._connections[doctor_id]) > 0


# 全局连接管理器实例
ws_manager = ConnectionManager()


# ==================== 便捷发送函数 ====================

async def notify_doctor(doctor_id: str, message_type: WSMessageType, data: Dict[str, Any] = None):
    """
    向指定医生发送通知
    
    Args:
        doctor_id: 医生 ID
        message_type: 消息类型
        data: 消息数据
    """
    message = WSMessage(type=message_type, data=data or {})
    await ws_manager.send_to_doctor(doctor_id, message)


async def notify_patient_signed_in(doctor_id: str, appointment_data: Dict[str, Any]):
    """通知医生：患者已签到"""
    await notify_doctor(doctor_id, WSMessageType.PATIENT_SIGNED_IN, appointment_data)


async def notify_queue_updated(doctor_id: str, queue_data: Dict[str, Any] = None):
    """通知医生：队列已更新"""
    await notify_doctor(doctor_id, WSMessageType.QUEUE_UPDATED, queue_data or {})


async def notify_new_appointment(doctor_id: str, appointment_data: Dict[str, Any]):
    """通知医生：新预约"""
    await notify_doctor(doctor_id, WSMessageType.NEW_APPOINTMENT, appointment_data)


async def notify_leave_request_reviewed(doctor_id: str, review_data: Dict[str, Any]):
    """通知医生：请假审核结果"""
    await notify_doctor(doctor_id, WSMessageType.LEAVE_REQUEST_REVIEWED, review_data)


async def broadcast_system_message(message: str, title: str = "系统通知"):
    """广播系统消息给所有在线医生"""
    await ws_manager.broadcast_to_all(
        WSMessage(
            type=WSMessageType.SYSTEM_MESSAGE,
            data={"title": title, "message": message}
        )
    )
