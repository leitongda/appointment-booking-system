from app.schemas.response import to_camel
"""随访模块 Schema"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime, date

from app.enums.general import PatientCondition, SelfReportStatus, TaskStatus  # noqa: F401 — re-export

# ========== 计划步骤 ==========

class FollowUpPlanStepCreate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    step_order: int = Field(..., ge=1, description="步骤顺序")
    name: str = Field(..., max_length=100, description="步骤名称")
    days_after_visit: int = Field(..., ge=1, description="就诊后第几天")
    description: Optional[str] = Field(None, description="步骤说明")

class FollowUpPlanStepResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True, by_alias=True)

    id: str
    plan_id: str
    step_order: int
    name: str
    days_after_visit: int
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# ========== 计划 ==========

class FollowUpPlanCreate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str = Field(..., max_length=200, description="计划名称")
    description: Optional[str] = Field(None, description="计划描述")
    department_id: Optional[str] = Field(None, description="科室ID，不传=全局")
    diagnosis_code: Optional[str] = Field(None, description="诊断编码")
    diagnosis_name: Optional[str] = Field(None, description="诊断名称")
    steps: List[FollowUpPlanStepCreate] = Field(..., min_length=1, description="随访步骤")

class FollowUpPlanUpdate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: Optional[str] = Field(None, max_length=200, description="计划名称")
    description: Optional[str] = Field(None, description="计划描述")
    department_id: Optional[str] = Field(None, description="科室ID")
    diagnosis_code: Optional[str] = Field(None, description="诊断编码")
    diagnosis_name: Optional[str] = Field(None, description="诊断名称")
    status: Optional[int] = Field(None, ge=0, le=1, description="状态 0=停用 1=启用")

class FollowUpPlanStepsUpdate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    steps: List[FollowUpPlanStepCreate] = Field(..., min_length=1, description="随访步骤（全量替换）")

class FollowUpPlanResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True, by_alias=True)

    id: str
    name: str
    description: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    diagnosis_code: Optional[str] = None
    diagnosis_name: Optional[str] = None
    status: Optional[int] = None
    steps: List[FollowUpPlanStepResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class FollowUpPlanListResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True, by_alias=True)

    id: str
    name: str
    department_name: Optional[str] = None
    diagnosis_name: Optional[str] = None
    status: Optional[int] = None
    step_count: Optional[int] = None
    created_at: Optional[datetime] = None

# ========== 任务 ==========

class FollowUpTaskCreate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    patient_id: str = Field(..., description="患者ID")
    doctor_id: str = Field(..., description="医生ID")
    department_id: str = Field(..., description="科室ID")
    appointment_id: Optional[str] = Field(None, description="预约ID")
    medical_record_id: Optional[str] = Field(None, description="病历ID")
    scheduled_date: date = Field(..., description="计划随访日期")
    description: Optional[str] = Field(None, description="备注")

class FollowUpTaskGenerateRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    patient_id: str = Field(..., description="患者ID")
    doctor_id: str = Field(..., description="医生ID")
    department_id: str = Field(..., description="科室ID")
    plan_id: str = Field(..., description="随访计划ID")
    appointment_id: Optional[str] = Field(None, description="预约ID")
    medical_record_id: Optional[str] = Field(None, description="病历ID")
    base_date: Optional[date] = Field(None, description="基准日期，不传=今天")

class FollowUpTaskSkipRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    reason: str = Field(..., max_length=500, description="跳过原因")

class FollowUpTaskResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True, by_alias=True)

    id: str
    task_no: Optional[str] = None
    patient_id: str
    patient_name: Optional[str] = None
    doctor_id: str
    doctor_name: Optional[str] = None
    department_id: str
    department_name: Optional[str] = None
    appointment_id: Optional[str] = None
    medical_record_id: Optional[str] = None
    plan_id: Optional[str] = None
    plan_name: Optional[str] = None
    step_order: Optional[int] = None
    scheduled_date: Optional[date] = None
    status: Optional[str] = None
    completed_at: Optional[datetime] = None
    completed_by: Optional[str] = None
    skip_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class FollowUpTaskListResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True, by_alias=True)

    id: str
    task_no: Optional[str] = None
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None
    department_name: Optional[str] = None
    scheduled_date: Optional[date] = None
    status: Optional[str] = None
    plan_name: Optional[str] = None
    step_order: Optional[int] = None
    created_at: Optional[datetime] = None

# ========== 记录 ==========

class FollowUpRecordCreate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    task_id: Optional[str] = Field(None, description="关联任务ID，不传=独立记录")
    patient_id: str = Field(..., description="患者ID")
    doctor_id: str = Field(..., description="医生ID")
    appointment_id: Optional[str] = Field(None, description="预约ID")
    medical_record_id: Optional[str] = Field(None, description="病历ID")
    follow_up_date: datetime = Field(default_factory=datetime.now, description="随访时间")
    content: str = Field(..., description="随访内容")
    patient_condition: Optional[PatientCondition] = Field(None, description="患者状况")
    next_action: Optional[str] = Field(None, description="下一步措施")
    next_follow_up_date: Optional[date] = Field(None, description="下次随访日期")
    attachments: Optional[List[str]] = Field(None, description="附件URL列表")

class FollowUpRecordUpdate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    content: Optional[str] = Field(None, description="随访内容")
    patient_condition: Optional[PatientCondition] = Field(None, description="患者状况")
    next_action: Optional[str] = Field(None, description="下一步措施")
    next_follow_up_date: Optional[date] = Field(None, description="下次随访日期")
    attachments: Optional[List[str]] = Field(None, description="附件URL列表")

class FollowUpRecordResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True, by_alias=True)

    id: str
    task_id: Optional[str] = None
    patient_id: str
    patient_name: Optional[str] = None
    doctor_id: str
    doctor_name: Optional[str] = None
    appointment_id: Optional[str] = None
    medical_record_id: Optional[str] = None
    follow_up_date: Optional[datetime] = None
    content: Optional[str] = None
    patient_condition: Optional[str] = None
    next_action: Optional[str] = None
    next_follow_up_date: Optional[date] = None
    attachments: Optional[list] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class FollowUpRecordListResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True, by_alias=True)

    id: str
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None
    follow_up_date: Optional[datetime] = None
    content: Optional[str] = None
    patient_condition: Optional[str] = None
    task_id: Optional[str] = None
    created_at: Optional[datetime] = None

# ========== 患者自报告 ==========

class SelfReportCreate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    task_id: Optional[str] = Field(None, description="关联随访任务ID")
    report_date: Optional[datetime] = Field(None, description="测量时间，不传=当前时间")
    systolic_bp: Optional[int] = Field(None, ge=60, le=300, description="收缩压 (mmHg)")
    diastolic_bp: Optional[int] = Field(None, ge=30, le=200, description="舒张压 (mmHg)")
    blood_glucose: Optional[float] = Field(None, ge=1.0, le=50.0, description="血糖 (mmol/L)")
    heart_rate: Optional[int] = Field(None, ge=30, le=300, description="心率 (次/分)")
    temperature: Optional[float] = Field(None, ge=30.0, le=45.0, description="体温 (°C)")
    symptoms: Optional[str] = Field(None, description="症状描述")
    patient_condition: Optional[PatientCondition] = Field(None, description="自我感受")
    notes: Optional[str] = Field(None, description="备注")
    attachments: Optional[List[str]] = Field(None, description="附件URL列表")

class SelfReportResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True, by_alias=True)

    id: str
    task_id: Optional[str] = None
    patient_id: str
    patient_name: Optional[str] = None
    report_date: Optional[datetime] = None
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    blood_glucose: Optional[float] = None
    heart_rate: Optional[int] = None
    temperature: Optional[float] = None
    symptoms: Optional[str] = None
    patient_condition: Optional[str] = None
    notes: Optional[str] = None
    attachments: Optional[list] = None
    status: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    created_at: Optional[datetime] = None

class SelfReportListResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True, by_alias=True)

    id: str
    task_id: Optional[str] = None
    patient_name: Optional[str] = None
    report_date: Optional[datetime] = None
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    blood_glucose: Optional[float] = None
    symptoms: Optional[str] = None
    patient_condition: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
