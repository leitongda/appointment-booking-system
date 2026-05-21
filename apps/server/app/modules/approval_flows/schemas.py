"""审批流 Pydantic schemas"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================
# 流程定义相关
# ============================================================

class FlowConditionCreate(BaseModel):
    target_node_key: str
    field_name: str
    operator: str = Field(pattern="^(eq|neq|gt|gte|lt|lte|in|not_in|contains|exists)$")
    value: str
    priority: int = 0


class FlowNodeCreate(BaseModel):
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
    conditions: List[FlowConditionCreate] = []


class FlowDefinitionCreate(BaseModel):
    name: str
    business_type: str
    description: Optional[str] = None
    form_schema: Optional[Dict[str, Any]] = None
    callback_config: Optional[Dict[str, Any]] = None
    store_id: Optional[str] = None
    nodes: List[FlowNodeCreate] = []


class FlowDefinitionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    form_schema: Optional[Dict[str, Any]] = None
    callback_config: Optional[Dict[str, Any]] = None
    nodes: Optional[List[FlowNodeCreate]] = None


class FlowConditionResponse(BaseModel):
    id: str
    node_id: str
    target_node_key: str
    field_name: str
    operator: str
    value: str
    priority: int

    class Config:
        from_attributes = True


class FlowNodeResponse(BaseModel):
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
    conditions: List[FlowConditionResponse] = []

    class Config:
        from_attributes = True


class FlowDefinitionResponse(BaseModel):
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
    nodes: List[FlowNodeResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FlowDefinitionListResponse(BaseModel):
    id: str
    name: str
    business_type: str
    version: int
    status: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================
# 审批实例相关
# ============================================================

class ApprovalRecordResponse(BaseModel):
    id: str
    node_key: str
    node_name: Optional[str] = None
    approver_id: str
    approver_name: Optional[str] = None
    action: str
    comment: Optional[str] = None
    delegate_to: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApprovalInstanceResponse(BaseModel):
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
    records: List[ApprovalRecordResponse] = []
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApprovalInstanceListResponse(BaseModel):
    id: str
    business_type: str
    business_id: str
    title: str
    status: str
    applicant_id: str
    applicant_name: Optional[str] = None
    current_node_key: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApprovalActionRequest(BaseModel):
    comment: Optional[str] = None


class ApprovalDelegateRequest(BaseModel):
    target_user_id: str
    target_user_name: Optional[str] = None
    comment: Optional[str] = None


class ApprovalQuery(BaseModel):
    page: int = 1
    page_size: int = 20
    status: Optional[str] = None
    business_type: Optional[str] = None
    applicant_id: Optional[str] = None
    store_id: Optional[str] = None
