"""小程序模板相关的 Pydantic Schema"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.schemas.base import BaseSchema

# ==================== AppTemplate (小程序模板) ====================

class AppTemplateBase(BaseModel):
    """模板基础 Schema"""
    name: str = Field(..., max_length=100, description="模板名称")
    code: str = Field(..., max_length=50, description="模板编码，全局唯一")
    description: str | None = Field(None, description="模板描述")
    category: str = Field(..., max_length=50, description="模板分类")
    default_config: dict[str, Any] | None = Field(None, description="默认配置(JSON)")

class AppTemplateCreate(AppTemplateBase):
    """创建模板"""
    pass

class AppTemplateUpdate(BaseModel):
    """更新模板"""
    name: str | None = Field(None, max_length=100)
    description: str | None = None
    default_config: dict[str, Any] | None = None
    status: int | None = Field(None, ge=0, le=1)

class AppTemplateResponse(AppTemplateBase, BaseSchema):
    """模板响应"""
    id: str
    status: int = Field(..., description="状态: 0-禁用 1-启用")
    created_at: datetime
    updated_at: datetime | None = None

class AppTemplateListResponse(BaseSchema):
    """模板列表响应（简化版）"""
    id: str
    code: str
    name: str
    description: str | None = None
    category: str
    status: int
    created_at: datetime

# ==================== TemplateVersion (模板版本) ====================

class TemplateVersionBase(BaseModel):
    """模板版本基础 Schema"""
    version: str = Field(..., max_length=50, description="版本号")
    source_ref: str | None = Field(None, max_length=255, description="模板源码引用")
    schema_version: str | None = Field(None, max_length=50, description="模板配置结构版本")
    changelog: str | None = Field(None, description="版本变更说明")

class TemplateVersionCreate(TemplateVersionBase):
    """创建模板版本"""
    template_id: str = Field(..., description="模板ID")

class TemplateVersionResponse(TemplateVersionBase, BaseSchema):
    """模板版本响应"""
    id: str
    template_id: str
    status: int = Field(..., description="状态: 0-禁用 1-启用")
    created_at: datetime
    updated_at: datetime | None = None

# ==================== BuildJob (构建任务) ====================

class BuildJobCreate(BaseModel):
    """创建构建任务"""
    miniapp_instance_id: str = Field(..., description="小程序实例ID")
    template_version_id: str | None = Field(None, description="模板版本ID")
    trigger_source: str | None = Field(None, max_length=50, description="触发来源")
    build_params: dict[str, Any] | None = Field(None, description="构建参数")

class BuildJobResponse(BaseSchema):
    """构建任务响应"""
    id: str
    tenant_id: str
    miniapp_instance_id: str
    template_version_id: str | None = None
    trigger_source: str | None = None
    build_params: dict[str, Any] | None = None
    status: str = Field(..., description="任务状态")
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    # 关联信息
    miniapp_instance: dict[str, Any] | None = None
    template_version: dict[str, Any] | None = None

class BuildJobListResponse(BaseSchema):
    """构建任务列表响应（简化版）"""
    id: str
    miniapp_instance_id: str
    miniapp_instance_name: str | None = None
    template_version: str | None = None
    trigger_source: str | None = None
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime

# ==================== ReleaseArtifact (发布构建产物) ====================

class ReleaseArtifactResponse(BaseSchema):
    """发布构建产物响应"""
    id: str
    build_job_id: str
    file_path: str
    checksum: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime

# ==================== ReleaseJob (发布任务) ====================

class ReleaseJobCreate(BaseModel):
    """创建发布任务"""
    miniapp_instance_id: str = Field(..., description="小程序实例ID")
    artifact_id: str | None = Field(None, description="制品ID")
    action: str = Field(..., max_length=30, description="动作: upload/submit_audit/publish/rollback")
    target_version: str | None = Field(None, max_length=50, description="目标版本")

    @field_validator('action')
    @classmethod
    def validate_action(cls, v: str) -> str:
        valid_actions = ['upload', 'submit_audit', 'publish', 'rollback']
        if v not in valid_actions:
            raise ValueError(f'动作必须是 {", ".join(valid_actions)} 之一')
        return v

class ReleaseJobResponse(BaseSchema):
    """发布任务响应"""
    id: str
    miniapp_instance_id: str
    artifact_id: str | None = None
    action: str
    target_version: str | None = None
    result: dict[str, Any] | None = None
    status: str = Field(..., description="任务状态")
    created_at: datetime
    updated_at: datetime | None = None

    # 关联信息
    miniapp_instance: dict[str, Any] | None = None
    artifact: ReleaseArtifactResponse | None = None

class ReleaseJobListResponse(BaseSchema):
    """发布任务列表响应（简化版）"""
    id: str
    miniapp_instance_id: str
    miniapp_instance_name: str | None = None
    action: str
    target_version: str | None = None
    status: str
    result: dict[str, Any] | None = None
    created_at: datetime
