"""预约 API - 聚合路由"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_user_or_admin
from app.schemas.appointment import AppointmentCreate, AppointmentResponse, AppointmentCancelRequest
from app.schemas.response import ErrorResponse
from app.modules.appointments.service import AppointmentService


router = APIRouter()

# ==================== 根级别操作（保持在主路由器中以避免路径冲突） ====================


@router.post(
    "",
    response_model=AppointmentResponse,
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
        appointment = await service.create(current_user["id"], data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 发送 WebSocket 通知
    if appointment.doctor_id:
        try:
            from app.core.websocket import notify_new_appointment
            await notify_new_appointment(
                doctor_id=appointment.doctor_id,
                appointment_data={
                    "appointment_id": appointment.id,
                    "patient_name": appointment.patient_name,
                    "queue_number": appointment.queue_number,
                    "schedule_date": appointment.schedule.schedule_date.isoformat() if appointment.schedule else None,
                    "time_slot": appointment.schedule.time_slot if appointment.schedule else None,
                }
            )
        except Exception:
            pass

    return AppointmentResponse.from_appointment(appointment)


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


# ==================== 聚合子模块路由 ====================

from .router_query import router as query_router
from .router_flow import router as flow_router

# 子路由器使用非空路径前缀
router.include_router(query_router, prefix="/query", tags=["预约查询"])
router.include_router(flow_router, tags=["预约状态流转"])
