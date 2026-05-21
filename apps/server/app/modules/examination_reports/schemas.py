"""检查报告 Schemas"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


def to_camel(string: str) -> str:
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class ExaminationReportCreate(BaseModel):
    """创建检查报告（关联已有文件）"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    appointment_id: str = Field(..., description="预约ID")
    record_id: Optional[str] = Field(None, description="关联病历ID")
    report_type: str = Field(..., description="报告类型: blood_test/imaging/pathology/other")
    title: str = Field(..., max_length=200, description="报告标题")
    description: Optional[str] = Field(None, description="报告描述/备注")
    file_name: str = Field(..., max_length=255, description="原始文件名")
    file_key: str = Field(..., max_length=500, description="存储key")
    file_size: int = Field(..., description="文件大小(bytes)")
    file_type: str = Field(..., max_length=50, description="MIME类型")
    file_url: Optional[str] = Field(None, max_length=1000, description="文件访问URL")


class ExaminationReportResponse(BaseModel):
    """检查报告响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )

    id: str
    tenant_id: Optional[str] = None
    store_id: Optional[str] = None
    record_id: Optional[str] = None
    appointment_id: str
    patient_id: str
    doctor_id: str
    report_type: str
    title: str
    description: Optional[str] = None
    file_name: str
    file_key: str
    file_size: int
    file_type: str
    file_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ExaminationReportListResponse(BaseModel):
    """检查报告列表响应（简化版）"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )

    id: str
    report_type: str
    title: str
    file_name: str
    file_size: int
    file_type: str
    file_url: Optional[str] = None
    created_at: Optional[datetime] = None
