"""支付路由"""

from __future__ import annotations

import json
import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import check_store_access, get_current_user, get_current_user_or_admin
from app.db.session import get_db
from app.infrastructure.payments.schemas import (
    PaymentOrderCreate,
    PaymentOrderResponse,
    RefundCreate,
    RefundResponse,
)
from app.middleware.tenant_context import get_current_tenant_id
from app.models.admin import Admin
from app.models.appointment import Appointment
from app.modules.payments.service import PaymentService

logger = logging.getLogger(__name__)

router = APIRouter()


class StandardResponse(BaseModel):
    """标准响应格式"""

    code: int = Field(0, description="状态码，0表示成功")
    message: str = Field("success", description="响应消息")
    data: Dict = Field(default_factory=dict, description="响应数据")


async def _get_appointment_or_404(db: AsyncSession, appointment_id: str) -> Appointment:
    """加载预约及其排班信息，并应用租户隔离。"""
    stmt = (
        select(Appointment)
        .options(selectinload(Appointment.schedule))
        .where(Appointment.id == appointment_id)
    )
    tenant_id = get_current_tenant_id()
    if tenant_id:
        stmt = stmt.where(Appointment.tenant_id == tenant_id)

    result = await db.execute(stmt)
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预约不存在，请检查后重试")
    return appointment


async def _require_admin_permission(
    db: AsyncSession,
    current_actor: dict,
    permission: str,
) -> None:
    """校验管理员身份及权限。"""
    if not current_actor.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")

    if current_actor.get("is_super_admin"):
        return

    stmt = (
        select(Admin)
        .options(selectinload(Admin.role))
        .where(Admin.id == current_actor["id"])
    )
    result = await db.execute(stmt)
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="管理员信息不存在，请检查后重试")

    permissions: list[str] = []
    if admin.role and admin.role.permissions:
        try:
            permissions = json.loads(admin.role.permissions)
        except (TypeError, json.JSONDecodeError):
            permissions = []

    if "*" in permissions or permission in permissions:
        return

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"需要权限: {permission}")


def _ensure_user_owns_appointment(appointment: Appointment, current_user: dict) -> None:
    """患者只能操作自己的预约。"""
    if appointment.user_id != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作此预约")


def _ensure_admin_can_access_appointment(appointment: Appointment, current_actor: dict) -> None:
    """管理员必须拥有目标预约所属门店的访问权。"""
    if current_actor.get("is_super_admin"):
        return

    store_id = appointment.schedule.store_id if appointment.schedule else None
    if not check_store_access(current_actor, store_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权操作此门店的预约")


@router.post("/orders", response_model=PaymentOrderResponse, status_code=status.HTTP_200_OK)
async def create_payment_order(
    request_data: PaymentOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """创建支付订单

    返回小程序调起支付所需的参数。
    """
    service = PaymentService(db)
    appointment = await _get_appointment_or_404(db, request_data.appointment_id)
    _ensure_user_owns_appointment(appointment, current_user)

    try:
        result = await service.create_payment_order(
            appointment_id=request_data.appointment_id,
            openid=request_data.openid,
            miniapp_instance_id=request_data.miniapp_instance_id,
        )
        return result

    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建支付订单失败: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="创建支付订单失败")


@router.post("/wechat/callback")
async def wechat_payment_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """微信支付回调

    无需认证，但必须验签。
    """
    service = PaymentService(db)

    try:
        headers = dict(request.headers)
        body = await request.body()

        result = await service.handle_payment_callback(headers=headers, body=body)

        # 返回微信要求的格式
        from fastapi.responses import JSONResponse
        return JSONResponse(content=result)

    except ValueError as e:
        logger.error(f"支付回调处理失败: {e}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"code": "FAILED", "message": str(e)},
        )
    except Exception as e:
        logger.error(f"支付回调处理异常: {e}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"code": "FAILED", "message": "处理失败"},
        )


@router.post("/refunds", response_model=RefundResponse)
async def create_refund(
    request_data: RefundCreate,
    db: AsyncSession = Depends(get_db),
    current_actor: dict = Depends(get_current_user_or_admin),
):
    """创建退款

    需要认证。
    """
    service = PaymentService(db)
    appointment = await _get_appointment_or_404(db, request_data.appointment_id)
    await _require_admin_permission(db, current_actor, "appointment:refund")
    _ensure_admin_can_access_appointment(appointment, current_actor)

    try:
        result = await service.create_refund(
            appointment_id=request_data.appointment_id,
            refund_amount=request_data.refund_amount,
            reason=request_data.reason,
        )
        return result

    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建退款失败: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="创建退款失败")


@router.get("/orders/{appointment_id}", response_model=dict)
async def get_payment_order_status(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    current_actor: dict = Depends(get_current_user_or_admin),
):
    """查询支付订单状态

    返回预约的支付状态信息。
    """
    appointment = await _get_appointment_or_404(db, appointment_id)
    if current_actor.get("is_admin"):
        await _require_admin_permission(db, current_actor, "appointment:detail")
        _ensure_admin_can_access_appointment(appointment, current_actor)
    else:
        _ensure_user_owns_appointment(appointment, current_actor)

    return {
        "appointment_id": appointment.id,
        "status": appointment.status,
        "payment_amount": float(appointment.payment_amount) if appointment.payment_amount else 0,
        "payment_transaction_id": appointment.payment_transaction_id,
        "paid_at": appointment.paid_at.isoformat() if appointment.paid_at else None,
        "refund_status": appointment.refund_status,
        "refund_amount": float(appointment.refund_amount) if appointment.refund_amount else 0,
    }
