"""预约 API - 聚合路由"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_user_or_admin
from app.db.session import get_db
from app.modules.appointments.service import AppointmentService
from app.schemas.appointment import (
    AppointmentCancelRequest,
    AppointmentCreate,
    AppointmentPendingPaymentResponse,
    AppointmentResponse,
)
from app.schemas.response import ErrorResponse

router = APIRouter()


def _serialize_created_appointment(result):
    if isinstance(result, dict):
        return AppointmentPendingPaymentResponse.from_result(result)
    return AppointmentResponse.from_appointment(result)

# ==================== 根级别操作（保持在主路由器中以避免路径冲突） ====================


@router.post(
    "",
    response_model=AppointmentResponse | AppointmentPendingPaymentResponse,
    summary="创建预约",
    description="""
    患者提交预约申请，系统自动分配号源并生成预约编号。

    **业务规则**：
    - 必须关联有效的排班记录（schedule_id），且排班有余量
    - 同一患者同一天同一时段不可重复预约
    - 预约需在规则引擎允许的时间窗口内（预约开放时间 ~ 预约截止时间）
    - 创建成功后通过 WebSocket 通知对应医生端

    **权限要求**：
    - 患者用户或管理员均可调用
    """,
    responses={
        400: {"model": ErrorResponse, "description": "预约失败"},
        404: {"model": ErrorResponse, "description": "排班不存在"},
    }
)
async def create_appointment(
    data: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin)
):
    """创建预约"""
    service = AppointmentService(db)

    try:
        result = await service.create(current_user["id"], data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    appointment = result["appointment"] if isinstance(result, dict) else result

    # 发送 WebSocket 通知
    if appointment.doctor_id:
        try:
            from app.core.websocket import notify_new_appointment
            from app.schemas.appointment import AppointmentResponse
            _schedule = AppointmentResponse._safe_get_relation(appointment, "schedule")
            await notify_new_appointment(
                doctor_id=appointment.doctor_id,
                appointment_data={
                    "appointment_id": appointment.id,
                    "patient_name": appointment.patient_name,
                    "queue_number": appointment.queue_number,
                    "schedule_date": _schedule.schedule_date.isoformat() if _schedule else None,
                    "time_slot": _schedule.time_slot if _schedule else None,
                }
            )
        except Exception:
            pass

    return _serialize_created_appointment(result)


@router.put(
    "/{appointment_id}/cancel",
    summary="取消预约",
    description="""
    取消指定预约，释放对应排班的号源。

    **业务规则**：
    - 只有"已预约"状态的预约可以取消
    - 取消需在规则引擎允许的取消时间窗口内
    - 管理员可取消任意预约，普通用户只能取消自己的预约
    - 取消后对应排班的 booked_slots 自动减 1

    **参数说明**：
    - appointment_id: 预约记录ID（路径参数）
    - reason: 取消原因（可选）
    """,
    responses={
        400: {"model": ErrorResponse, "description": "取消失败"},
        404: {"model": ErrorResponse, "description": "预约不存在"},
    }
)
async def cancel_appointment(
    appointment_id: str,
    data: AppointmentCancelRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin)
):
    """取消预约"""
    service = AppointmentService(db)
    reason = data.reason if data else None
    is_admin = current_user.get("is_admin", False)

    try:
        appointment = await service.cancel(appointment_id, current_user["id"], reason, is_admin)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预约不存在")

    return {"message": "取消成功"}


@router.get(
    "/{appointment_id}/payment-params",
    summary="获取支付参数",
    description="""
    待支付订单重新获取支付参数（用户取消支付后重新发起）。

    **业务规则**：
    - 仅患者本人可调用
    - 预约状态必须为待支付（status=0）
    - 返回小程序调起支付所需的参数

    **参数说明**：
    - appointment_id: 预约记录ID（路径参数）
    - openid: 微信用户openid（query参数，必需）
    """,
    responses={
        400: {"model": ErrorResponse, "description": "参数错误或状态不正确"},
        404: {"model": ErrorResponse, "description": "预约不存在"},
    }
)
async def get_payment_params(
    appointment_id: str,
    openid: str | None = Query(None, description="微信用户openid；未提供时自动读取当前登录用户绑定值"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取支付参数（重新发起支付）"""
    from sqlalchemy import select

    from app.middleware.tenant_context import get_current_tenant_id
    from app.models.appointment import Appointment
    from app.models.user import User

    # 1. 查询预约
    stmt = select(Appointment).where(Appointment.id == appointment_id)
    tenant_id = get_current_tenant_id()
    if tenant_id:
        stmt = stmt.where(Appointment.tenant_id == tenant_id)

    result = await db.execute(stmt)
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预约不存在，请检查后重试"
        )

    # 2. 验证权限：只能操作自己的预约
    if appointment.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权操作此预约"
        )

    # 3. 验证预约状态：必须是待支付状态
    if appointment.status != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="预约状态不正确，当前状态不支持支付，请检查后重试"
        )

    # 4. 验证支付金额
    if not appointment.payment_amount or appointment.payment_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="支付金额无效，请检查后重试"
        )

    # 5. 优先使用显式传入的 openid，否则回退到当前登录用户已绑定的 openid
    effective_openid = openid
    if not effective_openid:
        user_stmt = select(User).where(User.id == current_user["id"])
        if tenant_id:
            user_stmt = user_stmt.where(User.tenant_id == tenant_id)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        effective_openid = user.openid if user else None

    if not effective_openid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前账号未绑定微信 openid，请重新登录微信后再试"
        )

    # 6. 调用支付服务生成支付参数
    try:
        from app.modules.payments.service import PaymentService
        payment_service = PaymentService(db)
        payment_params = await payment_service.create_payment_order(
            appointment_id=appointment_id,
            openid=effective_openid,
            miniapp_instance_id=appointment.payment_miniapp_instance_id,
        )
        return payment_params
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取支付参数失败: {str(e)}"
        )


# ==================== 聚合子模块路由 ====================

from .router_flow import router as flow_router
from .router_query import router as query_router

# 子路由器使用非空路径前缀
router.include_router(query_router, prefix="/query", tags=["预约查询"])
router.include_router(flow_router, tags=["预约状态流转"])
