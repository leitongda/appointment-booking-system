from app.schemas.response import to_camel

"""
规则管理系统 Schema 定义

包含请求/响应模型的 Pydantic 定义
"""
from datetime import date, datetime, time
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

# ==================== 通用模型 ====================

T = TypeVar('T')

class PageResult(BaseModel, Generic[T]):
    """分页结果"""
    data: list[T] = Field(default_factory=list, description="数据列表")
    total: int = Field(0, description="总数")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True
    )

# ==================== 基础模型 ====================

class ShiftTypeBase(BaseModel):
    """班次类型基础模型"""
    code: str = Field(..., max_length=50, description="类型代码")
    name: str = Field(..., max_length=100, description="类型名称")
    description: str | None = Field(None, description="描述")
    enabled: bool = True

class ShiftTypeResponse(ShiftTypeBase):
    """班次类型响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True
    )

    id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

# ==================== 规则组模型 ====================

class RuleSetBase(BaseModel):
    """规则组基础模型"""
    name: str = Field(..., max_length=200, description="规则组名称")
    enabled: bool = Field(True, description="是否启用")
    priority: int = Field(100, ge=1, le=999, description="优先级(越小越优先)")
    time_source: str = Field('SERVER', description="时间来源: SERVER/CLIENT")
    timezone_source: str = Field('HOSPITAL', description="时区来源")
    compare_precision: str = Field('SECOND', description="比较精度")
    default_open_inclusive: bool = Field(True, description="默认开放边界包含")
    default_close_inclusive: bool = Field(False, description="默认截止边界包含")
    rounding_mode: str = Field('NONE', description="取整模式")
    clock_skew_tolerance_sec: int = Field(5, ge=0, description="时钟偏差容忍度(秒)")
    description: str | None = Field(None, description="描述")
    store_id: str | None = Field(None, description="门店ID")
    department_id: str | None = Field(None, description="科室ID")
    doctor_id: str | None = Field(None, description="医生ID")

class RuleSetCreate(RuleSetBase):
    """创建规则组"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    shift_type_ids: list[str] = Field(..., min_length=1, description="适用的班次类型ID列表")
    windows: list['RuleWindowCreate'] | None = Field(None, description="时间窗配置")
    booking_policy: Optional['RuleBookingPolicyCreate'] = Field(None, description="预约策略")
    checkin_policy: Optional['RuleCheckinPolicyCreate'] = Field(None, description="签到策略")
    capacity_policy: Optional['RuleCapacityPolicyCreate'] = Field(None, description="容量策略")

class RuleSetUpdate(BaseModel):
    """更新规则组"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    name: str | None = Field(None, max_length=200, description="规则组名称")
    enabled: bool | None = Field(None, description="是否启用")
    priority: int | None = Field(None, ge=1, le=999, description="优先级")
    description: str | None = Field(None, description="描述")
    time_source: str | None = Field(None, description="时间来源")
    timezone_source: str | None = Field(None, description="时区来源")
    compare_precision: str | None = Field(None, description="比较精度")
    default_open_inclusive: bool | None = Field(None, description="开放边界包含")
    default_close_inclusive: bool | None = Field(None, description="截止边界包含")
    rounding_mode: str | None = Field(None, description="取整模式")
    clock_skew_tolerance_sec: int | None = Field(None, ge=0, description="时钟偏差容忍度")
    store_id: str | None = Field(None, description="门店ID")
    department_id: str | None = Field(None, description="科室ID")
    doctor_id: str | None = Field(None, description="医生ID")
    shift_type_ids: list[str] | None = Field(None, description="班次类型ID列表")
    windows: list['RuleWindowCreate'] | None = Field(None, description="时间窗配置")
    booking_policy: Optional['RuleBookingPolicyCreate'] = Field(None, description="预约策略")
    checkin_policy: Optional['RuleCheckinPolicyCreate'] = Field(None, description="签到策略")
    capacity_policy: Optional['RuleCapacityPolicyCreate'] = Field(None, description="容量策略")
    expected_updated_at: datetime | None = Field(None, description="乐观锁：期望的最后更新时间")

class RuleSetResponse(RuleSetBase):
    """规则组响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True
    )

    id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    is_active: bool = Field(False, description="是否为实际生效的规则组（优先级最高的启用规则）")
    store_name: str | None = Field(None, description="门店名称")
    department_name: str | None = Field(None, description="科室名称")
    doctor_name: str | None = Field(None, description="医生姓名")

class ScheduleTemplateBrief(BaseModel):
    """排班模板简要信息（用于规则组关联展示）"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )

    id: str
    name: str | None = None
    doctor_name: str | None = None
    department_name: str | None = None
    store_name: str | None = None
    shift_type_name: str | None = None
    status: int | None = 1

class RuleSetDetailResponse(RuleSetResponse):
    """规则组详情响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True
    )

    shift_types: list[ShiftTypeResponse] = []
    windows: list['RuleWindowResponse'] = []
    booking_policy: Optional['RuleBookingPolicyResponse'] = None
    checkin_policy: Optional['RuleCheckinPolicyResponse'] = None
    capacity_policy: Optional['RuleCapacityPolicyResponse'] = None
    schedule_templates: list[ScheduleTemplateBrief] = []

# ==================== 时间窗模型 ====================

class RuleWindowBase(BaseModel):
    """时间窗基础模型"""
    name: str | None = Field(None, max_length=200, description="时间窗名称")
    action: str = Field(..., description="动作类型: BOOK/CHECKIN/CANCEL")
    reference_point: str = Field(..., description="参考点: SHIFT_START/SHIFT_END/BOOKING_CREATED_AT")
    open_offset_sec: int | None = Field(None, description="开放偏移(秒),NULL表示不限制")
    close_offset_sec: int | None = Field(None, description="截止偏移(秒),NULL表示不限制")
    open_inclusive: bool | None = Field(None, description="开放边界包含")
    close_inclusive: bool | None = Field(None, description="截止边界包含")
    fail_policy: str = Field('REJECT', description="失败策略: REJECT/ALLOW_WITH_TAG/AUTO_TO_WAITLIST")
    fail_tag: str | None = Field(None, max_length=100, description="失败标签")
    enabled: bool = Field(True, description="是否启用")
    description: str | None = Field(None, description="描述")

class RuleWindowCreate(RuleWindowBase):
    """创建时间窗"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

class RuleWindowUpdate(BaseModel):
    """更新时间窗"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    open_offset_sec: int | None = Field(None, description="开放偏移(秒)")
    close_offset_sec: int | None = Field(None, description="截止偏移(秒)")
    open_inclusive: bool | None = Field(None, description="开放边界包含")
    close_inclusive: bool | None = Field(None, description="截止边界包含")
    fail_policy: str | None = Field(None, description="失败策略")
    fail_tag: str | None = Field(None, description="失败标签")
    enabled: bool | None = Field(None, description="是否启用")
    description: str | None = Field(None, description="描述")

class RuleWindowResponse(RuleWindowBase):
    """时间窗响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True
    )

    id: str
    rule_set_id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

# ==================== 策略模型 ====================

class RuleBookingPolicyBase(BaseModel):
    """预约策略基础模型"""
    require_auth: bool = Field(True, description="是否需要认证")
    require_patient_profile_complete: bool = Field(False, description="是否需要完善患者资料")
    per_user_per_shift: int = Field(1, ge=0, description="每用户每班次最大预约数")
    per_user_per_day: int | None = Field(None, ge=0, description="每用户每天最大预约数")
    per_user_per_week: int | None = Field(None, ge=0, description="每用户每周最大预约数")
    conflict_same_shift: str = Field('REJECT', description="同一班次冲突策略: REJECT/REPLACE")
    conflict_overlap_time: str = Field('REJECT', description="时间重叠冲突策略: REJECT/ALLOW")
    conflict_same_type_same_day: str = Field('ALLOW', description="同类型同日冲突策略: REJECT/ALLOW")

class RuleBookingPolicyCreate(RuleBookingPolicyBase):
    """创建预约策略"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

class RuleBookingPolicyResponse(RuleBookingPolicyBase):
    """预约策略响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True
    )

    rule_set_id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

class RuleCheckinPolicyBase(BaseModel):
    """签到策略基础模型"""
    require_booking: bool = Field(True, description="是否需要预约")
    allow_onsite_booking: bool = Field(False, description="允许现场预约")
    max_times: int = Field(1, ge=1, description="允许签到次数")
    audit_log: bool = Field(True, description="是否记录审计日志")
    grace_period_sec: int = Field(0, ge=0, description="宽限期(秒)")
    after_grace_status: str | None = Field(None, description="宽限后状态: LATE/ON_TIME")
    no_checkin_after_close: str = Field('KEEP_BOOKED', description="截止后未签到处理: KEEP_BOOKED/AUTO_CANCEL/ABSENT")

class RuleCheckinPolicyCreate(RuleCheckinPolicyBase):
    """创建签到策略"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

class RuleCheckinPolicyResponse(RuleCheckinPolicyBase):
    """签到策略响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True
    )

    rule_set_id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

class RuleCapacityPolicyBase(BaseModel):
    """容量策略基础模型"""
    total_capacity: int = Field(0, ge=0, description="总容量,0表示不限制")
    per_user_capacity: int = Field(1, ge=1, description="每用户容量")
    waitlist_enabled: bool = Field(False, description="是否启用候补队列")
    waitlist_max_size: int = Field(0, ge=0, description="候补队列最大长度")
    waitlist_promote_policy: str = Field('MANUAL', description="候补递补策略: MANUAL/AUTO")
    overbooking_enabled: bool = Field(False, description="是否允许超额预约")
    overbooking_max: int = Field(0, ge=0, description="超额最大数量")

class RuleCapacityPolicyCreate(RuleCapacityPolicyBase):
    """创建容量策略"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

class RuleCapacityPolicyResponse(RuleCapacityPolicyBase):
    """容量策略响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True
    )

    rule_set_id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

# ==================== 预览模型 ====================

class RulePreviewRequest(BaseModel):
    """规则预览请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    shift_type_id: str = Field(..., description="班次类型ID")
    schedule_date: date = Field(..., description="排班日期")
    start_time: time = Field(..., description="开始时间")
    end_time: time = Field(..., description="结束时间")
    current_time: datetime | None = Field(None, description="当前时间(可选,默认使用服务器时间)")

class WindowCheckResult(BaseModel):
    """窗口检查结果"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True
    )

    allowed: bool = Field(..., description="是否允许操作")
    open_at: datetime = Field(..., description="开放时间")
    close_at: datetime = Field(..., description="截止时间")
    current_time: datetime = Field(..., description="当前时间")
    fail_policy: str = Field(..., description="失败策略")
    fail_tag: str | None = Field(None, description="失败标签")
    message: str = Field(..., description="结果消息")

class RuleSetBrief(BaseModel):
    """规则组简要信息（用于预览匹配结果）"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True
    )

    id: str
    name: str
    priority: int
    enabled: bool

class RulePreviewResponse(BaseModel):
    """规则预览响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True
    )

    book_window: WindowCheckResult
    checkin_window: WindowCheckResult
    cancel_window: WindowCheckResult
    matched_rule_set: RuleSetBrief | None = Field(None, description="匹配到的规则组（优先级最高）")
    candidate_rule_sets: list[RuleSetBrief] = Field(default_factory=list, description="所有候选规则组（按优先级排序）")

# ==================== 预设模板模型 ====================

class RuleSetPresetBase(BaseModel):
    """预设模板基础模型"""
    name: str = Field(..., max_length=100, description="预设名称")
    description: str | None = Field(None, description="描述")
    config: dict[str, Any] = Field(..., description="完整规则组配置")

class RuleSetPresetCreate(RuleSetPresetBase):
    """创建预设模板"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    sort_order: int = Field(0, description="排序")

class RuleSetPresetUpdate(BaseModel):
    """更新预设模板"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    name: str | None = Field(None, max_length=100, description="预设名称")
    description: str | None = Field(None, description="描述")
    config: dict[str, Any] | None = Field(None, description="完整规则组配置")
    sort_order: int | None = Field(None, description="排序")

class RuleSetPresetResponse(BaseModel):
    """预设模板响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True
    )

    id: str
    name: str
    description: str | None = None
    config: dict[str, Any]
    is_system: bool = False
    sort_order: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

# ==================== 审计日志模型 ====================

class RuleSetAuditLogResponse(BaseModel):
    """规则组审计日志响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )

    id: str
    rule_set_id: str
    action: str
    resource_type: str
    resource_id: str
    operator_id: str | None = None
    snapshot_before: str | None = None
    snapshot_after: str | None = None
    changes: str | None = None
    created_at: datetime | None = None

# 更新前向引用
RuleSetCreate.model_rebuild()
RuleSetUpdate.model_rebuild()
RuleSetDetailResponse.model_rebuild()
