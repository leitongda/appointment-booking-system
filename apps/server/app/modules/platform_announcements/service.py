"""平台公告服务"""
import json
import uuid
from datetime import datetime
from typing import Optional, List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from app.models.platform_announcement import PlatformAnnouncement
from app.models.tenant import Tenant, TenantNotification
from app.schemas.platform_announcement import PlatformAnnouncementCreate, PlatformAnnouncementUpdate


class PlatformAnnouncementService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, announcement_id: str) -> Optional[PlatformAnnouncement]:
        result = await self.db.execute(
            select(PlatformAnnouncement).where(PlatformAnnouncement.id == announcement_id)
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        status: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[PlatformAnnouncement], int]:
        query = select(PlatformAnnouncement)
        count_query = select(func.count(PlatformAnnouncement.id))

        conditions = []
        if status:
            conditions.append(PlatformAnnouncement.status == status)
        if keyword:
            conditions.append(
                PlatformAnnouncement.title.contains(keyword)
                | PlatformAnnouncement.content.contains(keyword)
            )

        if conditions:
            condition = and_(*conditions)
            query = query.where(condition)
            count_query = count_query.where(condition)

        query = query.order_by(desc(PlatformAnnouncement.priority), desc(PlatformAnnouncement.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)

        return list(result.scalars().all()), count_result.scalar() or 0

    async def create(
        self,
        data: PlatformAnnouncementCreate,
        publisher_id: Optional[str] = None,
        publisher_name: Optional[str] = None,
    ) -> PlatformAnnouncement:
        announcement = PlatformAnnouncement(
            id=str(uuid.uuid4()),
            title=data.title,
            content=data.content,
            target_type=data.target_type,
            target_tenant_ids=json.dumps(data.target_tenant_ids) if data.target_tenant_ids else None,
            priority=data.priority,
            publish_at=data.publish_at,
            expire_at=data.expire_at,
            publisher_id=publisher_id,
            publisher_name=publisher_name,
        )
        self.db.add(announcement)
        await self.db.commit()
        await self.db.refresh(announcement)
        return announcement

    async def update(
        self,
        announcement_id: str,
        data: PlatformAnnouncementUpdate,
    ) -> Optional[PlatformAnnouncement]:
        announcement = await self.get_by_id(announcement_id)
        if not announcement:
            return None

        # 已发布的公告不允许修改核心内容
        if announcement.status == "published":
            raise ValueError("已发布的公告不允许修改，请先撤回")

        update_data = data.model_dump(exclude_unset=True)
        if "target_tenant_ids" in update_data and update_data["target_tenant_ids"] is not None:
            update_data["target_tenant_ids"] = json.dumps(update_data["target_tenant_ids"])

        for key, value in update_data.items():
            setattr(announcement, key, value)

        await self.db.commit()
        await self.db.refresh(announcement)
        return announcement

    async def publish(self, announcement_id: str) -> Optional[PlatformAnnouncement]:
        """发布公告：将公告状态改为 published，并为目标租户生成通知"""
        announcement = await self.get_by_id(announcement_id)
        if not announcement:
            return None

        if announcement.status == "published":
            raise ValueError("公告已发布")

        # 确定目标租户
        target_tenant_ids = []
        if announcement.target_type == "all":
            result = await self.db.execute(select(Tenant.id).where(Tenant.deleted_at.is_(None)))
            target_tenant_ids = [row[0] for row in result.all()]
        else:
            try:
                target_tenant_ids = json.loads(announcement.target_tenant_ids or "[]")
            except Exception:
                target_tenant_ids = []

        # 更新公告状态
        announcement.status = "published"
        announcement.publish_at = datetime.utcnow()
        announcement.total_count = len(target_tenant_ids)

        # 为每个目标租户生成通知
        for tenant_id in target_tenant_ids:
            notification = TenantNotification(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                notification_type="platform_announcement",
                title=announcement.title,
                content=announcement.content,
                priority=announcement.priority,
                extra_metadata=json.dumps({"announcement_id": announcement.id}),
            )
            self.db.add(notification)

        await self.db.commit()
        await self.db.refresh(announcement)
        return announcement

    async def revoke(self, announcement_id: str) -> Optional[PlatformAnnouncement]:
        """撤回公告"""
        announcement = await self.get_by_id(announcement_id)
        if not announcement:
            return None

        if announcement.status != "published":
            raise ValueError("只能撤回已发布的公告")

        announcement.status = "revoked"
        await self.db.commit()
        await self.db.refresh(announcement)
        return announcement

    async def delete(self, announcement_id: str) -> bool:
        announcement = await self.get_by_id(announcement_id)
        if not announcement:
            return False

        await self.db.delete(announcement)
        await self.db.commit()
        return True
