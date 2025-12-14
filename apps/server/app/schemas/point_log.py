"""积分流水 Schema"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PointLogBase(BaseModel):
    """积分流水基础"""
    change_amount: int = Field(..., description="变更积分（正增负减）")
    type: int = Field(4, ge=1, le=4, description="类型: 1消费 2充值 3赠送 4手动调整")
    remark: Optional[str] = Field(None, max_length=255, description="备注")


class PointAdjustData(BaseModel):
    """积分调整请求"""
    amount: int = Field(..., description="调整积分数量（正增负减）")
    remark: str = Field(..., max_length=255, description="调整原因")


class PointLogResponse(BaseModel):
    """积分流水响应"""
    id: str
    user_id: str
    change_amount: int
    balance: int
    type: int
    remark: Optional[str] = None
    operator_id: Optional[str] = None
    operator_name: Optional[str] = None
    created_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class PointSummary(BaseModel):
    """积分汇总"""
    current_points: int = 0
    total_earned: int = 0
    total_spent: int = 0
