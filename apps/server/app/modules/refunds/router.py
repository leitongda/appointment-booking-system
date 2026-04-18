"""退款路由。"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.deps import (
    check_store_access,
    get_current_admin,
    get_store_filter,
    require_permission,
)
from app.db.session import get_db
from app.middleware.tenant_context import get_current_tenant_id
from app.models.appointment import Appointment
from app.models.refund import RefundRecord
from app.modules.refunds.schemas import (
    RefundCreate,
    RefundListResponse,
    RefundResponse,
    RefundableAmountResponse,
)
from app.modules.refunds.service import RefundService

logger = logging.getLogger(__name__)
router = APIRouter()


async def _get_appointment_or_404(db: AsyncSession, appointment_id: str) -> Appointment:
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
        raise HTTPException(status_code=404, detail="预约不存在")
    return appointment


async def _get_refund_or_404(db: AsyncSession, refund_id: str) -> RefundRecord:
    stmt = (
        select(RefundRecord)
        .options(selectinload(RefundRecord.appointment).selectinload(Appointment.schedule))
        .where(RefundRecord.id == refund_id)
    )
    tenant_id = get_current_tenant_id()
    if tenant_id:
        stmt = stmt.where(RefundRecord.tenant_id == tenant_id)

    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="退款记录不存在")
    return record


def _ensure_admin_can_access_appointment(current_admin: dict, appointment: Appointment) -> None:
    if current_admin.get("is_super_admin"):
        return

    store_id = appointment.schedule.store_id if appointment.schedule else None
    if not check_store_access(current_admin, store_id):
        raise HTTPException(status_code=403, detail="您无权操作此门店的退款")


@router.get("/refundable-amount/{appointment_id}", response_model=RefundableAmountResponse)
async def get_refundable_amount(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("appointment:refund")),
):
    """查询预约的可退款金额。"""
    appointment = await _get_appointment_or_404(db, appointment_id)
    _ensure_admin_can_access_appointment(current_admin, appointment)

    service = RefundService(db)
    result = await service.get_refundable_amount(appointment_id)
    return RefundableAmountResponse(**result)


@router.post("", response_model=RefundResponse)
async def create_refund(
    data: RefundCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("appointment:refund")),
):
    """
    创建退款。

    防退错机制：
    - 退款金额基于预约支付快照的商户号，确保退到原收款商户
    - 累计退款不超过原支付金额
    - RefundRecord + Appointment 同一事务
    """
    appointment = await _get_appointment_or_404(db, data.appointment_id)
    _ensure_admin_can_access_appointment(current_admin, appointment)

    service = RefundService(db)
    refund_record = await service.create_refund(
        appointment_id=data.appointment_id,
        refund_amount=data.refund_amount,
        refund_reason=data.refund_reason,
        operator_id=current_admin.get("id", ""),
    )

    # 调用微信退款 API
    from app.infrastructure.payments.wechat_pay_service import WeChatPayService
    from app.models.miniapp_platform import PaymentProfile

    if refund_record.payment_profile_id:
        profile_stmt = select(PaymentProfile).where(
            PaymentProfile.id == refund_record.payment_profile_id
        )
        profile_result = await db.execute(profile_stmt)
        profile = profile_result.scalar_one_or_none()

        if profile:
            wx_service = WeChatPayService(profile)
            try:
                out_trade_no, transaction_id = await service.ensure_refund_payment_reference(
                    refund_record
                )
                result = await wx_service.create_refund(
                    out_trade_no=out_trade_no,
                    out_refund_no=refund_record.refund_no,
                    total=refund_record.original_amount,
                    refund=refund_record.refund_amount,
                    reason=refund_record.refund_reason or "",
                    notify_url=profile.refund_notify_url or profile.notify_url or "",
                    transaction_id=transaction_id,
                )
                refund_record.status = "processing"
                if result.get("refund_id"):
                    refund_record.wx_refund_id = result.get("refund_id")
            except Exception as e:
                logger.error(f"微信退款调用失败: {e}")
                refund_record.status = "failed"
                refund_record.failed_reason = str(e)
            await service.sync_appointment_refund_state(refund_record.appointment_id)

    await db.commit()
    await db.refresh(refund_record)
    return refund_record


@router.get("", response_model=RefundListResponse)
async def get_refund_records(
    appointment_id: str = None,
    status: str = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("appointment:refund")),
):
    """查询退款记录列表。"""
    if appointment_id:
        appointment = await _get_appointment_or_404(db, appointment_id)
        _ensure_admin_can_access_appointment(current_admin, appointment)

    service = RefundService(db)
    store_filter = get_store_filter(current_admin, allow_all=True)
    records, total = await service.get_refund_records(
        appointment_id=appointment_id,
        status=status,
        store_id=store_filter,
        page=page,
        page_size=page_size,
    )
    return RefundListResponse(
        total=total,
        items=[RefundResponse.model_validate(r) for r in records],
    )


@router.get("/{refund_id}", response_model=RefundResponse)
async def get_refund_detail(
    refund_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("appointment:refund")),
):
    """获取退款详情。"""
    record = await _get_refund_or_404(db, refund_id)
    appointment = record.appointment
    if appointment:
        _ensure_admin_can_access_appointment(current_admin, appointment)
    return record


@router.post("/wechat/callback")
async def wechat_refund_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    微信退款回调（无需认证）。

    流程：
    1. 验签前严格按租户 + 证书序列号反查 PaymentProfile，不做跨租户 fallback
    2. 验签
    3. 解析退款结果
    4. 更新 RefundRecord 状态
    5. 更新 Appointment 退款状态
    """
    from app.infrastructure.payments.wechat_pay_service import WeChatPayService
    from app.middleware.tenant_context import get_current_tenant_id
    from app.models.miniapp_platform import PaymentProfile

    body = await request.body()
    headers = dict(request.headers)

    # 从 header 获取证书序列号（HTTP headers 会被 FastAPI 转换为小写）
    cert_serial_no = headers.get("Wechatpay-Serial") or headers.get("wechatpay-serial")
    if not cert_serial_no:
        return {"code": "FAILED", "message": "缺少证书序列号"}

    tenant_id = get_current_tenant_id()
    if not tenant_id:
        return {"code": "FAILED", "message": "回调缺少租户上下文"}

    # 严格按 tenant_id + cert_serial_no 反查；
    # 多条匹配（如同一商户证书被多 PaymentProfile 复用）按最近创建优先。
    profile_stmt = (
        select(PaymentProfile)
        .where(
            PaymentProfile.cert_serial_no == cert_serial_no,
            PaymentProfile.status == 1,
            PaymentProfile.tenant_id == tenant_id,
        )
        .order_by(PaymentProfile.created_at.desc())
        .limit(1)
    )
    profile_result = await db.execute(profile_stmt)
    profile = profile_result.scalar_one_or_none()

    if not profile:
        return {"code": "FAILED", "message": "未找到支付配置"}

    try:
        # 验签并解密
        wx_service = WeChatPayService(profile)
        data = wx_service.verify_callback(headers=headers, body=body)

        # 解析回调数据
        event_type = data.get("event_type")
        resource = data.get("resource", {})

        if event_type not in ("REFUND.SUCCESS", "REFUND.ABNORMAL", "REFUND.CLOSED"):
            logger.warning(f"非退款事件: {event_type}")
            return {"code": "SUCCESS", "message": "忽略非退款事件"}

        out_refund_no = resource.get("out_refund_no")
        wx_refund_id = resource.get("refund_id")

        if not out_refund_no:
            return {"code": "FAILED", "message": "缺少退款单号"}

        # 确定退款状态
        if event_type == "REFUND.SUCCESS":
            status = "success"
        elif event_type == "REFUND.CLOSED":
            status = "failed"
        else:
            status = "failed"

        # 更新退款记录
        service = RefundService(db)
        await service.process_refund_callback(
            refund_no=out_refund_no,
            wx_refund_id=wx_refund_id,
            status=status,
            callback_raw=body.decode(),
            failed_reason=None if status == "success" else "退款异常",
        )
        await db.commit()

        return {"code": "SUCCESS", "message": "成功"}

    except Exception as e:
        logger.error(f"退款回调处理失败: {e}")
        return {"code": "FAILED", "message": "处理失败"}
