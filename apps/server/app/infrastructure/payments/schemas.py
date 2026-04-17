"""支付相关的 Pydantic schemas"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class PaymentOrderCreate(BaseModel):
    """创建支付订单请求"""

    appointment_id: str = Field(..., description="预约ID")
    openid: str = Field(..., description="微信用户 openid")
    miniapp_instance_id: Optional[str] = Field(None, description="小程序实例ID（可选，用于路由支付配置）")


class PaymentOrderResponse(BaseModel):
    """支付订单响应（小程序调起支付所需参数）"""

    appointment_id: str
    payment_amount: Decimal
    # 微信支付参数
    time_stamp: str
    nonce_str: str
    package: str  # prepay_id=xxx
    sign_type: str
    pay_sign: str


class PaymentCallbackData(BaseModel):
    """微信支付回调数据（解密后）"""

    event_type: str = Field(..., description="事件类型: TRANSACTION.SUCCESS")
    resource: PaymentCallbackResource


class PaymentCallbackResource(BaseModel):
    """支付回调资源数据"""

    appid: str
    mchid: str
    out_trade_no: str
    transaction_id: str
    trade_type: str
    trade_state: str
    trade_state_desc: str
    bank_type: str
    attach: Optional[str] = None
    success_time: Optional[str] = None
    payer: Optional[dict] = None
    amount: PaymentCallbackAmount


class PaymentCallbackAmount(BaseModel):
    """支付回调金额信息"""

    total: int = Field(..., description="订单总金额（分）")
    payer_total: int = Field(..., description="用户支付金额（分）")
    currency: str = Field(..., description="货币类型")
    payer_currency: str = Field(..., description="用户支付货币")


class RefundCreate(BaseModel):
    """创建退款请求"""

    appointment_id: str = Field(..., description="预约ID")
    refund_amount: Decimal = Field(..., gt=0, description="退款金额（元）")
    reason: str = Field("", description="退款原因")


class RefundResponse(BaseModel):
    """退款响应"""

    appointment_id: str
    refund_amount: Decimal
    refund_status: str  # pending/success/failed
    refund_id: Optional[str] = None
    out_refund_no: Optional[str] = None


class RefundCallbackData(BaseModel):
    """微信退款回调数据（解密后）"""

    event_type: str = Field(..., description="事件类型: REFUND.SUCCESS 等")
    resource: RefundCallbackResource


class RefundCallbackResource(BaseModel):
    """退款回调资源数据"""

    refund_id: str
    out_refund_no: str
    transaction_id: str
    refund_status: str
    amount: RefundCallbackAmount


class RefundCallbackAmount(BaseModel):
    """退款回调金额信息"""

    total: int = Field(..., description="订单总金额（分）")
    refund: int = Field(..., description="退款金额（分）")
    payer_total: int = Field(..., description="用户支付金额（分）")
    payer_refund: int = Field(..., description="用户退款金额（分）")
