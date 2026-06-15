from app.schemas.response import to_camel

"""积分流水 Schema"""

from pydantic import BaseModel, ConfigDict, Field


class PointLogBase(BaseModel):
    """积分流水基础"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    change_amount: int = Field(..., description="变更积分（正增负减）")
    type: int = Field(4, ge=1, le=4, description="类型: 1消费 2充值 3赠送 4手动调整")
    remark: str | None = Field(None, max_length=255, description="备注")

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

    id: str = Field(..., description="流水ID")
    user_id: str | None = Field(None, description="用户ID")
    change_amount: int | None = Field(0, description="变更积分数")
    balance: int | None = Field(0, description="变更后余额")
    type: int | None = Field(4, description="类型: 1消费 2充值 3赠送 4手动调整")
    remark: str | None = Field(None, description="备注")
    operator_id: str | None = Field(None, description="操作人ID")
    operator_name: str | None = Field(None, description="操作人姓名")
    created_at: str | None = Field(None, description="创建时间")

class PointSummary(BaseModel):
    """积分汇总"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )

    current_points: int = Field(0, description="当前积分")
    total_earned: int = Field(0, description="累计获得积分")
    total_spent: int = Field(0, description="累计消费积分")
