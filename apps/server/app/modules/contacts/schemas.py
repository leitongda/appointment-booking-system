"""通讯录模块 Pydantic schemas"""

from datetime import datetime

from pydantic import Field

from app.schemas.base import BaseSchema


# ============================================================
# 联系人相关
# ============================================================


class ChannelInput(BaseSchema):
    """渠道信息输入"""
    channel_type: str = Field(..., description="渠道类型: phone/email/wechat/sms")
    channel_value: str = Field(..., description="渠道标识值")
    is_primary: int = Field(0, description="是否主要渠道 0否 1是")


class ContactCreate(BaseSchema):
    """创建联系人"""
    name: str = Field(..., min_length=1, max_length=100, description="联系人姓名")
    nickname: str | None = Field(None, max_length=50, description="昵称")
    avatar: str | None = Field(None, max_length=255, description="头像URL")
    gender: int = Field(0, description="性别 0未知 1男 2女")
    phone: str | None = Field(None, max_length=20, description="手机号")
    email: str | None = Field(None, max_length=100, description="邮箱")
    contact_type: str = Field(..., max_length=20, description="联系人类型: patient/doctor/admin/staff/external")
    source_type: str | None = Field(None, max_length=20, description="来源类型")
    source_id: str | None = Field(None, description="来源记录ID")
    account_id: str | None = Field(None, description="关联账号ID")
    department_id: str | None = Field(None, description="所属科室ID")
    store_id: str | None = Field(None, description="所属门店ID")
    position: str | None = Field(None, max_length=50, description="职位/职称")
    organization: str | None = Field(None, max_length=200, description="所属机构")
    notes: str | None = Field(None, description="备注")
    group_ids: list[str] | None = Field(None, description="分组ID列表")
    tag_ids: list[str] | None = Field(None, description="标签ID列表")
    channels: list[ChannelInput] | None = Field(None, description="渠道信息列表")


class ContactUpdate(BaseSchema):
    """更新联系人"""
    name: str | None = Field(None, min_length=1, max_length=100, description="联系人姓名")
    nickname: str | None = Field(None, max_length=50, description="昵称")
    avatar: str | None = Field(None, max_length=255, description="头像URL")
    gender: int | None = Field(None, description="性别 0未知 1男 2女")
    phone: str | None = Field(None, max_length=20, description="手机号")
    email: str | None = Field(None, max_length=100, description="邮箱")
    contact_type: str | None = Field(None, max_length=20, description="联系人类型")
    department_id: str | None = Field(None, description="所属科室ID")
    store_id: str | None = Field(None, description="所属门店ID")
    position: str | None = Field(None, max_length=50, description="职位/职称")
    organization: str | None = Field(None, max_length=200, description="所属机构")
    notes: str | None = Field(None, description="备注")
    status: int | None = Field(None, description="状态 0禁用 1正常")
    group_ids: list[str] | None = Field(None, description="分组ID列表（全量替换）")
    tag_ids: list[str] | None = Field(None, description="标签ID列表（全量替换）")
    channels: list[ChannelInput] | None = Field(None, description="渠道信息列表（全量替换）")


class ChannelResponse(BaseSchema):
    """渠道信息响应"""
    id: str
    channel_type: str
    channel_value: str
    is_primary: int
    verified: int


class GroupBriefResponse(BaseSchema):
    """分组简要信息"""
    id: str
    name: str


class TagBriefResponse(BaseSchema):
    """标签简要信息"""
    id: str
    name: str
    color: str | None = None


class ContactResponse(BaseSchema):
    """联系人详情响应"""
    id: str
    tenant_id: str
    name: str
    nickname: str | None = None
    avatar: str | None = None
    gender: int = 0
    phone: str | None = None
    email: str | None = None
    contact_type: str
    source_type: str | None = None
    source_id: str | None = None
    account_id: str | None = None
    department_id: str | None = None
    store_id: str | None = None
    position: str | None = None
    organization: str | None = None
    notes: str | None = None
    status: int = 1
    last_contact_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: str | None = None
    updated_by: str | None = None
    groups: list[GroupBriefResponse] = []
    tags: list[TagBriefResponse] = []
    channels: list[ChannelResponse] = []


class ContactListResponse(BaseSchema):
    """联系人列表响应（精简版）"""
    id: str
    name: str
    nickname: str | None = None
    avatar: str | None = None
    gender: int = 0
    phone: str | None = None
    email: str | None = None
    contact_type: str
    organization: str | None = None
    status: int = 1
    last_contact_at: datetime | None = None
    created_at: datetime | None = None
    groups: list[GroupBriefResponse] = []
    tags: list[TagBriefResponse] = []


class ContactQuery(BaseSchema):
    """列表查询参数"""
    keyword: str | None = Field(None, description="搜索关键词（姓名/手机号/邮箱）")
    contact_type: str | None = Field(None, description="联系人类型筛选")
    status: int | None = Field(None, description="状态筛选")
    group_id: str | None = Field(None, description="分组ID筛选")
    tag_ids: list[str] | None = Field(None, description="标签ID列表筛选")
    store_id: str | None = Field(None, description="门店ID筛选")
    department_id: str | None = Field(None, description="科室ID筛选")


# ============================================================
# 分组相关
# ============================================================


class GroupCreate(BaseSchema):
    """创建分组"""
    name: str = Field(..., min_length=1, max_length=100, description="分组名称")
    description: str | None = Field(None, max_length=500, description="分组描述")
    parent_id: str | None = Field(None, description="父分组ID")
    sort_order: int = Field(0, description="排序")


class GroupUpdate(BaseSchema):
    """更新分组"""
    name: str | None = Field(None, min_length=1, max_length=100, description="分组名称")
    description: str | None = Field(None, max_length=500, description="分组描述")
    parent_id: str | None = Field(None, description="父分组ID")
    sort_order: int | None = Field(None, description="排序")
    status: int | None = Field(None, description="状态 0禁用 1正常")


class GroupResponse(BaseSchema):
    """分组响应"""
    id: str
    tenant_id: str
    name: str
    description: str | None = None
    parent_id: str | None = None
    sort_order: int = 0
    status: int = 1
    children_count: int = Field(0, description="子分组数量")
    contact_count: int = Field(0, description="联系人数量")
    created_at: datetime | None = None
    updated_at: datetime | None = None


class GroupTreeResponse(BaseSchema):
    """树形结构响应"""
    id: str
    name: str
    description: str | None = None
    parent_id: str | None = None
    sort_order: int = 0
    status: int = 1
    contact_count: int = 0
    children: list["GroupTreeResponse"] = []


# ============================================================
# 标签相关
# ============================================================


class TagCreate(BaseSchema):
    """创建标签"""
    name: str = Field(..., min_length=1, max_length=50, description="标签名称")
    color: str | None = Field(None, max_length=20, description="标签颜色")
    sort_order: int = Field(0, description="排序")


class TagUpdate(BaseSchema):
    """更新标签"""
    name: str | None = Field(None, min_length=1, max_length=50, description="标签名称")
    color: str | None = Field(None, max_length=20, description="标签颜色")
    sort_order: int | None = Field(None, description="排序")


class TagResponse(BaseSchema):
    """标签响应"""
    id: str
    tenant_id: str
    name: str
    color: str | None = None
    sort_order: int = 0
    contact_count: int = Field(0, description="关联联系人数量")
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ============================================================
# 批量操作
# ============================================================


class BatchDeleteRequest(BaseSchema):
    """批量删除"""
    ids: list[str] = Field(..., min_length=1, description="联系人ID列表")


class BatchMoveGroupRequest(BaseSchema):
    """批量移动分组"""
    ids: list[str] = Field(..., min_length=1, description="联系人ID列表")
    group_id: str = Field(..., description="目标分组ID")


class BatchTagRequest(BaseSchema):
    """批量打标签 / 移除标签"""
    ids: list[str] = Field(..., min_length=1, description="联系人ID列表")
    tag_ids: list[str] = Field(..., min_length=1, description="标签ID列表")


# ============================================================
# 渠道账号相关
# ============================================================


class ChannelAccountCreate(BaseSchema):
    """创建渠道账号"""
    store_id: str | None = Field(None, description="门店ID（NULL=全局账号）")
    channel_type: str = Field(..., max_length=20, description="渠道类型: sms/email/wechat/webhook")
    name: str = Field(..., min_length=1, max_length=100, description="账号名称")
    config: str = Field(..., description="渠道配置JSON")
    status: int = Field(1, description="状态 0禁用 1正常")
    is_default: int = Field(0, description="是否为该渠道默认账号 0否 1是")


class ChannelAccountUpdate(BaseSchema):
    """更新渠道账号"""
    store_id: str | None = Field(None, description="门店ID")
    channel_type: str | None = Field(None, max_length=20, description="渠道类型")
    name: str | None = Field(None, min_length=1, max_length=100, description="账号名称")
    config: str | None = Field(None, description="渠道配置JSON")
    status: int | None = Field(None, description="状态 0禁用 1正常")
    is_default: int | None = Field(None, description="是否为该渠道默认账号")


class ChannelAccountResponse(BaseSchema):
    """渠道账号响应（不含敏感配置）"""
    id: str
    tenant_id: str
    store_id: str | None = None
    channel_type: str
    name: str
    status: int = 1
    is_default: int = 0
    last_sync_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ChannelAccountListResponse(BaseSchema):
    """渠道账号列表响应"""
    id: str
    channel_type: str
    name: str
    store_id: str | None = None
    status: int = 1
    is_default: int = 0
    last_sync_at: datetime | None = None
    created_at: datetime | None = None


class ChannelAccountTestResponse(BaseSchema):
    """渠道账号测试连接响应"""
    success: bool
    message: str
