"""门店邮件接收人服务"""
import json
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import Store
from app.models.store_email_recipient import StoreEmailRecipient
from app.schemas.store_email_recipient import (
    StoreEmailRecipientCreate,
    StoreEmailRecipientQuery,
    StoreEmailRecipientUpdate,
)
from app.utils.audit import set_create_audit, set_update_audit


class StoreEmailRecipientService:
    """门店邮件接收人服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, recipient_id: str) -> StoreEmailRecipient | None:
        """根据ID获取接收人"""
        result = await self.db.execute(
            select(StoreEmailRecipient).where(StoreEmailRecipient.id == recipient_id)
        )
        return result.scalar_one_or_none()

    async def get_list(
        self, query: StoreEmailRecipientQuery
    ) -> tuple[list[StoreEmailRecipient], int]:
        """获取接收人列表（分页）"""
        stmt = select(StoreEmailRecipient)
        count_stmt = select(func.count(StoreEmailRecipient.id))

        if query.store_id:
            stmt = stmt.where(StoreEmailRecipient.store_id == query.store_id)
            count_stmt = count_stmt.where(StoreEmailRecipient.store_id == query.store_id)

        if query.status is not None:
            stmt = stmt.where(StoreEmailRecipient.status == query.status)
            count_stmt = count_stmt.where(StoreEmailRecipient.status == query.status)

        if query.keyword:
            keyword_filter = (
                StoreEmailRecipient.name.contains(query.keyword)
                | StoreEmailRecipient.email.contains(query.keyword)
            )
            stmt = stmt.where(keyword_filter)
            count_stmt = count_stmt.where(keyword_filter)

        stmt = stmt.order_by(StoreEmailRecipient.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)

        result = await self.db.execute(stmt)
        count_result = await self.db.execute(count_stmt)

        return list(result.scalars().all()), count_result.scalar() or 0

    async def create(
        self,
        data: StoreEmailRecipientCreate,
        operator_id: str | None = None,
    ) -> StoreEmailRecipient:
        """创建接收人"""
        # p3a8：写入时落租户维度（经 store 继承）
        store = await self.db.get(Store, data.store_id)
        recipient = StoreEmailRecipient(
            id=str(uuid.uuid4()),
            store_id=data.store_id,
            tenant_id=store.tenant_id if store else None,
            name=data.name,
            email=data.email,
            event_types=json.dumps(data.event_types, ensure_ascii=False),
            status=data.status,
        )
        set_create_audit(recipient, operator_id)
        self.db.add(recipient)
        await self.db.commit()
        await self.db.refresh(recipient)
        return recipient

    async def update(
        self,
        recipient_id: str,
        data: StoreEmailRecipientUpdate,
        operator_id: str | None = None,
    ) -> StoreEmailRecipient | None:
        """更新接收人"""
        recipient = await self.get_by_id(recipient_id)
        if not recipient:
            return None

        update_data = data.model_dump(exclude_unset=True)

        if "event_types" in update_data and update_data["event_types"] is not None:
            update_data["event_types"] = json.dumps(
                update_data["event_types"], ensure_ascii=False
            )

        for field, value in update_data.items():
            setattr(recipient, field, value)

        set_update_audit(recipient, operator_id)
        await self.db.commit()
        await self.db.refresh(recipient)
        return recipient

    async def delete(self, recipient_id: str) -> bool:
        """删除接收人"""
        recipient = await self.get_by_id(recipient_id)
        if not recipient:
            return False

        await self.db.delete(recipient)
        await self.db.commit()
        return True

    async def get_recipients_by_event(
        self, store_id: str, event_type: str
    ) -> list[StoreEmailRecipient]:
        """查询某门店某事件的启用接收人"""
        result = await self.db.execute(
            select(StoreEmailRecipient).where(
                StoreEmailRecipient.store_id == store_id,
                StoreEmailRecipient.status == 1,
            )
        )
        all_recipients = result.scalars().all()

        matched = []
        for r in all_recipients:
            if not r.event_types:
                continue
            try:
                subscribed = json.loads(r.event_types)
                if event_type in subscribed:
                    matched.append(r)
            except (json.JSONDecodeError, TypeError):
                continue

        return matched
