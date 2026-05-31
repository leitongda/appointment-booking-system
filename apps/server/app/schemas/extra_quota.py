from app.schemas.response import to_camel
"""加号申请与审批 Schema。"""
from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums.general import ApprovalStatus, ExtraQuotaType  # noqa: F401 — re-export

# ==================== 请求 Schema ====================

class ExtraQuotaRequestCreate(BaseModel):
    """加号申请创建请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    schedule_id: str = Field(..., description="排班ID")
    quantity: int = Field(..., ge=1, le=50, description="加号数量")
    quota_type: str = Field("normal", description="加号类型（字典: extra_quota_type）: normal普通/special特殊/green_channel绿色通道")
    open_to_public: bool = Field(True, description="是否对外开放（true = 患者端可见可约）")
    patient_id: Optional[str] = Field(None, description="指定患者ID（仅对指定患者可见）")
    reason: Optional[str] = Field(None, max_length=500, description="加号原因")

class ExtraQuotaApprovalRequest(BaseModel):
    """加号审批请求（用于审批通过/拒绝操作）"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    remark: Optional[str] = Field(None, max_length=500, description="审批备注")

# ==================== 响应 Schema ====================

class ExtraQuotaRequestResponse(BaseModel):
    """加号申请响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )

    id: str = Field(..., description="申请ID")
    tenant_id: str = Field(..., description="租户ID")
    store_id: str = Field(..., description="门店ID")
    schedule_id: str = Field(..., description="排班ID")
    doctor_id: str = Field(..., description="医生ID")
    schedule_date: str = Field(..., description="排班日期")
    time_slot: str = Field(..., description="时间段")
    quantity: int = Field(..., description="加号数量")
    quota_type: str = Field(..., description="加号类型")
    open_to_public: bool = Field(True, description="是否对外开放")
    patient_id: Optional[str] = Field(None, description="指定患者ID")
    reason: Optional[str] = Field(None, description="加号原因")
    approval_status: str = Field("pending", description="审批状态")
    applicant_id: str = Field(..., description="申请人ID")
    approver_id: Optional[str] = Field(None, description="审批人ID")
    approval_remark: Optional[str] = Field(None, description="审批备注")
    approved_at: Optional[datetime] = Field(None, description="审批时间")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

class ExtraQuotaListResponse(BaseModel):
    """加号申请列表响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )

    data: List[ExtraQuotaRequestResponse] = Field(default_factory=list, description="申请列表")
    total: int = Field(0, description="总数")
    page: int = Field(1, description="当前页")
    page_size: int = Field(10, alias="pageSize", description="每页数量")

# ==================== 兼容旧接口 ====================

# 保持向后兼容的别名
ExtraQuotaRequest = ExtraQuotaRequestCreate
ExtraQuotaApproval = ExtraQuotaApprovalRequest
