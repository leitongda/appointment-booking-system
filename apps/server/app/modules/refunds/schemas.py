"""退款模块 Pydantic schemas。"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class RefundCreate(BaseModel):
    """创建退款请求。"""
    appointment_id: str = Field(..., description="预约ID")
    refund_amount: Decimal = Field(..., gt=0, description="退款金额")
    refund_reason: str = Field(..., min_length=1, max_length=500, description="退款原因")


class RefundResponse(BaseModel):
    """退款记录响应。"""
    id: str
    appointment_id: str
    refund_no: str
    out_trade_no: str | None = None
    refund_amount: Decimal
    original_amount: Decimal
    refund_reason: str | None = None
    status: str
    wx_refund_id: str | None = None
    failed_reason: str | None = None
    mch_id: str | None = None
    sub_mchid: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class RefundListResponse(BaseModel):
    """退款列表响应。"""
    total: int
    items: list[RefundResponse]


class RefundableAmountResponse(BaseModel):
    """可退款金额查询响应。"""
    payment_amount: Decimal | None = None
    refunded_amount: Decimal = Decimal("0")
    refundable_amount: Decimal = Decimal("0")
    refund_status: str | None = None
