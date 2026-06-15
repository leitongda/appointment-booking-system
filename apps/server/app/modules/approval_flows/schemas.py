from app.schemas.response import to_camel

"""审批流 Pydantic schemas"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

CAMEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

# ============================================================
# 流程定义相关
# ============================================================

class FlowConditionCreate(BaseModel):
    model_config = CAMEL_CONFIG

    target_node_key: str
    field_name: str
    operator: str = Field(pattern="^(eq|neq|gt|gte|lt|lte|in|not_in|contains|exists)$")
    value: str
    priority: int = 0

class FlowNodeCreate(BaseModel):
    model_config = CAMEL_CONFIG

    node_key: str
    node_name: str
    node_type: str = Field(pattern="^(start|approval|cc|condition|end)$")
    approval_mode: str | None = Field(None, pattern="^(and|or|sequential)$")
    assignee_type: str | None = None
    assignee_config: dict[str, Any] | None = None
    timeout_hours: int | None = None
    timeout_action: str | None = Field(None, pattern="^(remind|auto_approve|auto_reject|transfer)$")
    sort_order: int = 0
    position_x: float | None = None
    position_y: float | None = None
    conditions: list[FlowConditionCreate] = Field(default_factory=list)

class FlowDefinitionCreate(BaseModel):
    model_config = CAMEL_CONFIG

    name: str
    business_type: str
    description: str | None = None
    form_schema: dict[str, Any] | None = None
    callback_config: dict[str, Any] | None = None
    store_id: str | None = None
    nodes: list[FlowNodeCreate] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)

class FlowDefinitionUpdate(BaseModel):
    model_config = CAMEL_CONFIG

    name: str | None = None
    description: str | None = None
    form_schema: dict[str, Any] | None = None
    callback_config: dict[str, Any] | None = None
    nodes: list[FlowNodeCreate] | None = None
    edges: list[dict[str, Any]] | None = None

class FlowConditionResponse(BaseModel):
    model_config = CAMEL_CONFIG

    id: str
    node_id: str
    target_node_key: str
    field_name: str
    operator: str
    value: str
    priority: int

class FlowNodeResponse(BaseModel):
    model_config = CAMEL_CONFIG

    id: str
    node_key: str
    node_name: str
    node_type: str
    approval_mode: str | None = None
    assignee_type: str | None = None
    assignee_config: dict[str, Any] | None = None
    timeout_hours: int | None = None
    timeout_action: str | None = None
    sort_order: int
    position_x: float | None = None
    position_y: float | None = None
    conditions: list[FlowConditionResponse] = Field(default_factory=list)

class FlowDefinitionResponse(BaseModel):
    model_config = CAMEL_CONFIG

    id: str
    name: str
    business_type: str
    description: str | None = None
    version: int
    status: str
    form_schema: dict[str, Any] | None = None
    callback_config: dict[str, Any] | None = None
    store_id: str | None = None
    snapshot_json: dict[str, Any] | None = None
    edges: list[dict[str, Any]] | None = None
    nodes: list[FlowNodeResponse] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

class FlowDefinitionListResponse(BaseModel):
    model_config = CAMEL_CONFIG

    id: str
    name: str
    business_type: str
    version: int
    status: str
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

# ============================================================
# 审批实例相关
# ============================================================

class ApprovalRecordResponse(BaseModel):
    model_config = CAMEL_CONFIG

    id: str
    node_key: str
    node_name: str | None = None
    approver_id: str
    approver_name: str | None = None
    action: str
    comment: str | None = None
    delegate_to: str | None = None
    created_at: datetime | None = None

class ApprovalTaskResponse(BaseModel):
    model_config = CAMEL_CONFIG

    id: str
    instance_id: str
    node_key: str
    node_name: str | None = None
    task_type: str
    status: str
    assignee_id: str
    assignee_name: str | None = None
    candidate_user_ids: list[str] | None = None
    assignee_snapshot: dict[str, Any] | None = None
    completed_at: datetime | None = None
    completed_by: str | None = None
    timeout_at: datetime | None = None
    created_at: datetime | None = None

class ApprovalInstanceResponse(BaseModel):
    model_config = CAMEL_CONFIG

    id: str
    flow_def_id: str
    business_type: str
    business_id: str
    title: str
    form_data: dict[str, Any]
    status: str
    current_node_key: str | None = None
    applicant_id: str
    applicant_name: str | None = None
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    cancelled_at: datetime | None = None
    completed_reason: str | None = None
    records: list[ApprovalRecordResponse] = Field(default_factory=list)
    tasks: list[ApprovalTaskResponse] = Field(default_factory=list)
    created_at: datetime | None = None

class ApprovalInstanceListResponse(BaseModel):
    model_config = CAMEL_CONFIG

    id: str
    business_type: str
    business_id: str
    title: str
    status: str
    applicant_id: str
    applicant_name: str | None = None
    current_node_key: str | None = None
    created_at: datetime | None = None

class ApprovalActionRequest(BaseModel):
    model_config = CAMEL_CONFIG

    comment: str | None = None

class ApprovalDelegateRequest(BaseModel):
    model_config = CAMEL_CONFIG

    target_user_id: str
    target_user_name: str | None = None
    comment: str | None = None

class ApprovalRollbackRequest(BaseModel):
    """回退请求"""
    model_config = CAMEL_CONFIG
    target_node_key: str = Field(description="回退到的目标节点 key")
    comment: str | None = None

class ApprovalAddSignerRequest(BaseModel):
    """加签请求"""
    model_config = CAMEL_CONFIG
    user_ids: list[str] = Field(description="要加签的用户 ID 列表")
    comment: str | None = None

class ApprovalJumpRequest(BaseModel):
    """自由跳转请求"""
    model_config = CAMEL_CONFIG
    target_node_key: str = Field(description="跳转到的目标节点 key")
    comment: str | None = None

class ApprovalQuery(BaseModel):
    model_config = CAMEL_CONFIG

    page: int = 1
    page_size: int = 20
    status: str | None = None
    business_type: str | None = None
    applicant_id: str | None = None
    store_id: str | None = None
