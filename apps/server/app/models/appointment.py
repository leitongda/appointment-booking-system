from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from app.db.base import Base, AuditMixin
from datetime import datetime
import uuid

class Appointment(Base, AuditMixin):
    __tablename__ = "appointments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    appointment_no = Column(String(50), unique=True, nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(String(36), ForeignKey("doctors.id"), nullable=False)
    schedule_id = Column(String(36), ForeignKey("schedules.id"), nullable=False)
    rule_set_id = Column(String(36), ForeignKey("rule_sets.id"), nullable=True, comment="应用的规则组ID")
    # 租户关联（多租户支持）
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    queue_number = Column(Integer)  # 队列号
    status = Column(Integer, default=1)  # 0待支付 1已预约 2已签到 3历史候诊(遗留) 4就诊中 5已完成 6已取消 7已过期 8已爽约
    sign_in_time = Column(DateTime)
    call_time = Column(DateTime)
    complete_time = Column(DateTime)
    cancel_time = Column(DateTime)
    cancel_reason = Column(Text)
    remark = Column(Text)
    symptom_description = Column(Text, nullable=True, comment="病情描述/预填信息")

    # 规则快照 - 预约时计算并存储
    book_open_at = Column(DateTime(timezone=True), nullable=True, comment="预约开放时间(快照)")
    book_close_at = Column(DateTime(timezone=True), nullable=True, comment="预约截止时间(快照)")
    checkin_open_at = Column(DateTime(timezone=True), nullable=True, comment="签到开放时间(快照)")
    checkin_close_at = Column(DateTime(timezone=True), nullable=True, comment="签到截止时间(快照)")
    cancel_open_at = Column(DateTime(timezone=True), nullable=True, comment="取消开放时间(快照)")
    cancel_close_at = Column(DateTime(timezone=True), nullable=True, comment="取消截止时间(快照)")
    checkin_count = Column(Integer, default=0, comment="签到次数")

    # 就诊人快照信息
    patient_name = Column(String(50), nullable=True, comment="就诊人姓名(快照)")
    patient_phone = Column(String(20), nullable=True, comment="就诊人手机(快照)")

    # 医生快照信息
    doctor_name = Column(String(50), nullable=True, comment="医生姓名(快照)")
    doctor_title = Column(String(50), nullable=True, comment="医生职称(快照)")
    department_name = Column(String(100), nullable=True, comment="科室名称(快照)")

    # 提醒相关（三级提醒策略）
    reminder_sent = Column(Integer, default=0, comment="是否已发送提醒: 0否 1是（兼容旧版本）")
    reminder_sent_at = Column(DateTime, comment="提醒发送时间（兼容旧版本）")
    reminder_sent_24h = Column(Integer, default=0, comment="24h级别提醒是否已发送: 0否 1是")
    reminder_sent_2h = Column(Integer, default=0, comment="2h级别提醒是否已发送: 0否 1是")
    reminder_sent_30min = Column(Integer, default=0, comment="30min级别提醒是否已发送: 0否 1是")

    # 支付快照
    payment_profile_id = Column(String(36), ForeignKey("payment_profiles.id"), nullable=True, index=True, comment="支付配置ID快照")
    payment_miniapp_instance_id = Column(
        String(36),
        ForeignKey("miniapp_instances.id"),
        nullable=True,
        index=True,
        comment="小程序实例ID快照",
    )
    payment_mode = Column(String(30), nullable=True, comment="支付模式快照")
    payment_app_id = Column(String(100), nullable=True, comment="支付AppID快照")
    payment_mch_id = Column(String(100), nullable=True, comment="支付商户号快照")
    payment_sub_mchid = Column(String(100), nullable=True, comment="支付子商户号快照")
    payment_notify_url = Column(String(255), nullable=True, comment="支付回调地址快照")
    payment_amount = Column(Numeric(10, 2), nullable=True, comment="支付金额(快照)")
    payment_transaction_id = Column(String(100), nullable=True, comment="微信支付交易号/外部订单号")
    paid_at = Column(DateTime, nullable=True, comment="支付完成时间")

    # 退款相关
    refund_status = Column(String(20), nullable=True, comment="退款状态: none/partial_refunded/refunded")
    refund_amount = Column(Numeric(10, 2), nullable=True, default=0, comment="累计退款金额")

    # 关联关系
    tenant = relationship("Tenant", back_populates="appointments")
    schedule = relationship("Schedule", back_populates="appointments")
    patient = relationship("Patient", backref="appointments")
    doctor = relationship("Doctor", backref="appointments")
    payment_profile = relationship("PaymentProfile", backref="appointments")
    payment_miniapp_instance = relationship("MiniappInstance", backref="appointments")

    __table_args__ = (
        {'comment': '预约表（多租户支持）'},
    )
