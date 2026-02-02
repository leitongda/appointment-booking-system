"""
规则管理系统数据模型

包含:
- ShiftType: 班次类型
- RuleSet: 规则组
- RuleSetShiftType: 规则组与班次类型关联
- RuleWindow: 时间窗配置
- RuleBookingPolicy: 预约策略
- RuleCheckinPolicy: 签到策略
- RuleCapacityPolicy: 容量策略
- AppointmentCheckin: 签到日志
"""
from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, Index, DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base, AuditMixin
from datetime import datetime
import uuid


class ShiftType(Base, AuditMixin):
    """班次类型表"""
    __tablename__ = "shift_types"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), unique=True, nullable=False, comment="类型代码: OPD/CHECKUP/EXAM/NURSING/SPECIAL")
    name = Column(String(100), nullable=False, comment="类型名称")
    description = Column(Text, comment="描述")
    enabled = Column(Boolean, nullable=False, default=True, comment="是否启用")

    # 关联关系
    schedules = relationship("Schedule", backref="shift_type")
    rule_sets = relationship("RuleSet", secondary="rule_set_shift_types", back_populates="shift_types")


class RuleSet(Base, AuditMixin):
    """规则组表"""
    __tablename__ = "rule_sets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False, comment="规则组名称")
    enabled = Column(Boolean, nullable=False, default=True, comment="是否启用")
    priority = Column(Integer, nullable=False, default=100, comment="优先级(越小越优先)")

    # 默认口径
    time_source = Column(String(20), nullable=False, default='SERVER', comment="时间来源: SERVER/CLIENT")
    timezone_source = Column(String(20), nullable=False, default='HOSPITAL', comment="时区来源: HOSPITAL/SHIFT/USER")
    compare_precision = Column(String(20), nullable=False, default='SECOND', comment="比较精度: SECOND/MILLISECOND/MINUTE")
    default_open_inclusive = Column(Boolean, nullable=False, default=True, comment="默认开放边界包含")
    default_close_inclusive = Column(Boolean, nullable=False, default=False, comment="默认截止边界包含(与前端默认值一致)")
    rounding_mode = Column(String(30), nullable=False, default='NONE', comment="取整模式")
    clock_skew_tolerance_sec = Column(Integer, nullable=False, default=5, comment="时钟偏差容忍度(秒)")

    description = Column(Text, comment="描述")

    # 关联关系
    shift_types = relationship("ShiftType", secondary="rule_set_shift_types", back_populates="rule_sets")
    windows = relationship("RuleWindow", back_populates="rule_set", cascade="all, delete-orphan")
    booking_policy = relationship("RuleBookingPolicy", back_populates="rule_set", uselist=False, cascade="all, delete-orphan")
    checkin_policy = relationship("RuleCheckinPolicy", back_populates="rule_set", uselist=False, cascade="all, delete-orphan")
    capacity_policy = relationship("RuleCapacityPolicy", back_populates="rule_set", uselist=False, cascade="all, delete-orphan")

    # 反向关联
    appointments = relationship("Appointment", backref="rule_set")

    __table_args__ = (
        Index('idx_rule_sets_enabled_priority', 'enabled', 'priority'),
    )


class RuleSetShiftType(Base):
    """规则组与班次类型关联表"""
    __tablename__ = "rule_set_shift_types"

    rule_set_id = Column(String(36), ForeignKey("rule_sets.id", ondelete="CASCADE"), primary_key=True)
    shift_type_id = Column(String(36), ForeignKey("shift_types.id", ondelete="CASCADE"), primary_key=True)

    __table_args__ = (
        Index('idx_rsst_shift_type', 'shift_type_id'),
    )


class RuleWindow(Base, AuditMixin):
    """时间窗配置表"""
    __tablename__ = "rule_windows"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_set_id = Column(String(36), ForeignKey("rule_sets.id", ondelete="CASCADE"), nullable=False)

    action = Column(String(30), nullable=False, comment="动作类型: BOOK/CHECKIN/CANCEL/HOLD_RELEASE")
    reference_point = Column(String(50), nullable=False, comment="参考点: SHIFT_START/SHIFT_END/BOOKING_CREATED_AT")

    open_offset_sec = Column(Integer, nullable=True, comment="开放偏移(秒),可负可正,NULL表示不限制")
    close_offset_sec = Column(Integer, nullable=True, comment="截止偏移(秒),可负可正,NULL表示不限制")

    open_inclusive = Column(Boolean, comment="开放边界包含,NULL则使用规则组默认值")
    close_inclusive = Column(Boolean, comment="截止边界包含,NULL则使用规则组默认值")

    fail_policy = Column(String(30), nullable=False, default='REJECT', comment="失败策略: REJECT/ALLOW_WITH_TAG/AUTO_TO_WAITLIST")
    fail_tag = Column(String(100), comment="失败标签")

    enabled = Column(Boolean, nullable=False, default=True, comment="是否启用")
    description = Column(Text, comment="描述")

    # 关联关系
    rule_set = relationship("RuleSet", back_populates="windows")

    __table_args__ = (
        Index('idx_rule_windows_rs', 'rule_set_id', 'enabled'),
    )


class RuleBookingPolicy(Base, AuditMixin):
    """预约策略表"""
    __tablename__ = "rule_booking_policies"

    rule_set_id = Column(String(36), ForeignKey("rule_sets.id", ondelete="CASCADE"), primary_key=True)

    require_auth = Column(Boolean, nullable=False, default=True, comment="是否要求登录")
    require_patient_profile_complete = Column(Boolean, nullable=False, default=False, comment="是否要求档案完整")

    per_user_per_shift = Column(Integer, nullable=False, default=1, comment="每用户每班次最大预约数")
    per_user_per_day = Column(Integer, comment="每用户每天最大预约数")
    per_user_per_week = Column(Integer, comment="每用户每周最大预约数")

    conflict_same_shift = Column(String(20), nullable=False, default='REJECT', comment="同一班次冲突策略: REJECT/REPLACE")
    conflict_overlap_time = Column(String(20), nullable=False, default='REJECT', comment="时间重叠冲突策略: REJECT/ALLOW")
    conflict_same_type_same_day = Column(String(20), nullable=False, default='ALLOW', comment="同类型同日冲突策略: REJECT/ALLOW")

    # 关联关系
    rule_set = relationship("RuleSet", back_populates="booking_policy")


class RuleCheckinPolicy(Base, AuditMixin):
    """签到策略表"""
    __tablename__ = "rule_checkin_policies"

    rule_set_id = Column(String(36), ForeignKey("rule_sets.id", ondelete="CASCADE"), primary_key=True)

    require_booking = Column(Boolean, nullable=False, default=True, comment="是否必须预约")
    allow_onsite_booking = Column(Boolean, nullable=False, default=False, comment="是否允许现场补约")
    max_times = Column(Integer, nullable=False, default=1, comment="允许签到次数")

    audit_log = Column(Boolean, nullable=False, default=True, comment="是否记录审计日志")

    grace_period_sec = Column(Integer, nullable=False, default=0, comment="宽限期(秒)")
    after_grace_status = Column(String(30), comment="宽限后状态: LATE/ON_TIME")
    no_checkin_after_close = Column(String(30), nullable=False, default='KEEP_BOOKED', comment="截止后未签到处理: KEEP_BOOKED/AUTO_CANCEL/ABSENT")

    # 关联关系
    rule_set = relationship("RuleSet", back_populates="checkin_policy")


class RuleCapacityPolicy(Base, AuditMixin):
    """容量策略表"""
    __tablename__ = "rule_capacity_policies"

    rule_set_id = Column(String(36), ForeignKey("rule_sets.id", ondelete="CASCADE"), primary_key=True)

    total_capacity = Column(Integer, nullable=False, default=0, comment="总容量,0表示不限制")
    per_user_capacity = Column(Integer, nullable=False, default=1, comment="每用户容量")

    waitlist_enabled = Column(Boolean, nullable=False, default=False, comment="是否启用候补")
    waitlist_max_size = Column(Integer, nullable=False, default=0, comment="候补队列最大长度")
    waitlist_promote_policy = Column(String(50), nullable=False, default='MANUAL', comment="候补递补策略: MANUAL/AUTO")

    overbooking_enabled = Column(Boolean, nullable=False, default=False, comment="是否允许超额")
    overbooking_max = Column(Integer, nullable=False, default=0, comment="超额最大数量")

    # 关联关系
    rule_set = relationship("RuleSet", back_populates="capacity_policy")


class AppointmentCheckin(Base):
    """签到日志表"""
    __tablename__ = "appointment_checkins"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    appointment_id = Column(String(36), ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False)

    checkin_time = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(), comment="签到时间")
    checkin_method = Column(String(30), nullable=False, comment="签到方式: QR_CODE/MANUAL/PHONE")
    device_info = Column(String(200), comment="设备信息")
    location_info = Column(String(200), comment="位置信息")
    operator_id = Column(String(36), comment="操作人ID")
    operator_type = Column(String(20), comment="操作人类型: USER/ADMIN/DOCTOR")
    status = Column(String(20), nullable=False, default='SUCCESS', comment="状态: SUCCESS/FAILED/CANCELLED")
    fail_reason = Column(String(200), comment="失败原因")

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now())

    # 关联关系
    appointment = relationship("Appointment", backref="checkin_logs")

    __table_args__ = (
        Index('idx_app_checkins_appointment', 'appointment_id'),
        Index('idx_app_checkins_time', 'checkin_time'),
    )
