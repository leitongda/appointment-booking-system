"""
WebSocket API 路由
提供实时通信能力
"""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from typing import Optional
import json

from app.core.websocket import ws_manager, WSMessage, WSMessageType
from app.core.security import decode_token
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


async def verify_ws_token(token: str) -> Optional[dict]:
    """
    验证 WebSocket 连接的 Token
    
    Args:
        token: JWT Token
        
    Returns:
        Token payload 或 None
    """
    try:
        payload = decode_token(token)
        return payload
    except Exception as e:
        logger.warning(f"WebSocket Token 验证失败: {e}")
        return None


@router.websocket("/doctor/{doctor_id}")
async def doctor_websocket(
    websocket: WebSocket,
    doctor_id: str,
    token: str = Query(...)
):
    """
    医生端 WebSocket 连接
    
    连接地址: ws://host/api/v1/ws/doctor/{doctor_id}?token={jwt_token}
    
    消息类型:
    - CONNECTED: 连接成功
    - HEARTBEAT: 心跳
    - PATIENT_SIGNED_IN: 患者签到
    - PATIENT_CALLED: 叫号
    - QUEUE_UPDATED: 队列更新
    - NEW_APPOINTMENT: 新预约
    - LEAVE_REQUEST_REVIEWED: 请假审核结果
    - SYSTEM_MESSAGE: 系统消息
    """
    # 验证 Token
    payload = await verify_ws_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Token 无效或已过期")
        return
    
    # 验证医生 ID 是否匹配
    token_doctor_id = payload.get("doctor_id")
    token_sub = payload.get("sub")
    
    # 允许医生本人或管理员连接
    if token_doctor_id != doctor_id and token_sub != doctor_id:
        # 检查是否是管理员 Token（有 admin_id）
        admin_id = payload.get("admin_id")
        if not admin_id:
            await websocket.close(code=4003, reason="无权限连接此医生的 WebSocket")
            return
    
    # 建立连接
    await ws_manager.connect(websocket, doctor_id)
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                msg_type = message.get("type", "")
                
                # 处理客户端发来的消息
                if msg_type == "HEARTBEAT":
                    # 心跳响应
                    await websocket.send_text(
                        WSMessage(type=WSMessageType.HEARTBEAT).to_json()
                    )
                elif msg_type == "PING":
                    # Ping 响应
                    await websocket.send_text(
                        json.dumps({"type": "PONG", "timestamp": message.get("timestamp")})
                    )
                else:
                    logger.debug(f"收到医生 {doctor_id} 的消息: {msg_type}")
                    
            except json.JSONDecodeError:
                logger.warning(f"无效的 JSON 消息: {data}")
                
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, doctor_id)
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}")
        await ws_manager.disconnect(websocket, doctor_id)


@router.get("/online-doctors", summary="获取在线医生列表")
async def get_online_doctors():
    """
    获取当前在线的医生列表（调试用）
    """
    if not settings.DEBUG:
        raise HTTPException(status_code=403, detail="仅在调试模式下可用")
    
    return {
        "online_doctors": ws_manager.get_online_doctors(),
        "count": len(ws_manager.get_online_doctors())
    }
