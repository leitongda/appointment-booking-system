"""
WebSocket API 路由
提供实时通信能力
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.core.config import settings
from app.core.security import decode_token
from app.core.websocket import WSMessage, WSMessageType, ws_manager
from app.common.auth_deps import get_current_doctor_by_token
from app.models.doctor import Doctor

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== 请求/响应模型 ====================

class PollMessagesResponse(BaseModel):
    """轮询消息响应"""
    messages: list
    count: int


class AckRequest(BaseModel):
    """消息确认请求"""
    message_id: str


# ==================== Token 验证 ====================

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
    token: str = Query(...),
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
    payload = await verify_ws_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Token 无效或已过期")
        return

    token_doctor_id = payload.get("doctor_id")
    token_sub = payload.get("sub")
    tenant_id = payload.get("tenant_id")

    if token_doctor_id != doctor_id and token_sub != doctor_id:
        admin_id = payload.get("admin_id")
        if not admin_id:
            await websocket.close(code=4003, reason="无权限连接此医生的 WebSocket")
            return

    await ws_manager.connect(websocket, doctor_id)

    # 连接成功后，检查并补发未确认消息
    pending_messages = await ws_manager.get_pending_messages(doctor_id, tenant_id)
    if pending_messages:
        logger.info(f"医生 {doctor_id} 重连，补发 {len(pending_messages)} 条未确认消息")
        for msg_data in pending_messages:
            try:
                resend_message = WSMessage(
                    type=msg_data["type"],
                    data=msg_data["data"],
                    timestamp=msg_data["timestamp"],
                    message_id=msg_data["message_id"]
                )
                await websocket.send_text(resend_message.to_json())
            except Exception as e:
                logger.error(f"补发消息失败: {e}")

    try:
        while True:
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_type = message.get("type", "")

                if msg_type == "HEARTBEAT":
                    await websocket.send_text(
                        WSMessage(type=WSMessageType.HEARTBEAT).to_json()
                    )
                elif msg_type == "PING":
                    await websocket.send_text(
                        json.dumps({"type": "PONG", "timestamp": message.get("timestamp")})
                    )
                elif msg_type == "ACK":
                    # 处理消息确认
                    message_id = message.get("message_id")
                    if message_id:
                        removed = await ws_manager.remove_pending_message(
                            message_id, doctor_id, tenant_id
                        )
                        if removed:
                            logger.debug(f"消息 {message_id} 已确认")
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

    online_doctors = ws_manager.get_online_doctors()
    return {
        "online_doctors": online_doctors,
        "count": len(online_doctors),
    }


@router.get("/poll", summary="轮询未确认消息", response_model=PollMessagesResponse)
async def poll_pending_messages(
    doctor_id: str = Query(..., description="医生 ID"),
    tenant_id: Optional[str] = Query(None, description="租户 ID")
):
    """
    HTTP 轮询接口：获取未确认的 WebSocket 消息

    当 WebSocket 连接不可用时，客户端可使用此接口作为降级方案。

    建议轮询间隔：5-10 秒
    """
    messages = await ws_manager.get_pending_messages(doctor_id, tenant_id)
    return PollMessagesResponse(messages=messages, count=len(messages))


@router.post("/ack", summary="确认消息")
async def acknowledge_message(
    body: AckRequest,
    doctor: Doctor = Depends(get_current_doctor_by_token),
):
    """
    HTTP 接口：确认消息已接收

    客户端通过 WebSocket 收到消息后，如果 WebSocket 连接断开，
    可以使用此 HTTP 接口来确认消息。

    需要医生认证 token。
    """
    from app.middleware.tenant_context import get_current_tenant_id
    from app.models.doctor import Doctor

    tenant_id = get_current_tenant_id()
    removed = await ws_manager.remove_pending_message(
        body.message_id, doctor.id, tenant_id
    )

    return {
        "success": True,
        "message_removed": removed
    }
