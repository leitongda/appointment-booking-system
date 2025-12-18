from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class EmailTemplateType(str, Enum):
    APPOINTMENT_CONFIRM = "appointment_confirm"
    APPOINTMENT_REMIND = "appointment_remind"
    APPOINTMENT_CANCEL = "appointment_cancel"
    STOP_CLINIC = "stop_clinic"
    CUSTOM = "custom"


class EmailTemplateBase(BaseModel):
    """邮件模板基础模型"""
    code: str = Field(..., max_length=50, description="模板编码")
    name: str = Field(..., max_length=100, description="模板名称")
    template_type: EmailTemplateType = Field(EmailTemplateType.CUSTOM, description="模板类型")
    subject_template: str = Field(..., max_length=200, description="邮件主题模板")
    content_template: str = Field(..., description="邮件内容模板(HTML)")
    description: Optional[str] = Field(None, max_length=255, description="模板说明")
    status: int = Field(1, ge=0, le=1, description="状态: 0-禁用 1-启用")


class EmailTemplateCreate(EmailTemplateBase):
    """创建邮件模板"""
    pass


class EmailTemplateUpdate(BaseModel):
    """更新邮件模板"""
    name: Optional[str] = Field(None, max_length=100)
    template_type: Optional[EmailTemplateType] = None
    subject_template: Optional[str] = Field(None, max_length=200)
    content_template: Optional[str] = None
    description: Optional[str] = Field(None, max_length=255)
    status: Optional[int] = Field(None, ge=0, le=1)


class EmailTemplateResponse(BaseModel):
    """邮件模板响应"""
    id: str
    code: str
    name: str
    templateType: str = Field(alias='template_type')
    subjectTemplate: str = Field(alias='subject_template')
    contentTemplate: str = Field(alias='content_template')
    description: Optional[str] = None
    status: int
    createdAt: datetime = Field(alias='created_at')
    updatedAt: datetime = Field(alias='updated_at')
    
    class Config:
        from_attributes = True
        populate_by_name = True


class EmailTemplateListResponse(BaseModel):
    """邮件模板列表响应"""
    id: str
    code: str
    name: str
    templateType: str = Field(alias='template_type')
    subjectTemplate: str = Field(alias='subject_template')
    description: Optional[str] = None
    status: int
    createdAt: datetime = Field(alias='created_at')
    updatedAt: datetime = Field(alias='updated_at')
    
    class Config:
        from_attributes = True
        populate_by_name = True


class EmailTemplateQuery(BaseModel):
    """邮件模板查询参数"""
    template_type: Optional[EmailTemplateType] = Field(None, description="模板类型")
    status: Optional[int] = Field(None, description="状态")
    keyword: Optional[str] = Field(None, description="关键词搜索")
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)


class EmailTestRequest(BaseModel):
    """发送测试邮件请求"""
    to_email: str = Field(..., description="收件人邮箱")
    variables: Optional[dict] = Field(None, description="模板变量")


class EmailSendRequest(BaseModel):
    """发送邮件请求"""
    template_code: str = Field(..., description="模板编码")
    to_email: str = Field(..., description="收件人邮箱")
    variables: dict = Field(default_factory=dict, description="模板变量")

