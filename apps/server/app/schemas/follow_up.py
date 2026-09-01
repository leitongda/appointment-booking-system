"""随访模块 Schema"""
from datetime import date, datetime

from pydantic import Field

from app.enums.general import PatientCondition, SelfReportStatus, TaskStatus  # noqa: F401 — re-export
from app.schemas.base import BaseRequestSchema, BaseSchema

# ========== 计划步骤 ==========

class FollowUpPlanStepCreate(BaseRequestSchema):

    step_order: int = Field(..., ge=1, description="步骤顺序")
    name: str = Field(..., max_length=100, description="步骤名称")
    days_after_visit: int = Field(..., ge=1, description="就诊后第几天")
    description: str | None = Field(None, description="步骤说明")

class FollowUpPlanStepResponse(BaseSchema):

    id: str
    plan_id: str
    step_order: int
    name: str
    days_after_visit: int
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

# ========== 计划 ==========

class FollowUpPlanCreate(BaseRequestSchema):

    name: str = Field(..., max_length=200, description="计划名称")
    description: str | None = Field(None, description="计划描述")
    department_id: str | None = Field(None, description="科室ID，不传=全局")
    diagnosis_code: str | None = Field(None, description="诊断编码")
    diagnosis_name: str | None = Field(None, description="诊断名称")
    steps: list[FollowUpPlanStepCreate] = Field(..., min_length=1, description="随访步骤")

class FollowUpPlanUpdate(BaseRequestSchema):

    name: str | None = Field(None, max_length=200, description="计划名称")
    description: str | None = Field(None, description="计划描述")
    department_id: str | None = Field(None, description="科室ID")
    diagnosis_code: str | None = Field(None, description="诊断编码")
    diagnosis_name: str | None = Field(None, description="诊断名称")
    status: int | None = Field(None, ge=0, le=1, description="状态 0=停用 1=启用")

class FollowUpPlanStepsUpdate(BaseRequestSchema):

    steps: list[FollowUpPlanStepCreate] = Field(..., min_length=1, description="随访步骤（全量替换）")

class FollowUpPlanResponse(BaseSchema):

    id: str
    name: str
    description: str | None = None
    department_id: str | None = None
    department_name: str | None = None
    diagnosis_code: str | None = None
    diagnosis_name: str | None = None
    status: int | None = None
    steps: list[FollowUpPlanStepResponse] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None

class FollowUpPlanListResponse(BaseSchema):

    id: str
    name: str
    department_name: str | None = None
    diagnosis_name: str | None = None
    status: int | None = None
    step_count: int | None = None
    created_at: datetime | None = None

# ========== 任务 ==========

class FollowUpTaskCreate(BaseRequestSchema):

    patient_id: str = Field(..., description="患者ID")
    doctor_id: str = Field(..., description="医生ID")
    department_id: str = Field(..., description="科室ID")
    appointment_id: str | None = Field(None, description="预约ID")
    medical_record_id: str | None = Field(None, description="病历ID")
    scheduled_date: date = Field(..., description="计划随访日期")
    description: str | None = Field(None, description="备注")

class FollowUpTaskGenerateRequest(BaseRequestSchema):

    patient_id: str = Field(..., description="患者ID")
    doctor_id: str = Field(..., description="医生ID")
    department_id: str = Field(..., description="科室ID")
    plan_id: str = Field(..., description="随访计划ID")
    appointment_id: str | None = Field(None, description="预约ID")
    medical_record_id: str | None = Field(None, description="病历ID")
    base_date: date | None = Field(None, description="基准日期，不传=今天")

class FollowUpTaskSkipRequest(BaseRequestSchema):

    reason: str = Field(..., max_length=500, description="跳过原因")

class FollowUpTaskResponse(BaseSchema):

    id: str
    task_no: str | None = None
    patient_id: str
    patient_name: str | None = None
    doctor_id: str
    doctor_name: str | None = None
    department_id: str
    department_name: str | None = None
    appointment_id: str | None = None
    medical_record_id: str | None = None
    plan_id: str | None = None
    plan_name: str | None = None
    step_order: int | None = None
    scheduled_date: date | None = None
    status: str | None = None
    completed_at: datetime | None = None
    completed_by: str | None = None
    skip_reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class FollowUpTaskListResponse(BaseSchema):

    id: str
    task_no: str | None = None
    patient_name: str | None = None
    doctor_name: str | None = None
    department_name: str | None = None
    scheduled_date: date | None = None
    status: str | None = None
    plan_name: str | None = None
    step_order: int | None = None
    created_at: datetime | None = None

# ========== 记录 ==========

class FollowUpRecordCreate(BaseRequestSchema):

    task_id: str | None = Field(None, description="关联任务ID，不传=独立记录")
    patient_id: str = Field(..., description="患者ID")
    doctor_id: str = Field(..., description="医生ID")
    appointment_id: str | None = Field(None, description="预约ID")
    medical_record_id: str | None = Field(None, description="病历ID")
    follow_up_date: datetime = Field(default_factory=datetime.now, description="随访时间")
    content: str = Field(..., description="随访内容")
    patient_condition: PatientCondition | None = Field(None, description="患者状况")
    next_action: str | None = Field(None, description="下一步措施")
    next_follow_up_date: date | None = Field(None, description="下次随访日期")
    attachments: list[str] | None = Field(None, description="附件URL列表")

class FollowUpRecordUpdate(BaseRequestSchema):

    content: str | None = Field(None, description="随访内容")
    patient_condition: PatientCondition | None = Field(None, description="患者状况")
    next_action: str | None = Field(None, description="下一步措施")
    next_follow_up_date: date | None = Field(None, description="下次随访日期")
    attachments: list[str] | None = Field(None, description="附件URL列表")

class FollowUpRecordResponse(BaseSchema):

    id: str
    task_id: str | None = None
    patient_id: str
    patient_name: str | None = None
    doctor_id: str
    doctor_name: str | None = None
    appointment_id: str | None = None
    medical_record_id: str | None = None
    follow_up_date: datetime | None = None
    content: str | None = None
    patient_condition: str | None = None
    next_action: str | None = None
    next_follow_up_date: date | None = None
    attachments: list | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class FollowUpRecordListResponse(BaseSchema):

    id: str
    patient_name: str | None = None
    doctor_name: str | None = None
    follow_up_date: datetime | None = None
    content: str | None = None
    patient_condition: str | None = None
    task_id: str | None = None
    created_at: datetime | None = None

# ========== 患者自报告 ==========

class SelfReportCreate(BaseRequestSchema):

    task_id: str | None = Field(None, description="关联随访任务ID")
    report_date: datetime | None = Field(None, description="测量时间，不传=当前时间")
    systolic_bp: int | None = Field(None, ge=60, le=300, description="收缩压 (mmHg)")
    diastolic_bp: int | None = Field(None, ge=30, le=200, description="舒张压 (mmHg)")
    blood_glucose: float | None = Field(None, ge=1.0, le=50.0, description="血糖 (mmol/L)")
    heart_rate: int | None = Field(None, ge=30, le=300, description="心率 (次/分)")
    temperature: float | None = Field(None, ge=30.0, le=45.0, description="体温 (°C)")
    symptoms: str | None = Field(None, description="症状描述")
    patient_condition: PatientCondition | None = Field(None, description="自我感受")
    notes: str | None = Field(None, description="备注")
    attachments: list[str] | None = Field(None, description="附件URL列表")

class SelfReportResponse(BaseSchema):

    id: str
    task_id: str | None = None
    patient_id: str
    patient_name: str | None = None
    report_date: datetime | None = None
    systolic_bp: int | None = None
    diastolic_bp: int | None = None
    blood_glucose: float | None = None
    heart_rate: int | None = None
    temperature: float | None = None
    symptoms: str | None = None
    patient_condition: str | None = None
    notes: str | None = None
    attachments: list | None = None
    status: str | None = None
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None
    created_at: datetime | None = None

class SelfReportListResponse(BaseSchema):

    id: str
    task_id: str | None = None
    patient_name: str | None = None
    report_date: datetime | None = None
    systolic_bp: int | None = None
    diastolic_bp: int | None = None
    blood_glucose: float | None = None
    symptoms: str | None = None
    patient_condition: str | None = None
    status: str | None = None
    created_at: datetime | None = None
