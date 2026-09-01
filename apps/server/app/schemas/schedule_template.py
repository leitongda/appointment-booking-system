from datetime import date, datetime, time

from pydantic import Field

from app.enums.schedule import AppointmentType, ScheduleMode  # noqa: F401 — re-export
from app.schemas.base import BaseRequestSchema, BaseSchema


class BreakTime(BaseRequestSchema):
    """排除时间段（如午休时间）"""

    start_time: time = Field(..., description="开始时间")
    end_time: time = Field(..., description="结束时间")

class ScheduleTemplateBase(BaseRequestSchema):
    """排班模板基础模型"""

    name: str = Field(..., max_length=100, description="模板名称")
    store_id: str = Field(..., description="门店ID")
    doctor_id: str = Field(..., description="医生ID")
    department_id: str = Field(..., description="科室ID")
    shift_type_id: str = Field(..., description="班次类型ID")
    rule_set_id: str | None = Field(None, description="关联规则组ID（可选，指定后使用该规则组而非按班次类型匹配）")
    weekdays: list[int] = Field(..., description="星期数组 1-7，如[1,2,3,4,5]")
    appointment_type: AppointmentType = Field(default=AppointmentType.NORMAL, description="预约类型")
    start_time: time = Field(..., description="开始时间")
    end_time: time = Field(..., description="结束时间")
    slot_count: int = Field(default=1, ge=1, le=50, description="班次数量")
    slot_capacity: int = Field(default=10, ge=1, le=200, description="每班次人数")
    schedule_mode: ScheduleMode = Field(default=ScheduleMode.WEEKLY, description="排班方式")
    break_times: list[BreakTime] | None = Field(None, description="排除时间段列表（如午休时间）")

class ScheduleTemplateCreate(ScheduleTemplateBase):
    """创建排班模板"""
    pass

class ScheduleTemplateUpdate(BaseRequestSchema):
    """更新排班模板"""

    name: str | None = Field(None, max_length=100, description="模板名称")
    store_id: str | None = None
    doctor_id: str | None = None
    department_id: str | None = None
    shift_type_id: str | None = None
    rule_set_id: str | None = Field(None, description="关联规则组ID")
    weekdays: list[int] | None = Field(None, description="星期数组 1-7")
    appointment_type: AppointmentType | None = None
    start_time: time | None = None
    end_time: time | None = None
    slot_count: int | None = Field(None, ge=1, le=50)
    slot_capacity: int | None = Field(None, ge=1, le=200)
    schedule_mode: ScheduleMode | None = None
    break_times: list[BreakTime] | None = Field(None, description="排除时间段列表（如午休时间）")
    status: int | None = Field(None, ge=0, le=1)

class ScheduleTemplateResponse(BaseSchema):
    """排班模板响应"""

    id: str
    name: str | None = None
    store_id: str | None = None
    doctor_id: str | None = None
    department_id: str | None = None
    shift_type_id: str | None = None
    rule_set_id: str | None = None
    weekdays: list[int] | None = None
    appointment_type: str | None = "normal"
    start_time: time | None = None
    end_time: time | None = None
    slot_count: int | None = 1
    slot_capacity: int | None = 10
    schedule_mode: str | None = "weekly"
    break_times: list[BreakTime] | None = None
    status: int | None = 1
    store_name: str | None = None
    doctor_name: str | None = None
    department_name: str | None = None
    shift_type_name: str | None = None
    rule_set_name: str | None = None
    last_generated_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class ScheduleGenerateRequest(BaseRequestSchema):
    """根据模板生成排班请求"""

    template_ids: list[str] = Field(..., description="模板ID列表")
    start_date: date | None = Field(None, description="开始日期，为空则默认今天")
    end_date: date | None = Field(None, description="结束日期，为空则默认1年后")

class ScheduleBatchAddRequest(BaseRequestSchema):
    """批量添加排班请求（不依赖模板）"""

    store_id: str = Field(..., description="门店ID")
    doctor_id: str = Field(..., description="医生ID")
    department_id: str = Field(..., description="科室ID")
    shift_type_id: str = Field(..., description="班次类型ID")
    appointment_type: AppointmentType = Field(default=AppointmentType.NORMAL, description="预约类型")
    start_time: time = Field(..., description="开始时间")
    end_time: time = Field(..., description="结束时间")
    slot_count: int = Field(default=1, ge=1, le=50, description="班次数量")
    slot_capacity: int = Field(default=10, ge=1, le=200, description="每班次人数")
    schedule_mode: ScheduleMode = Field(default=ScheduleMode.WEEKLY, description="排班方式")
    break_times: list[BreakTime] | None = Field(None, description="排除时间段列表（如午休时间）")
    weekdays: list[int] = Field(..., description="星期列表 1-7")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")

class ScheduleSlotPreview(BaseRequestSchema):
    """班次预览项"""

    schedule_date: date = Field(..., description="排班日期")
    start_time: time = Field(..., description="开始时间")
    end_time: time = Field(..., description="结束时间")
    time_slot: str = Field(..., description="时段: morning/afternoon/evening")
    period_name: str = Field(..., description="时段名称: 上午/下午/晚上 或自定义")
    slot_capacity: int = Field(..., description="可预约人数")
    weekday: int = Field(..., description="星期几 1-7")
    weekday_name: str = Field(..., description="星期名称")
    rule_validation: list[str] | None = Field(default=None, description="规则校验警告列表，null表示未校验")
    action: str = Field("create", description="操作类型: create将创建/skip_exists已存在跳过/skip_overlap时间重叠/skip_rest_day休息日/skip_rule规则限制")
    reason: str | None = Field(None, description="跳过原因描述")
    conflicting_schedule_id: str | None = Field(None, description="冲突排班ID（如有）")

class SchedulePreviewGenerateRequest(BaseRequestSchema):
    """预览生成排班请求"""

    template_ids: list[str] = Field(..., description="模板ID列表")
    start_date: date | None = Field(None, description="开始日期，为空则默认今天")
    end_date: date | None = Field(None, description="结束日期，为空则默认30天后")

class SchedulePreviewGenerateResponse(BaseRequestSchema):
    """预览生成排班响应"""

    slots: list[ScheduleSlotPreview] = Field(..., description="预览班次列表")
    total_count: int = Field(..., description="总班次数")
    create_count: int = Field(0, description="将创建数量")
    skip_count: int = Field(0, description="跳过数量（已存在/休息日/规则限制等）")
    conflict_count: int = Field(0, description="时间重叠冲突数量")
    daily_duration_hours: int | None = Field(None, description="每日总时长（小时）")
    daily_duration_minutes: int | None = Field(None, description="每日总时长（剩余分钟数）")
    template_id: str = Field(..., description="模板ID")
    template_name: str = Field(..., description="模板名称")
    doctor_name: str | None = None
    department_name: str | None = None

class SlotCapacityOverride(BaseRequestSchema):
    """班次容量覆盖"""

    schedule_date: date = Field(..., description="排班日期")
    start_time: time = Field(..., description="开始时间")
    end_time: time = Field(..., description="结束时间")
    slot_capacity: int = Field(..., ge=1, le=200, description="可预约人数")

class ScheduleGenerateWithCapacityRequest(BaseRequestSchema):
    """带自定义容量的生成排班请求"""

    template_ids: list[str] = Field(..., description="模板ID列表")
    start_date: date | None = Field(None, description="开始日期，为空则默认今天")
    end_date: date | None = Field(None, description="结束日期，为空则默认1年后")
    slot_capacities: list[SlotCapacityOverride] | None = Field(None, description="自定义班次容量列表")

class ScheduleTemplateCopyRequest(BaseRequestSchema):
    """复制排班规则请求"""

    target_doctor_ids: list[str] = Field(..., description="目标医生ID列表")
    # 可调整的配置字段（覆盖原规则配置）
    name: str | None = Field(None, max_length=100, description="规则名称（可选，不填则自动生成）")
    shift_type_id: str | None = Field(None, description="班次类型ID")
    rule_set_id: str | None = Field(None, description="关联规则组ID")
    weekdays: list[int] | None = Field(None, description="星期数组 1-7")
    appointment_type: str | None = Field(None, description="预约类型")
    start_time: time | None = Field(None, description="开始时间")
    end_time: time | None = Field(None, description="结束时间")
    slot_count: int | None = Field(None, ge=1, le=50, description="班次数量")
    slot_capacity: int | None = Field(None, ge=1, le=200, description="每班次人数")
    schedule_mode: str | None = Field(None, description="排班方式")
    break_times: list[BreakTime] | None = Field(None, description="排除时间段列表")

class ScheduleTemplateCopyResponse(BaseRequestSchema):
    """复制排班规则响应"""

    message: str = Field(..., description="提示消息")
    created_count: int = Field(..., description="创建数量")

class CrossStoreDoctorMapping(BaseRequestSchema):
    """跨院区复制时的医生映射项"""

    source_department_id: str = Field(..., description="源科室ID")
    target_department_id: str = Field(..., description="目标科室ID")
    target_doctor_id: str = Field(..., description="目标医生ID")

class ScheduleTemplateCrossStoreCopyRequest(BaseRequestSchema):
    """跨院区复制排班规则请求"""

    target_store_id: str = Field(..., description="目标门店ID")
    mappings: list[CrossStoreDoctorMapping] = Field(..., description="科室/医生映射列表")
    # 可调整的配置字段（覆盖原规则配置）
    name: str | None = Field(None, max_length=100, description="规则名称（可选，不填则自动生成）")
    shift_type_id: str | None = Field(None, description="班次类型ID")
    rule_set_id: str | None = Field(None, description="关联规则组ID")
    weekdays: list[int] | None = Field(None, description="星期数组 1-7")
    appointment_type: str | None = Field(None, description="预约类型")
    start_time: time | None = Field(None, description="开始时间")
    end_time: time | None = Field(None, description="结束时间")
    slot_count: int | None = Field(None, ge=1, le=50, description="班次数量")
    slot_capacity: int | None = Field(None, ge=1, le=200, description="每班次人数")
    schedule_mode: str | None = Field(None, description="排班方式")
    break_times: list[BreakTime] | None = Field(None, description="排除时间段列表")

class ScheduleTemplateCrossStoreCopyResponse(BaseRequestSchema):
    """跨院区复制排班规则响应"""

    message: str = Field(..., description="提示消息")
    created_count: int = Field(..., description="创建数量")
    failed_mappings: list[CrossStoreDoctorMapping] | None = Field(None, description="失败的映射列表")
