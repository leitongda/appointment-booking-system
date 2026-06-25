"""考勤管理核心模型"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


class AttendanceShift(Base, AuditMixin):
    """考勤班次表"""
    __tablename__ = "attendance_shifts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    name = Column(String(100), nullable=False, comment="班次名称")
    code = Column(String(50), nullable=False, comment="班次代码")
    start_time = Column(String(5), nullable=False, comment="上班时间 HH:MM")
    end_time = Column(String(5), nullable=False, comment="下班时间 HH:MM")
    break_start = Column(String(5), nullable=True, comment="午休开始 HH:MM")
    break_end = Column(String(5), nullable=True, comment="午休结束 HH:MM")
    grace_minutes = Column(Integer, default=0, comment="迟到宽限分钟数")
    late_threshold_minutes = Column(Integer, default=0, comment="迟到判定阈值(分钟)")
    early_threshold_minutes = Column(Integer, default=0, comment="早退判定阈值(分钟)")
    is_flexible = Column(Boolean, default=False, comment="是否弹性工作制")
    enabled = Column(Boolean, default=True, comment="是否启用")

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_attendance_shifts_tenant_code"),
        {"comment": "考勤班次表"},
    )


class AttendanceGroup(Base, AuditMixin):
    """签到组表"""
    __tablename__ = "attendance_groups"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    name = Column(String(100), nullable=False, comment="签到组名称")
    description = Column(Text, nullable=True, comment="描述")
    check_method = Column(String(20), default="gps", comment="打卡方式: gps/wifi/device")
    location_lat = Column(Float, nullable=True, comment="纬度")
    location_lng = Column(Float, nullable=True, comment="经度")
    location_radius = Column(Integer, default=300, comment="打卡范围(米)")
    wifi_ssid = Column(String(200), nullable=True, comment="WiFi SSID（单个，向后兼容）")
    wifi_ssids = Column(Text, nullable=True, comment="允许的WiFi SSID列表，逗号分隔")
    device_whitelist = Column(Text, nullable=True, comment="允许的设备ID列表，逗号分隔")
    require_device_bind = Column(Boolean, default=False, comment="是否要求设备绑定")
    enabled = Column(Boolean, default=True, comment="是否启用")

    members = relationship("AttendanceGroupMember", backref="group", cascade="all, delete-orphan")

    __table_args__ = (
        {"comment": "签到组表"},
    )


class AttendanceGroupMember(Base):
    """签到组成员关联表"""
    __tablename__ = "attendance_group_members"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id = Column(String(36), ForeignKey("attendance_groups.id", ondelete="CASCADE"), nullable=False, comment="签到组ID")
    account_id = Column(String(36), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, comment="账号ID")
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    __table_args__ = (
        UniqueConstraint("group_id", "account_id", name="uq_attendance_group_member"),
        {"comment": "签到组成员关联表"},
    )


class AttendanceRecord(Base, AuditMixin):
    """考勤打卡记录表"""
    __tablename__ = "attendance_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False, index=True, comment="账号ID")
    shift_id = Column(String(36), ForeignKey("attendance_shifts.id"), nullable=True, comment="班次ID")
    group_id = Column(String(36), ForeignKey("attendance_groups.id"), nullable=True, comment="签到组ID")
    check_date = Column(Date, nullable=False, comment="打卡日期")
    check_in_time = Column(DateTime, nullable=True, comment="签到时间")
    check_out_time = Column(DateTime, nullable=True, comment="签退时间")
    check_in_lat = Column(Float, nullable=True, comment="签到纬度")
    check_in_lng = Column(Float, nullable=True, comment="签到经度")
    check_out_lat = Column(Float, nullable=True, comment="签退纬度")
    check_out_lng = Column(Float, nullable=True, comment="签退经度")
    check_in_device = Column(String(200), nullable=True, comment="签到设备信息")
    check_out_device = Column(String(200), nullable=True, comment="签退设备信息")
    status = Column(String(20), default="normal", comment="状态: normal/late/early/absent/leave/field_work/expected")
    late_minutes = Column(Integer, default=0, comment="迟到分钟数")
    early_minutes = Column(Integer, default=0, comment="早退分钟数")
    work_hours = Column(Float, nullable=True, comment="工作时长(小时)")
    remark = Column(Text, nullable=True, comment="备注")

    __table_args__ = (
        UniqueConstraint("account_id", "check_date", name="uq_attendance_record_account_date"),
        {"comment": "考勤打卡记录表"},
    )


class AttendanceRule(Base, AuditMixin):
    """考勤规则表"""
    __tablename__ = "attendance_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    name = Column(String(100), nullable=False, comment="规则名称")
    description = Column(Text, nullable=True, comment="描述")
    late_policy = Column(String(20), default="flexible", comment="迟到策略: flexible/strict/ignore")
    early_policy = Column(String(20), default="flexible", comment="早退策略: flexible/strict/ignore")
    absent_policy = Column(String(20), default="strict", comment="缺勤策略: strict/ignore")
    overtime_enabled = Column(Boolean, default=False, comment="是否启用加班计算")
    overtime_min_minutes = Column(Integer, default=30, comment="加班最小分钟数")
    enabled = Column(Boolean, default=True, comment="是否启用")

    __table_args__ = (
        {"comment": "考勤规则表"},
    )


class AttendanceStatDaily(Base, AuditMixin):
    """每日考勤统计表"""
    __tablename__ = "attendance_stat_daily"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False, index=True, comment="账号ID")
    date = Column(Date, nullable=False, comment="统计日期")
    shift_id = Column(String(36), nullable=True, comment="班次ID")
    scheduled_in = Column(String(5), nullable=True, comment="排班上班时间")
    scheduled_out = Column(String(5), nullable=True, comment="排班下班时间")
    actual_in = Column(DateTime, nullable=True, comment="实际签到时间")
    actual_out = Column(DateTime, nullable=True, comment="实际签退时间")
    status = Column(String(20), default="normal", comment="状态: normal/late/early/absent/leave/field_work/expected")
    late_minutes = Column(Integer, default=0, comment="迟到分钟数")
    early_minutes = Column(Integer, default=0, comment="早退分钟数")
    work_hours = Column(Float, nullable=True, comment="工作时长(小时)")
    overtime_hours = Column(Float, default=0, comment="加班时长(小时)")

    __table_args__ = (
        UniqueConstraint("account_id", "date", name="uq_attendance_stat_daily"),
        {"comment": "每日考勤统计表"},
    )


class AttendanceLeaveType(Base, AuditMixin):
    """假期类型表"""
    __tablename__ = "attendance_leave_types"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    name = Column(String(50), nullable=False, comment="假期名称（年假/事假/病假/调休/婚假/产假/陪产假/丧假）")
    code = Column(String(30), nullable=False, comment="假期代码")
    paid = Column(Boolean, default=True, comment="是否带薪")
    default_days = Column(Integer, default=0, comment="默认年假天数（0表示不限）")
    enabled = Column(Boolean, default=True, comment="是否启用")
    sort_order = Column(Integer, default=0, comment="排序")

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_attendance_leave_types_tenant_code"),
        {"comment": "假期类型表"},
    )


class AttendanceLeaveBalance(Base, AuditMixin):
    """假期余额表"""
    __tablename__ = "attendance_leave_balances"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False, index=True, comment="账号ID")
    leave_type_id = Column(String(36), ForeignKey("attendance_leave_types.id"), nullable=False, comment="假期类型ID")
    year = Column(Integer, nullable=False, comment="年度")
    total_days = Column(Float, default=0, comment="总额度天数")
    used_days = Column(Float, default=0, comment="已用天数")

    __table_args__ = (
        UniqueConstraint("account_id", "leave_type_id", "year", name="uq_attendance_leave_balance"),
        {"comment": "假期余额表"},
    )


class AttendanceLeaveRequest(Base, AuditMixin):
    """假期申请表"""
    __tablename__ = "attendance_leave_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False, index=True, comment="申请人ID")
    leave_type_id = Column(String(36), ForeignKey("attendance_leave_types.id"), nullable=False, comment="假期类型ID")
    start_date = Column(Date, nullable=False, comment="开始日期")
    end_date = Column(Date, nullable=False, comment="结束日期")
    duration_days = Column(Float, nullable=False, comment="请假天数")
    reason = Column(Text, nullable=True, comment="请假原因")
    status = Column(String(20), default="pending", comment="状态: pending/approved/rejected/cancelled")
    reviewer_id = Column(String(36), nullable=True, comment="审核人ID")
    review_comment = Column(Text, nullable=True, comment="审核意见")
    reviewed_at = Column(DateTime, nullable=True, comment="审核时间")

    __table_args__ = (
        {"comment": "假期申请表"},
    )
