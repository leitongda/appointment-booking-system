"""积分流水 Schema"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class PointLogBase(BaseModel):
    """积分流水基础"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    change_amount: int = Field(..., description="变更积分（正增负减）")
    type: int = Field(4, ge=1, le=4, description="类型: 1消费 2充值 3赠送 4手动调整")
    remark: Optional[str] = Field(None, max_length=255, description="备注")


class PointAdjustData(BaseModel):
    """积分调整请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    amount: int = Field(..., description="调整积分数量（正增负减）")
    remark: str = Field(..., max_length=255, description="调整原因")


class PointLogResponse(BaseModel):
    """积分流水响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    user_id: Optional[str] = None
    change_amount: Optional[int] = 0
    balance: Optional[int] = 0
    type: Optional[int] = 4
    remark: Optional[str] = None
    operator_id: Optional[str] = None
    operator_name: Optional[str] = None
    created_at: Optional[str] = None


class PointSummary(BaseModel):
    """积分汇总"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    current_points: int = 0
    total_earned: int = 0
    total_spent: int = 0
