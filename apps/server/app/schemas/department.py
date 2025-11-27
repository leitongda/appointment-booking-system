from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class DepartmentBase(BaseModel):
    name: str = Field(..., max_length=100, description="科室名称")
    parent_id: Optional[str] = Field(None, description="父级科室ID")
    description: Optional[str] = None
    sort_order: int = Field(0, ge=0)
    is_hot: int = Field(0, ge=0, le=1, description="是否热门")
    status: int = Field(1, ge=0, le=1)

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    parent_id: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = Field(None, ge=0)
    is_hot: Optional[int] = Field(None, ge=0, le=1)
    status: Optional[int] = Field(None, ge=0, le=1)

class DepartmentResponse(DepartmentBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class DepartmentTreeNode(BaseModel):
    id: str
    name: str
    parent_id: Optional[str]
    children: List['DepartmentTreeNode'] = []
    
    class Config:
        from_attributes = True

DepartmentTreeNode.model_rebuild()

