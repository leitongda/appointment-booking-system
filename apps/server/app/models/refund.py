from sqlalchemy import Column, String, Integer, Numeric, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base, AuditMixin
import uuid


class RefundRecord(Base, AuditMixin):
    """退款记录表 — 防重复退款、退款审计、退款全生命周期追踪。"""
    __tablename__ = "refund_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    appointment_id = Column(String(36), ForeignKey("appointments.id"), nullable=False, index=True, comment="预约ID")
    payment_profile_id = Column(String(36), ForeignKey("payment_profiles.id"), nullable=True, index=True, comment="支付配置ID(快照)")

    # 退款单号 — 幂等键
    refund_no = Column(String(64), nullable=False, unique=True, comment="退款单号(幂等键)")
    out_trade_no = Column(String(100), nullable=True, comment="原支付商户订单号")
    wx_transaction_id = Column(String(100), nullable=True, comment="原支付微信交易号")

    # 金额
    refund_amount = Column(Numeric(10, 2), nullable=False, comment="本次退款金额")
    original_amount = Column(Numeric(10, 2), nullable=False, comment="原支付金额(快照)")

    # 退款信息
    refund_reason = Column(String(500), nullable=True, comment="退款原因")
    status = Column(String(20), nullable=False, default="pending", comment="退款状态: pending/processing/success/failed")

    # 微信退款结果
    wx_refund_id = Column(String(100), nullable=True, comment="微信退款单号")
    callback_raw = Column(Text, nullable=True, comment="微信退款回调原始数据")
    callback_at = Column(DateTime, nullable=True, comment="回调接收时间")
    failed_reason = Column(String(500), nullable=True, comment="退款失败原因")

    # 商户信息快照 — 确保退款到原收款商户
    mch_id = Column(String(100), nullable=True, comment="退款使用的商户号(快照)")
    sub_mchid = Column(String(100), nullable=True, comment="退款使用的子商户号(快照)")

    # 关联关系
    tenant = relationship("Tenant", backref="refund_records")
    appointment = relationship("Appointment", backref="refund_records")
    payment_profile = relationship("PaymentProfile", backref="refund_records")

    __table_args__ = (
        UniqueConstraint("appointment_id", "refund_no", name="uq_refund_records_appointment_refund_no"),
        {"comment": "退款记录表"},
    )
