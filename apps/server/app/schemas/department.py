from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class DepartmentBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # 允许使用原始字段名或别名
    )
    
    name: str = Field(..., max_length=100, description="科室名称")
    parent_id: Optional[str] = Field(None, description="父级科室ID")
    description: Optional[str] = None
    sort_order: int = Field(0, ge=0)
    is_hot: int = Field(0, ge=0, le=1, description="是否热门")
    status: int = Field(1, ge=0, le=1)
    
    # 基础配置
    store_id: Optional[str] = Field(None, description="默认门店ID")
    tag: Optional[str] = Field(None, max_length=100, description="科室标签")
    enable_banner: int = Field(0, ge=0, le=1, description="是否开放banner")
    enable_intro: int = Field(0, ge=0, le=1, description="是否开放科室简介")
    is_final: int = Field(0, ge=0, le=1, description="是否终极科室")
    is_recommended: int = Field(0, ge=0, le=1, description="是否推荐")
    
    # 图片资源
    banner_image: Optional[str] = Field(None, max_length=500, description="banner图片URL")
    icon: Optional[str] = Field(None, max_length=500, description="科室图标URL")
    intro_images: Optional[str] = Field(None, description="简介图片集JSON")
    
    # 详情内容
    intro_content: Optional[str] = Field(None, description="富文本简介")
    features: Optional[str] = Field(None, description="科室特色JSON数组")
    appointment_notice: Optional[str] = Field(None, description="预约须知")
    
    # 联系信息
    phone: Optional[str] = Field(None, max_length=20, description="科室电话")
    location: Optional[str] = Field(None, max_length=100, description="位置/楼层")
    working_hours: Optional[str] = Field(None, max_length=200, description="工作时间")

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # 允许使用原始字段名或别名
    )
    
    name: Optional[str] = Field(None, max_length=100)
    parent_id: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = Field(None, ge=0)
    is_hot: Optional[int] = Field(None, ge=0, le=1)
    status: Optional[int] = Field(None, ge=0, le=1)
    
    # 基础配置
    store_id: Optional[str] = None
    tag: Optional[str] = Field(None, max_length=100)
    enable_banner: Optional[int] = Field(None, ge=0, le=1)
    enable_intro: Optional[int] = Field(None, ge=0, le=1)
    is_final: Optional[int] = Field(None, ge=0, le=1)
    is_recommended: Optional[int] = Field(None, ge=0, le=1)
    
    # 图片资源
    banner_image: Optional[str] = Field(None, max_length=500)
    icon: Optional[str] = Field(None, max_length=500)
    intro_images: Optional[str] = None
    
    # 详情内容
    intro_content: Optional[str] = None
    features: Optional[str] = None
    appointment_notice: Optional[str] = None
    
    # 联系信息
    phone: Optional[str] = Field(None, max_length=20)
    location: Optional[str] = Field(None, max_length=100)
    working_hours: Optional[str] = Field(None, max_length=200)

class DepartmentResponse(BaseModel):
    """科室响应模型 - 所有字段都可为空以兼容历史数据"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,  # 序列化时使用别名 (camelCase)
    )
    
    id: str
    name: str
    parent_id: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = 0
    is_hot: Optional[int] = 0
    status: Optional[int] = 1
    created_at: datetime
    updated_at: datetime
    
    # 基础配置
    store_id: Optional[str] = None
    store_name: Optional[str] = None
    tag: Optional[str] = None
    enable_banner: Optional[int] = 0
    enable_intro: Optional[int] = 0
    is_final: Optional[int] = 0
    is_recommended: Optional[int] = 0
    
    # 图片资源
    banner_image: Optional[str] = None
    icon: Optional[str] = None
    intro_images: Optional[str] = None
    
    # 详情内容
    intro_content: Optional[str] = None
    features: Optional[str] = None
    appointment_notice: Optional[str] = None
    
    # 联系信息
    phone: Optional[str] = None
    location: Optional[str] = None
    working_hours: Optional[str] = None

class DepartmentTreeNode(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    name: str
    parent_id: Optional[str] = None
    children: List['DepartmentTreeNode'] = []

DepartmentTreeNode.model_rebuild()

