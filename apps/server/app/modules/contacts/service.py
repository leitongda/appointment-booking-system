"""通讯录联系人业务逻辑"""

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.contact import (
    ChannelAccount,
    Contact,
    ContactChannel,
    ContactGroup,
    ContactTag,
    contact_group_members,
    contact_tag_members,
)


class ContactService:
    """联系人服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================================
    # 列表查询
    # ============================================================

    async def get_list(
        self,
        tenant_id: str,
        keyword: str | None = None,
        contact_type: str | None = None,
        status: int | None = None,
        group_id: str | None = None,
        tag_ids: list[str] | None = None,
        store_id: str | None = None,
        department_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Contact], int]:
        """获取联系人列表"""
        query = select(Contact).where(
            Contact.tenant_id == tenant_id,
            Contact.deleted_at.is_(None),
        )

        # 搜索
        if keyword:
            like_pattern = f"%{keyword}%"
            query = query.where(or_(
                Contact.name.ilike(like_pattern),
                Contact.phone.ilike(like_pattern),
                Contact.email.ilike(like_pattern),
                Contact.nickname.ilike(like_pattern),
            ))

        # 筛选
        if contact_type:
            query = query.where(Contact.contact_type == contact_type)
        if status is not None:
            query = query.where(Contact.status == status)
        if store_id:
            query = query.where(Contact.store_id == store_id)
        if department_id:
            query = query.where(Contact.department_id == department_id)

        # 分组筛选
        if group_id:
            query = query.join(
                contact_group_members, contact_group_members.c.contact_id == Contact.id
            ).where(contact_group_members.c.group_id == group_id)

        # 标签筛选
        if tag_ids:
            query = query.join(
                contact_tag_members, contact_tag_members.c.contact_id == Contact.id
            ).where(contact_tag_members.c.tag_id.in_(tag_ids))

        # 总数
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # 分页
        query = query.order_by(Contact.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        # 加载关联
        query = query.options(
            selectinload(Contact.groups),
            selectinload(Contact.tags),
        )

        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return items, total

    # ============================================================
    # 详情查询
    # ============================================================

    async def get_by_id(self, contact_id: str, tenant_id: str) -> Contact | None:
        """获取联系人详情"""
        query = select(Contact).where(
            Contact.id == contact_id,
            Contact.tenant_id == tenant_id,
            Contact.deleted_at.is_(None),
        ).options(
            selectinload(Contact.groups),
            selectinload(Contact.tags),
            selectinload(Contact.channels),
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    # ============================================================
    # 创建
    # ============================================================

    async def create(self, data: dict, tenant_id: str, created_by: str | None = None) -> Contact:
        """创建联系人"""
        group_ids = data.pop("group_ids", None)
        tag_ids = data.pop("tag_ids", None)
        channels_data = data.pop("channels", None)

        contact = Contact(
            **data,
            tenant_id=tenant_id,
            created_by=created_by,
        )
        self.db.add(contact)
        await self.db.flush()

        # 关联分组
        if group_ids:
            for gid in group_ids:
                self.db.add(contact_group_members(
                    contact_id=contact.id,
                    group_id=gid,
                ))

        # 关联标签
        if tag_ids:
            for tid in tag_ids:
                self.db.add(contact_tag_members(
                    contact_id=contact.id,
                    tag_id=tid,
                ))

        # 创建渠道信息
        if channels_data:
            for ch in channels_data:
                self.db.add(ContactChannel(
                    contact_id=contact.id,
                    **ch,
                ))

        await self.db.flush()
        return contact

    # ============================================================
    # 更新
    # ============================================================

    async def update(self, contact_id: str, data: dict, tenant_id: str, updated_by: str | None = None) -> Contact | None:
        """更新联系人"""
        contact = await self.get_by_id(contact_id, tenant_id)
        if not contact:
            return None

        group_ids = data.pop("group_ids", None)
        tag_ids = data.pop("tag_ids", None)
        channels_data = data.pop("channels", None)

        # 更新基础字段
        for key, value in data.items():
            if hasattr(contact, key):
                setattr(contact, key, value)
        contact.updated_by = updated_by

        # 更新分组（全量替换）
        if group_ids is not None:
            await self.db.execute(
                delete(contact_group_members).where(contact_group_members.c.contact_id == contact_id)
            )
            for gid in group_ids:
                self.db.add(contact_group_members(contact_id=contact_id, group_id=gid))

        # 更新标签（全量替换）
        if tag_ids is not None:
            await self.db.execute(
                delete(contact_tag_members).where(contact_tag_members.c.contact_id == contact_id)
            )
            for tid in tag_ids:
                self.db.add(contact_tag_members(contact_id=contact_id, tag_id=tid))

        # 更新渠道（全量替换）
        if channels_data is not None:
            await self.db.execute(
                delete(ContactChannel).where(ContactChannel.contact_id == contact_id)
            )
            for ch in channels_data:
                self.db.add(ContactChannel(contact_id=contact_id, **ch))

        await self.db.flush()
        return contact

    # ============================================================
    # 删除
    # ============================================================

    async def delete(self, contact_id: str, tenant_id: str) -> bool:
        """软删除联系人"""
        contact = await self.get_by_id(contact_id, tenant_id)
        if not contact:
            return False
        from datetime import datetime
        contact.deleted_at = datetime.utcnow()
        await self.db.flush()
        return True

    async def batch_delete(self, ids: list[str], tenant_id: str) -> int:
        """批量软删除"""
        from datetime import datetime
        query = select(Contact).where(
            Contact.id.in_(ids),
            Contact.tenant_id == tenant_id,
            Contact.deleted_at.is_(None),
        )
        result = await self.db.execute(query)
        contacts = list(result.scalars().all())
        for c in contacts:
            c.deleted_at = datetime.utcnow()
        await self.db.flush()
        return len(contacts)

    # ============================================================
    # 批量操作
    # ============================================================

    async def batch_move_group(self, ids: list[str], group_id: str, tenant_id: str) -> int:
        """批量移动到分组"""
        # 先删除这些联系人的旧分组关联
        await self.db.execute(
            delete(contact_group_members).where(contact_group_members.c.contact_id.in_(ids))
        )
        # 添加新分组关联
        for cid in ids:
            self.db.add(contact_group_members(contact_id=cid, group_id=group_id))
        await self.db.flush()
        return len(ids)

    async def batch_add_tags(self, ids: list[str], tag_ids: list[str], tenant_id: str) -> int:
        """批量打标签"""
        for cid in ids:
            for tid in tag_ids:
                # 跳过已存在的关联
                existing = await self.db.execute(
                    select(contact_tag_members).where(
                        contact_tag_members.c.contact_id == cid,
                        contact_tag_members.c.tag_id == tid,
                    )
                )
                if not existing.first():
                    self.db.add(contact_tag_members(contact_id=cid, tag_id=tid))
        await self.db.flush()
        return len(ids)

    async def batch_remove_tags(self, ids: list[str], tag_ids: list[str], tenant_id: str) -> int:
        """批量移除标签"""
        await self.db.execute(
            delete(contact_tag_members).where(
                contact_tag_members.c.contact_id.in_(ids),
                contact_tag_members.c.tag_id.in_(tag_ids),
            )
        )
        await self.db.flush()
        return len(ids)


class ContactGroupService:
    """联系人分组服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tree(self, tenant_id: str) -> list[ContactGroup]:
        """获取分组树"""
        query = select(ContactGroup).where(
            ContactGroup.tenant_id == tenant_id,
        ).order_by(ContactGroup.sort_order, ContactGroup.created_at)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, data: dict, tenant_id: str, created_by: str | None = None) -> ContactGroup:
        """创建分组"""
        group = ContactGroup(**data, tenant_id=tenant_id, created_by=created_by)
        self.db.add(group)
        await self.db.flush()
        return group

    async def update(self, group_id: str, data: dict, tenant_id: str, updated_by: str | None = None) -> ContactGroup | None:
        """更新分组"""
        query = select(ContactGroup).where(
            ContactGroup.id == group_id,
            ContactGroup.tenant_id == tenant_id,
        )
        result = await self.db.execute(query)
        group = result.scalar_one_or_none()
        if not group:
            return None
        for key, value in data.items():
            if hasattr(group, key):
                setattr(group, key, value)
        group.updated_by = updated_by
        await self.db.flush()
        return group

    async def delete(self, group_id: str, tenant_id: str) -> bool:
        """删除分组"""
        query = select(ContactGroup).where(
            ContactGroup.id == group_id,
            ContactGroup.tenant_id == tenant_id,
        )
        result = await self.db.execute(query)
        group = result.scalar_one_or_none()
        if not group:
            return False
        await self.db.delete(group)
        await self.db.flush()
        return True


class ContactTagService:
    """联系人标签服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(self, tenant_id: str) -> list[ContactTag]:
        """获取标签列表"""
        query = select(ContactTag).where(
            ContactTag.tenant_id == tenant_id,
        ).order_by(ContactTag.sort_order, ContactTag.created_at)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, data: dict, tenant_id: str, created_by: str | None = None) -> ContactTag:
        """创建标签"""
        tag = ContactTag(**data, tenant_id=tenant_id, created_by=created_by)
        self.db.add(tag)
        await self.db.flush()
        return tag

    async def update(self, tag_id: str, data: dict, tenant_id: str, updated_by: str | None = None) -> ContactTag | None:
        """更新标签"""
        query = select(ContactTag).where(
            ContactTag.id == tag_id,
            ContactTag.tenant_id == tenant_id,
        )
        result = await self.db.execute(query)
        tag = result.scalar_one_or_none()
        if not tag:
            return None
        for key, value in data.items():
            if hasattr(tag, key):
                setattr(tag, key, value)
        tag.updated_by = updated_by
        await self.db.flush()
        return tag

    async def delete(self, tag_id: str, tenant_id: str) -> bool:
        """删除标签"""
        query = select(ContactTag).where(
            ContactTag.id == tag_id,
            ContactTag.tenant_id == tenant_id,
        )
        result = await self.db.execute(query)
        tag = result.scalar_one_or_none()
        if not tag:
            return False
        await self.db.delete(tag)
        await self.db.flush()
        return True


class ChannelAccountService:
    """渠道账号服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        tenant_id: str,
        channel_type: str | None = None,
        store_id: str | None = None,
        status: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ChannelAccount], int]:
        """获取渠道账号列表"""
        query = select(ChannelAccount).where(ChannelAccount.tenant_id == tenant_id)

        if channel_type:
            query = query.where(ChannelAccount.channel_type == channel_type)
        if store_id is not None:
            query = query.where(ChannelAccount.store_id == store_id)
        if status is not None:
            query = query.where(ChannelAccount.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        query = query.order_by(ChannelAccount.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def get_by_id(self, account_id: str, tenant_id: str) -> ChannelAccount | None:
        """获取渠道账号详情"""
        query = select(ChannelAccount).where(
            ChannelAccount.id == account_id,
            ChannelAccount.tenant_id == tenant_id,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create(self, data: dict, tenant_id: str, created_by: str | None = None) -> ChannelAccount:
        """创建渠道账号"""
        account = ChannelAccount(**data, tenant_id=tenant_id, created_by=created_by)
        self.db.add(account)
        await self.db.flush()
        return account

    async def update(self, account_id: str, data: dict, tenant_id: str, updated_by: str | None = None) -> ChannelAccount | None:
        """更新渠道账号"""
        account = await self.get_by_id(account_id, tenant_id)
        if not account:
            return None
        for key, value in data.items():
            if hasattr(account, key):
                setattr(account, key, value)
        account.updated_by = updated_by
        await self.db.flush()
        return account

    async def delete(self, account_id: str, tenant_id: str) -> bool:
        """删除渠道账号"""
        account = await self.get_by_id(account_id, tenant_id)
        if not account:
            return False
        await self.db.delete(account)
        await self.db.flush()
        return True
