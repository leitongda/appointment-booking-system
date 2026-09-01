from app.schemas.base import BaseRequestSchema, BaseSchema

"""检查报告 Schemas"""
from datetime import datetime

from pydantic import Field


class ExaminationReportCreate(BaseRequestSchema):
    """创建检查报告（关联已有文件）"""
    appointment_id: str = Field(..., description="预约ID")
    record_id: str | None = Field(None, description="关联病历ID")
    report_type: str = Field(..., description="报告类型: blood_test/imaging/pathology/other")
    title: str = Field(..., max_length=200, description="报告标题")
    description: str | None = Field(None, description="报告描述/备注")
    file_name: str = Field(..., max_length=255, description="原始文件名")
    file_key: str = Field(..., max_length=500, description="存储key")
    file_size: int = Field(..., description="文件大小(bytes)")
    file_type: str = Field(..., max_length=50, description="MIME类型")
    file_url: str | None = Field(None, max_length=1000, description="文件访问URL")

class ExaminationReportResponse(BaseSchema):
    """检查报告响应"""
    id: str
    tenant_id: str | None = None
    store_id: str | None = None
    record_id: str | None = None
    appointment_id: str
    patient_id: str
    doctor_id: str
    patient_name: str | None = None
    doctor_name: str | None = None
    report_type: str
    title: str
    description: str | None = None
    file_name: str
    file_key: str
    file_size: int
    file_type: str
    file_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class ExaminationReportListResponse(BaseSchema):
    """检查报告列表响应（简化版）"""
    id: str
    report_type: str
    title: str
    file_name: str
    file_size: int
    file_type: str
    file_url: str | None = None
    created_at: datetime | None = None
