from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.enums.general import EmailTemplateType  # noqa: F401 — re-export
from app.schemas.response import to_camel


class EmailTemplateBase(BaseModel):
    """邮件模板基础模型"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    code: str = Field(..., max_length=50, description="模板编码")
    name: str = Field(..., max_length=100, description="模板名称")
    template_type: str = Field("custom", description="模板类型（字典: email_template_type）")
    subject_template: str = Field(..., max_length=200, description="邮件主题模板")
    content_template: str = Field(..., description="邮件内容模板(HTML)")
    description: str | None = Field(None, max_length=255, description="模板说明")
    status: int = Field(1, ge=0, le=1, description="状态: 0-禁用 1-启用")

class EmailTemplateCreate(EmailTemplateBase):
    """创建邮件模板"""
    pass

class EmailTemplateUpdate(BaseModel):
    """更新邮件模板"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    name: str | None = Field(None, max_length=100)
    template_type: str | None = None
    subject_template: str | None = Field(None, max_length=200)
    content_template: str | None = None
    description: str | None = Field(None, max_length=255)
    status: int | None = Field(None, ge=0, le=1)

class EmailTemplateResponse(BaseModel):
    """邮件模板响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    code: str | None = None
    name: str | None = None
    template_type: str | None = None
    subject_template: str | None = None
    content_template: str | None = None
    description: str | None = None
    status: int | None = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None

class EmailTemplateListResponse(BaseModel):
    """邮件模板列表响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    code: str | None = None
    name: str | None = None
    template_type: str | None = None
    subject_template: str | None = None
    description: str | None = None
    status: int | None = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None

class EmailTemplateQuery(BaseModel):
    """邮件模板查询参数"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    template_type: str | None = Field(None, description="模板类型（字典: email_template_type）")
    status: int | None = Field(None, description="状态")
    keyword: str | None = Field(None, description="关键词搜索")
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=settings.MAX_PAGE_SIZE)

class EmailTestRequest(BaseModel):
    """发送测试邮件请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    to_email: str = Field(..., description="收件人邮箱")
    variables: dict | None = Field(None, description="模板变量")

class EmailSendRequest(BaseModel):
    """发送邮件请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    template_code: str = Field(..., description="模板编码")
    to_email: str = Field(..., description="收件人邮箱")
    variables: dict = Field(default_factory=dict, description="模板变量")
