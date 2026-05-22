"""审批流 Pydantic schemas"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


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
    approval_mode: Optional[str] = Field(None, pattern="^(and|or|sequential)$")
    assignee_type: Optional[str] = None
    assignee_config: Optional[Dict[str, Any]] = None
    timeout_hours: Optional[int] = None
    timeout_action: Optional[str] = Field(None, pattern="^(remind|auto_approve|auto_reject|transfer)$")
    sort_order: int = 0
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    conditions: List[FlowConditionCreate] = Field(default_factory=list)


class FlowDefinitionCreate(BaseModel):
    model_config = CAMEL_CONFIG

    name: str
    business_type: str
    description: Optional[str] = None
    form_schema: Optional[Dict[str, Any]] = None
    callback_config: Optional[Dict[str, Any]] = None
    store_id: Optional[str] = None
    nodes: List[FlowNodeCreate] = Field(default_factory=list)


class FlowDefinitionUpdate(BaseModel):
    model_config = CAMEL_CONFIG

    name: Optional[str] = None
    description: Optional[str] = None
    form_schema: Optional[Dict[str, Any]] = None
    callback_config: Optional[Dict[str, Any]] = None
    nodes: Optional[List[FlowNodeCreate]] = None


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
    approval_mode: Optional[str] = None
    assignee_type: Optional[str] = None
    assignee_config: Optional[Dict[str, Any]] = None
    timeout_hours: Optional[int] = None
    timeout_action: Optional[str] = None
    sort_order: int
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    conditions: List[FlowConditionResponse] = Field(default_factory=list)


class FlowDefinitionResponse(BaseModel):
    model_config = CAMEL_CONFIG

    id: str
    name: str
    business_type: str
    description: Optional[str] = None
    version: int
    status: str
    form_schema: Optional[Dict[str, Any]] = None
    callback_config: Optional[Dict[str, Any]] = None
    store_id: Optional[str] = None
    snapshot_json: Optional[Dict[str, Any]] = None
    nodes: List[FlowNodeResponse] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class FlowDefinitionListResponse(BaseModel):
    model_config = CAMEL_CONFIG

    id: str
    name: str
    business_type: str
    version: int
    status: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ============================================================
# 审批实例相关
# ============================================================

class ApprovalRecordResponse(BaseModel):
    model_config = CAMEL_CONFIG

    id: str
    node_key: str
    node_name: Optional[str] = None
    approver_id: str
    approver_name: Optional[str] = None
    action: str
    comment: Optional[str] = None
    delegate_to: Optional[str] = None
    created_at: Optional[datetime] = None


class ApprovalTaskResponse(BaseModel):
    model_config = CAMEL_CONFIG

    id: str
    instance_id: str
    node_key: str
    node_name: Optional[str] = None
    task_type: str
    status: str
    assignee_id: str
    assignee_name: Optional[str] = None
    candidate_user_ids: Optional[List[str]] = None
    assignee_snapshot: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None
    completed_by: Optional[str] = None
    timeout_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class ApprovalInstanceResponse(BaseModel):
    model_config = CAMEL_CONFIG

    id: str
    flow_def_id: str
    business_type: str
    business_id: str
    title: str
    form_data: Dict[str, Any]
    status: str
    current_node_key: Optional[str] = None
    applicant_id: str
    applicant_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    completed_reason: Optional[str] = None
    records: List[ApprovalRecordResponse] = Field(default_factory=list)
    tasks: List[ApprovalTaskResponse] = Field(default_factory=list)
    created_at: Optional[datetime] = None


class ApprovalInstanceListResponse(BaseModel):
    model_config = CAMEL_CONFIG

    id: str
    business_type: str
    business_id: str
    title: str
    status: str
    applicant_id: str
    applicant_name: Optional[str] = None
    current_node_key: Optional[str] = None
    created_at: Optional[datetime] = None


class ApprovalActionRequest(BaseModel):
    model_config = CAMEL_CONFIG

    comment: Optional[str] = None


class ApprovalDelegateRequest(BaseModel):
    model_config = CAMEL_CONFIG

    target_user_id: str
    target_user_name: Optional[str] = None
    comment: Optional[str] = None


class ApprovalQuery(BaseModel):
    model_config = CAMEL_CONFIG

    page: int = 1
    page_size: int = 20
    status: Optional[str] = None
    business_type: Optional[str] = None
    applicant_id: Optional[str] = None
    store_id: Optional[str] = None
