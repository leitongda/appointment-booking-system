from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime, date, time
from app.core.config import settings


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class AppointmentCreate(BaseModel):
    """创建预约请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "scheduleId": "sch_abc123def456",
                "patientId": "pat_xyz789abc",
                "symptomDescription": "头痛三天，伴有轻微发热"
            }
        }
    )
    
    schedule_id: str = Field(..., description="排班ID", examples=["sch_abc123def456"])
    patient_id: str = Field(..., description="就诊人ID", examples=["pat_xyz789abc"])
    symptom_description: Optional[str] = Field(None, max_length=500, description="病情描述/预填信息", examples=["头痛三天，伴有轻微发热"])


class AppointmentResponse(BaseModel):
    """预约信息响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str = Field(..., description="预约ID")
    appointment_no: Optional[str] = Field(None, description="预约编号")
    user_id: Optional[str] = Field(None, description="用户ID")
    patient_id: Optional[str] = Field(None, description="就诊人ID")
    patient_name: Optional[str] = Field(None, description="就诊人姓名")
    patient_phone: Optional[str] = Field(None, description="就诊人手机号")
    doctor_id: Optional[str] = Field(None, description="医生ID")
    doctor_name: Optional[str] = Field(None, description="医生姓名")
    doctor_title: Optional[str] = Field(None, description="医生职称")
    department_name: Optional[str] = Field(None, description="科室名称")
    schedule_id: Optional[str] = Field(None, description="排班ID")
    schedule_date: Optional[date] = Field(None, description="就诊日期")
    time_slot: Optional[str] = Field(None, description="时段: AM上午/PM下午")
    start_time: Optional[time] = Field(None, description="开始时间")
    end_time: Optional[time] = Field(None, description="结束时间")
    queue_number: Optional[int] = Field(None, description="排队序号")
    status: Optional[int] = Field(None, description="状态: 0待支付 1已预约 2已签到 3候诊中 4就诊中 5已完成 6已取消 7已过期 8已关闭")
    sign_in_time: Optional[datetime] = Field(None, description="签到时间")
    call_time: Optional[datetime] = Field(None, description="叫号时间")
    complete_time: Optional[datetime] = Field(None, description="完成就诊时间")
    cancel_time: Optional[datetime] = Field(None, description="取消时间")
    cancel_reason: Optional[str] = Field(None, description="取消原因")
    symptom_description: Optional[str] = Field(None, description="病情描述")
    created_at: Optional[datetime] = Field(None, description="创建时间")


class AppointmentListQuery(BaseModel):
    """预约列表查询参数"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    status: Optional[int] = Field(None, description="状态: 0待支付 1已预约 2已签到 3候诊中 4就诊中 5已完成 6已取消 7已过期 8已关闭")
    patient_id: Optional[str] = Field(None, description="就诊人ID")
    doctor_id: Optional[str] = Field(None, description="医生ID")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量")


class AppointmentCancelRequest(BaseModel):
    """取消预约请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "reason": "临时有事无法前往"
            }
        }
    )
    
    reason: Optional[str] = Field(None, max_length=200, description="取消原因", examples=["临时有事无法前往", "预约错误", "身体不适已恢复"])


class AppointmentStatistics(BaseModel):
    """预约统计信息"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    total: int = Field(0, description="总预约数")
    pending: int = Field(0, description="待签到数")
    signed_in: int = Field(0, description="已签到数")
    in_progress: int = Field(0, description="就诊中数")
    completed: int = Field(0, description="已完成数")
    cancelled: int = Field(0, description="已取消数")
    no_show: int = Field(0, description="爽约数")

