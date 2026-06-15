from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.response import to_camel


class DepartmentBase(BaseModel):
    """科室基础模型"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # 允许使用原始字段名或别名
    )
    
    name: str = Field(..., max_length=100, description="科室名称")
    parent_id: str | None = Field(None, description="父级科室ID")
    description: str | None = Field(None, description="科室描述")
    sort_order: int = Field(0, ge=0, description="排序序号")
    is_hot: int = Field(0, ge=0, le=1, description="是否热门: 0否 1是")
    status: int = Field(1, ge=0, le=1, description="状态: 0禁用 1启用")
    
    # 基础配置
    store_id: str | None = Field(None, description="默认门店ID")
    tag: str | None = Field(None, max_length=100, description="科室标签")
    enable_banner: int = Field(0, ge=0, le=1, description="是否开放banner")
    enable_intro: int = Field(0, ge=0, le=1, description="是否开放科室简介")
    is_final: int = Field(0, ge=0, le=1, description="是否终极科室")
    is_recommended: int = Field(0, ge=0, le=1, description="是否推荐")
    
    # 图片资源
    banner_image: str | None = Field(None, max_length=500, description="banner图片URL")
    icon: str | None = Field(None, max_length=500, description="科室图标URL")
    intro_images: str | None = Field(None, description="简介图片集JSON")
    
    # 详情内容
    intro_content: str | None = Field(None, description="富文本简介")
    features: str | None = Field(None, description="科室特色JSON数组")
    appointment_notice: str | None = Field(None, description="预约须知")
    
    # 联系信息
    phone: str | None = Field(None, max_length=20, description="科室电话")
    location: str | None = Field(None, max_length=100, description="位置/楼层")
    working_hours: str | None = Field(None, max_length=200, description="工作时间")

    # 智能导诊
    keywords: list[str] | None = Field(None, description="症状关键词数组，用于智能导诊")

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    """更新科室请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # 允许使用原始字段名或别名
    )
    
    name: str | None = Field(None, max_length=100, description="科室名称")
    parent_id: str | None = Field(None, description="父级科室ID")
    description: str | None = Field(None, description="科室描述")
    sort_order: int | None = Field(None, ge=0, description="排序序号")
    is_hot: int | None = Field(None, ge=0, le=1, description="是否热门: 0否 1是")
    status: int | None = Field(None, ge=0, le=1, description="状态: 0禁用 1启用")
    
    # 基础配置
    store_id: str | None = Field(None, description="默认门店ID")
    tag: str | None = Field(None, max_length=100, description="科室标签")
    enable_banner: int | None = Field(None, ge=0, le=1, description="是否开放banner: 0否 1是")
    enable_intro: int | None = Field(None, ge=0, le=1, description="是否开放科室简介: 0否 1是")
    is_final: int | None = Field(None, ge=0, le=1, description="是否终极科室: 0否 1是")
    is_recommended: int | None = Field(None, ge=0, le=1, description="是否推荐: 0否 1是")
    
    # 图片资源
    banner_image: str | None = Field(None, max_length=500, description="banner图片URL")
    icon: str | None = Field(None, max_length=500, description="科室图标URL")
    intro_images: str | None = Field(None, description="简介图片集JSON")
    
    # 详情内容
    intro_content: str | None = Field(None, description="富文本简介")
    features: str | None = Field(None, description="科室特色JSON数组")
    appointment_notice: str | None = Field(None, description="预约须知")
    
    # 联系信息
    phone: str | None = Field(None, max_length=20, description="科室电话")
    location: str | None = Field(None, max_length=100, description="位置/楼层")
    working_hours: str | None = Field(None, max_length=200, description="工作时间")

    # 智能导诊
    keywords: list[str] | None = Field(None, description="症状关键词数组，用于智能导诊")

class DepartmentResponse(BaseModel):
    """科室响应模型 - 所有字段都可为空以兼容历史数据"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,  # 序列化时使用别名 (camelCase)
    )
    
    id: str = Field(..., description="科室ID")
    name: str = Field(..., description="科室名称")
    parent_id: str | None = Field(None, description="父级科室ID")
    description: str | None = Field(None, description="科室描述")
    sort_order: int | None = Field(0, description="排序序号")
    is_hot: int | None = Field(0, description="是否热门: 0否 1是")
    status: int | None = Field(1, description="状态: 0禁用 1启用")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    # 基础配置
    store_id: str | None = Field(None, description="默认门店ID")
    store_name: str | None = Field(None, description="门店名称")
    tag: str | None = Field(None, description="科室标签")
    enable_banner: int | None = Field(0, description="是否开放banner: 0否 1是")
    enable_intro: int | None = Field(0, description="是否开放科室简介: 0否 1是")
    is_final: int | None = Field(0, description="是否终极科室: 0否 1是")
    is_recommended: int | None = Field(0, description="是否推荐: 0否 1是")
    
    # 图片资源
    banner_image: str | None = Field(None, description="banner图片URL")
    icon: str | None = Field(None, description="科室图标URL")
    intro_images: str | None = Field(None, description="简介图片集JSON")
    
    # 详情内容
    intro_content: str | None = Field(None, description="富文本简介")
    features: str | None = Field(None, description="科室特色JSON数组")
    appointment_notice: str | None = Field(None, description="预约须知")
    
    # 联系信息
    phone: str | None = Field(None, description="科室电话")
    location: str | None = Field(None, description="位置/楼层")
    working_hours: str | None = Field(None, description="工作时间")

    # 智能导诊
    keywords: list[str] | None = Field(None, description="症状关键词数组，用于智能导诊")

class DepartmentTreeNode(BaseModel):
    """科室树节点"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str = Field(..., description="科室ID")
    name: str = Field(..., description="科室名称")
    parent_id: str | None = Field(None, description="父级科室ID")
    children: list['DepartmentTreeNode'] = Field(default=[], description="子科室列表")

DepartmentTreeNode.model_rebuild()

