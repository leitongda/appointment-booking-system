"""
规则管理系统 Schema 定义

包含请求/响应模型的 Pydantic 定义
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, TypeVar, Generic
from datetime import datetime, date, time


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


# ==================== 通用模型 ====================

T = TypeVar('T')


class PageResult(BaseModel, Generic[T]):
    """分页结果"""
    data: List[T] = Field(default_factory=list, description="数据列表")
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
    description: Optional[str] = Field(None, description="描述")
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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ==================== 规则组模型 ====================

class RuleSetBase(BaseModel):
    """规则组基础模型"""
    name: str = Field(..., max_length=200, description="规则组名称")
    enabled: bool = True
    priority: int = Field(100, ge=1, le=999, description="优先级(越小越优先)")
    time_source: str = Field('SERVER', description="时间来源: SERVER/CLIENT")
    timezone_source: str = Field('HOSPITAL', description="时区来源")
    compare_precision: str = Field('SECOND', description="比较精度")
    default_open_inclusive: bool = True
    default_close_inclusive: bool = True
    rounding_mode: str = Field('NONE', description="取整模式")
    clock_skew_tolerance_sec: int = Field(5, ge=0, description="时钟偏差容忍度(秒)")
    description: Optional[str] = Field(None, description="描述")


class RuleSetCreate(RuleSetBase):
    """创建规则组"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    shift_type_ids: List[str] = Field(..., min_length=1, description="适用的班次类型ID列表")
    windows: Optional[List['RuleWindowCreate']] = Field(None, description="时间窗配置")
    booking_policy: Optional['RuleBookingPolicyCreate'] = Field(None, description="预约策略")
    checkin_policy: Optional['RuleCheckinPolicyCreate'] = Field(None, description="签到策略")
    capacity_policy: Optional['RuleCapacityPolicyCreate'] = Field(None, description="容量策略")


class RuleSetUpdate(BaseModel):
    """更新规则组"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    name: Optional[str] = Field(None, max_length=200)
    enabled: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=1, le=999)
    description: Optional[str] = None
    time_source: Optional[str] = None
    timezone_source: Optional[str] = None
    compare_precision: Optional[str] = None
    default_open_inclusive: Optional[bool] = None
    default_close_inclusive: Optional[bool] = None
    rounding_mode: Optional[str] = None
    clock_skew_tolerance_sec: Optional[int] = Field(None, ge=0)
    shift_type_ids: Optional[List[str]] = None


class RuleSetResponse(RuleSetBase):
    """规则组响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True
    )

    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class RuleSetDetailResponse(RuleSetResponse):
    """规则组详情响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True
    )

    shift_types: List[ShiftTypeResponse] = []
    windows: List['RuleWindowResponse'] = []
    booking_policy: Optional['RuleBookingPolicyResponse'] = None
    checkin_policy: Optional['RuleCheckinPolicyResponse'] = None
    capacity_policy: Optional['RuleCapacityPolicyResponse'] = None


# ==================== 时间窗模型 ====================

class RuleWindowBase(BaseModel):
    """时间窗基础模型"""
    action: str = Field(..., description="动作类型: BOOK/CHECKIN/CANCEL")
    reference_point: str = Field(..., description="参考点: SHIFT_START/SHIFT_END/BOOKING_CREATED_AT")
    open_offset_sec: int = Field(..., description="开放偏移(秒)")
    close_offset_sec: int = Field(..., description="截止偏移(秒)")
    open_inclusive: Optional[bool] = Field(None, description="开放边界包含")
    close_inclusive: Optional[bool] = Field(None, description="截止边界包含")
    fail_policy: str = Field('REJECT', description="失败策略: REJECT/ALLOW_WITH_TAG/AUTO_TO_WAITLIST")
    fail_tag: Optional[str] = Field(None, max_length=100, description="失败标签")
    enabled: bool = True
    description: Optional[str] = None


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

    open_offset_sec: Optional[int] = None
    close_offset_sec: Optional[int] = None
    open_inclusive: Optional[bool] = None
    close_inclusive: Optional[bool] = None
    fail_policy: Optional[str] = None
    fail_tag: Optional[str] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None


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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ==================== 策略模型 ====================

class RuleBookingPolicyBase(BaseModel):
    """预约策略基础模型"""
    require_auth: bool = True
    require_patient_profile_complete: bool = False
    per_user_per_shift: int = Field(1, ge=0, description="每用户每班次最大预约数")
    per_user_per_day: Optional[int] = Field(None, ge=0, description="每用户每天最大预约数")
    per_user_per_week: Optional[int] = Field(None, ge=0, description="每用户每周最大预约数")
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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class RuleCheckinPolicyBase(BaseModel):
    """签到策略基础模型"""
    require_booking: bool = True
    allow_onsite_booking: bool = False
    max_times: int = Field(1, ge=1, description="允许签到次数")
    audit_log: bool = True
    grace_period_sec: int = Field(0, ge=0, description="宽限期(秒)")
    after_grace_status: Optional[str] = Field(None, description="宽限后状态: LATE/ON_TIME")
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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class RuleCapacityPolicyBase(BaseModel):
    """容量策略基础模型"""
    total_capacity: int = Field(0, ge=0, description="总容量,0表示不限制")
    per_user_capacity: int = Field(1, ge=1, description="每用户容量")
    waitlist_enabled: bool = False
    waitlist_max_size: int = Field(0, ge=0, description="候补队列最大长度")
    waitlist_promote_policy: str = Field('MANUAL', description="候补递补策略: MANUAL/AUTO")
    overbooking_enabled: bool = False
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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


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
    current_time: Optional[datetime] = Field(None, description="当前时间(可选,默认使用服务器时间)")


class WindowCheckResult(BaseModel):
    """窗口检查结果"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True
    )

    allowed: bool
    open_at: datetime
    close_at: datetime
    current_time: datetime
    fail_policy: str
    fail_tag: Optional[str] = None
    message: str


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


# 更新前向引用
RuleSetCreate.model_rebuild()
RuleSetUpdate.model_rebuild()
RuleSetDetailResponse.model_rebuild()
