"""假期管理 Schema 定义"""

from datetime import date, datetime

from pydantic import Field

from app.schemas.base import BaseSchema


# ==================== 假期类型 ====================

class LeaveTypeCreate(BaseSchema):
    name: str = Field(..., min_length=1, max_length=50, description="假期名称")
    code: str = Field(..., min_length=1, max_length=30, description="假期代码")
    paid: bool = Field(True, description="是否带薪")
    default_days: int = Field(0, ge=0, description="默认年假天数（0表示不限）")
    enabled: bool = Field(True, description="是否启用")
    sort_order: int = Field(0, ge=0, description="排序")


class LeaveTypeUpdate(BaseSchema):
    name: str | None = Field(None, max_length=50)
    code: str | None = Field(None, max_length=30)
    paid: bool | None = None
    default_days: int | None = Field(None, ge=0)
    enabled: bool | None = None
    sort_order: int | None = Field(None, ge=0)


class LeaveTypeResponse(BaseSchema):
    id: str
    tenant_id: str | None = None
    name: str
    code: str
    paid: bool = True
    default_days: int = 0
    enabled: bool = True
    sort_order: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ==================== 假期余额 ====================

class LeaveBalanceResponse(BaseSchema):
    id: str
    account_id: str
    leave_type_id: str
    leave_type_name: str | None = None
    year: int
    total_days: float = 0
    used_days: float = 0
    remaining_days: float = 0


class LeaveBalanceUpdate(BaseSchema):
    account_id: str = Field(..., description="账号ID")
    leave_type_id: str = Field(..., description="假期类型ID")
    year: int = Field(..., description="年度")
    total_days: float = Field(..., ge=0, description="总额度天数")


# ==================== 假期申请 ====================

class LeaveRequestCreate(BaseSchema):
    leave_type_id: str = Field(..., description="假期类型ID")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    reason: str | None = Field(None, description="请假原因")


class LeaveRequestResponse(BaseSchema):
    id: str
    tenant_id: str | None = None
    account_id: str
    leave_type_id: str
    leave_type_name: str | None = None
    start_date: date
    end_date: date
    duration_days: float
    reason: str | None = None
    status: str = "pending"
    reviewer_id: str | None = None
    review_comment: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # 关联字段
    account_name: str | None = None


class LeaveReviewRequest(BaseSchema):
    comment: str | None = Field(None, description="审核意见")
