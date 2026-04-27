from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import date, time, datetime
from app.schemas.schedule_template import AppointmentType
from app.core.config import settings


from enum import Enum


def to_camel(string: str) -> str:
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class ScheduleBase(BaseModel):
    """排班基础模型"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


    doctor_id: str = Field(..., description="医生ID")
    store_id: Optional[str] = Field(None, description="门店ID")
    schedule_date: date = Field(..., description="排班日期")
    time_slot: Optional[str] = Field(None, pattern="^(morning|afternoon|evening)$", description="时段: morning上午/afternoon下午/evening晚间")
    start_time: Optional[time] = Field(None, description="开始时间")
    end_time: Optional[time] = Field(None, description="结束时间")
    total_slots: int = Field(10, ge=1, le=200, description="总号源数量")
    appointment_type: str = Field(default="normal", description="预约类型: normal普通/urgent加急/expert专家")
    status: int = Field(1, ge=0, le=1, description="状态: 0停用 1启用")


class ScheduleCreate(ScheduleBase):
    template_id: Optional[str] = Field(None, description="来源模板ID")


class ScheduleBatchCreate(ScheduleBase):
    """批量创建排班请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    doctor_id: str = Field(..., description="医生ID")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    time_slots: List[str] = Field(..., description="时段列表: morning/afternoon/evening")
    total_slots: int = Field(10, ge=1, description="每个时段的号源数量")
    weekdays: List[int] = Field(..., description="星期列表: 1周一 2周二 ... 7周日")


    appointment_type: Optional[str] = Field(None, description="预约类型")


    status: Optional[int] = Field(1, ge=0, le=1, description="状态")


class ScheduleUpdate(BaseModel):
    """更新排班请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    total_slots: Optional[int] = Field(None, ge=1, le=200, description="总号源数量")
    start_time: Optional[time] = Field(None, description="开始时间")
    end_time: Optional[time] = Field(None, description="结束时间")
    appointment_type: Optional[str] = Field(None, description="预约类型: normal普通/urgent加急/expert专家")
    status: Optional[int] = Field(None, ge=0, le=1, description="状态: 0停用 1启用")


class ScheduleResponse(ScheduleBase):
    """排班信息响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )

    id: str = Field(..., description="排班ID")
    doctor_id: str = Field(..., description="医生ID")
    store_id: Optional[str] = Field(None, description="门店ID")
    schedule_date: date = Field(..., description="排班日期")
    time_slot: Optional[str] = Field(None, description="时段: morning上午/afternoon下午/evening晚间")
    start_time: Optional[time] = Field(None, description="开始时间")
    end_time: Optional[time] = Field(None, description="结束时间")
    total_slots: int = Field(10, description="总号源数量")
    booked_slots: int = Field(0, description="已预约号源数量")
    appointment_type: str = Field("normal", description="预约类型: normal普通/urgent加急/expert专家")
    status: int = Field(1, description="状态: 0停用 1启用")
    template_id: Optional[str] = Field(None, description="来源模板ID")
    doctor_name: Optional[str] = Field(None, description="医生姓名")
    department_name: Optional[str] = Field(None, description="科室名称")
    store_name: Optional[str] = Field(None, description="门店名称")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    is_rest_day: bool = Field(False, description="是否在休息日")


class AvailableScheduleResponse(ScheduleResponse):
    """可预约排班信息响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )


    id: str = Field(..., description="排班ID")
    schedule_date: date = Field(..., description="排班日期")
    time_slot: Optional[str] = Field(None, description="时段: morning上午/afternoon下午/evening晚间")
    available_slots: int = Field(0, description="剩余可预约号源数量")
    start_time: Optional[time] = Field(None, description="开始时间")
    end_time: Optional[time] = Field(None, description="结束时间")
    appointment_type: str = Field("normal", description="预约类型: normal普通/urgent加急/expert专家")
    # 规则引擎相关
    total_slots: int = Field(0, description="总号源数量")
    booking_open_at: Optional[datetime] = Field(None, description="预约开放时间")
    booking_close_at: Optional[datetime] = Field(None, description="预约截止时间")
    booking_status: str = Field("available", description="预约状态: available可预约/closing_soon即将截止/full已满/closed已关闭/not_open未开放")
    capacity_percent: float = Field(100.0, description="容量百分比(0-100)")
    urgency_level: str = Field("normal", description="紧急程度: normal普通/medium中等/high高/critical紧急")

    # 排班优先级相关
    template_id: Optional[str] = Field(None, description="来源模板ID，为空表示自定义排班")
    is_rest_day: bool = Field(False, description="是否在休息日")


class BatchOperationResult(BaseModel):
    """批量操作结果"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    success_count: int = Field(0, description="成功数量")
    failed_count: int = Field(0, description="失败数量")
    success_ids: List[str] = Field(default_factory=list, description="成功的ID列表")
    failed_items: List[dict] = Field(default_factory=list, description="失败项列表")
    message: str = Field(..., description="操作消息")


class BatchDeleteResult(BatchOperationResult):
    """批量删除结果"""
    deleted_count: int = Field(..., description="已删除数量")
    skipped_ids: List[str] = Field(default_factory=list, description="跳过的ID列表（有预约记录）")
    failed_items: List[dict] = Field(default_factory=list, description="失败项列表")


class BatchSuspensionResult(BatchOperationResult):
    """批量停诊结果"""
    suspended_count: int = Field(..., description="已停诊数量")
    success_ids: List[str] = Field(default_factory=list, description="成功的ID列表")
    failed_items: List[dict] = Field(default_factory=list, description="失败项列表")


class BatchResumeResult(BatchOperationResult):
    """批量复诊结果"""
    resumed_count: int = Field(..., description="已复诊数量")
    success_ids: List[str] = Field(default_factory=list, description="成功的ID列表")
    failed_items: List[dict] = Field(default_factory=list, description="失败项列表")


class ScheduleBatchOperationResponse(BatchOperationResult):
    """排班批量操作响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )

    total_created: int = Field(..., description="总共创建数量")
    total_skipped: int = Field(..., description="总共跳过数量")
    total_failed: int = Field(..., description="总共失败数量")
    created_items: List[dict] = Field(default_factory=list, description="创建项列表")
    skipped_items: List[dict] = Field(default_factory=list, description="跳过项列表")
    failed_items: List[dict] = Field(default_factory=list, description="失败项列表")
    # 模板相关
    template_id: Optional[str] = Field(None, description="模板ID")
    template_name: Optional[str] = Field(None, description="模板名称")


    doctor_id: Optional[str] = Field(None, description="医生ID")
    date_range: Optional[str] = Field(None, description="日期范围")


    created_count: Optional[int] = Field(None, description="创建数量")
    skipped_count: Optional[int] = Field(None, description="跳过数量")
    error: Optional[str] = Field(None, description="错误信息")


# ========== 自定义排班相关 Schema（原 custom_schedule.py） ==========


class TimePeriod(BaseModel):
    """时间段配置"""
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    start_time: time = Field(..., description="开始时间")
    end_time: time = Field(..., description="结束时间")
    appointment_type: AppointmentType = Field(..., description="预约类型")
    slot_count: Optional[int] = Field(None, ge=1, le=50, description="排班数量(均分数量),不填则不均分")
    max_patients: int = Field(1, ge=1, le=100, description="预约人数(每个班次)")


class CustomScheduleCreate(BaseModel):
    """创建自定义排班"""
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    store_id: str = Field(..., description="门店ID")
    department_id: str = Field(..., description="科室ID")
    doctor_id: str = Field(..., description="医生ID")
    schedule_dates: List[date] = Field(..., min_length=1, description="排班日期列表(支持多选)")
    time_periods: List[TimePeriod] = Field(..., min_length=1, description="排班时段配置列表")


class CustomScheduleResponse(BaseModel):
    """自定义排班响应"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )

    id: str = Field(..., description="排班ID")
    store_id: str = Field(..., description="门店ID")
    store_name: Optional[str] = Field(None, description="门店名称")
    department_id: str = Field(..., description="科室ID")
    department_name: Optional[str] = Field(None, description="科室名称")
    doctor_id: str = Field(..., description="医生ID")
    doctor_name: Optional[str] = Field(None, description="医生名称")
    schedule_date: date = Field(..., description="排班日期")
    start_time: time = Field(..., description="开始时间")
    end_time: time = Field(..., description="结束时间")
    appointment_type: str = Field(..., description="预约类型")
    max_patients: int = Field(..., description="最大预约人数")
    booked_count: int = Field(..., description="已预约人数")
    status: int = Field(..., description="状态")
    created_at: datetime = Field(..., description="创建时间")
    is_rest_day: Optional[bool] = Field(False, description="是否在休息日")


class CustomScheduleListParams(BaseModel):
    """查询自定义排班列表参数"""
    store_id: Optional[str] = Field(None, description="门店ID")
    department_id: Optional[str] = Field(None, description="科室ID")
    doctor_id: Optional[str] = Field(None, description="医生ID")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")
    appointment_type: Optional[AppointmentType] = Field(None, description="预约类型")
    status: Optional[int] = Field(None, ge=0, le=1, description="状态")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量")


class EffectiveScheduleParams(BaseModel):
    """查询生效班次参数"""
    store_id: Optional[str] = Field(None, description="门店ID")
    doctor_id: Optional[str] = Field(None, description="医生ID")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
