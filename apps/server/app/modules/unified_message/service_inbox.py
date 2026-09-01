"""统一消息服务 - 消息读取/状态 Mixin

包含 7 个消息读取/状态方法（get_user_messages/get_unread_count/mark_as_read/
mark_all_as_read/delete/delete_all_read/get_by_id）。
方法体逐字从原 service.py 搬迁，逻辑/签名不变。
"""
from datetime import datetime

from sqlalchemy import and_, func, select, update

from app.modules.unified_message.models import (
    READ_STATUS_DELETED,
    READ_STATUS_READ,
    READ_STATUS_UNREAD,
    NotificationGroup,
    NotificationRecipient,
)
from app.modules.unified_message.schemas import (
    MessageQuery,
    UnreadCountResponse,
)


class UnifiedMessageInboxMixin:
    """统一消息服务 - 消息读取/状态 Mixin"""

    # -----------------------------------------------------------------------
    # 查询（兼容旧 API）
    # -----------------------------------------------------------------------

    async def get_user_messages(
        self, user_id: str, user_type: str, query: MessageQuery
    ) -> tuple[list[dict], int]:
        """获取用户消息列表（兼容旧 MessageService.get_user_messages）"""
        # 使用 join 一次性获取 recipient 和 group 数据，避免 N+1 查询
        stmt = (
            select(
                NotificationRecipient,
                NotificationGroup.store_id,
                NotificationGroup.message_type,
                NotificationGroup.related_id,
            )
            .join(NotificationGroup, NotificationRecipient.group_id == NotificationGroup.id)
            .where(
                and_(
                    NotificationRecipient.user_id == user_id,
                    NotificationRecipient.user_type == user_type,
                    NotificationRecipient.is_read != READ_STATUS_DELETED,
                )
            )
        )
        count_stmt = (
            select(func.count(NotificationRecipient.id))
            .where(
                and_(
                    NotificationRecipient.user_id == user_id,
                    NotificationRecipient.user_type == user_type,
                    NotificationRecipient.is_read != READ_STATUS_DELETED,
                )
            )
        )

        # 按消息类型过滤
        if query.message_type:
            stmt = stmt.where(NotificationGroup.message_type == query.message_type)
            count_stmt = count_stmt.join(NotificationGroup, NotificationRecipient.group_id == NotificationGroup.id)
            count_stmt = count_stmt.where(NotificationGroup.message_type == query.message_type)

        # 按已读状态过滤
        if query.is_read is not None:
            stmt = stmt.where(NotificationRecipient.is_read == query.is_read)
            count_stmt = count_stmt.where(NotificationRecipient.is_read == query.is_read)

        stmt = stmt.order_by(NotificationRecipient.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)

        result = await self.db.execute(stmt)
        count_result = await self.db.execute(count_stmt)

        rows = result.all()
        total = count_result.scalar() or 0

        # 转换为与旧 API 兼容的 dict 格式
        messages = []
        for r, store_id, message_type, related_id in rows:
            messages.append({
                "id": r.id,
                "store_id": store_id,
                "user_id": r.user_id,
                "user_type": r.user_type,
                "title": r.title,
                "content": r.content,
                "message_type": message_type,
                "related_id": related_id,
                "is_read": r.is_read,
                "read_at": r.read_at,
                "created_at": r.created_at,
            })

        return messages, total

    async def get_unread_count(self, user_id: str, user_type: str) -> UnreadCountResponse:
        """获取未读消息数量（兼容旧 MessageService.get_unread_count）"""
        base_condition = and_(
            NotificationRecipient.user_id == user_id,
            NotificationRecipient.user_type == user_type,
            NotificationRecipient.is_read == READ_STATUS_UNREAD,
        )

        # 使用单条 GROUP BY 查询获取所有消息类型的未读数
        stmt = (
            select(
                NotificationGroup.message_type,
                func.count(NotificationRecipient.id).label("count"),
            )
            .join(NotificationGroup, NotificationRecipient.group_id == NotificationGroup.id)
            .where(base_condition)
            .group_by(NotificationGroup.message_type)
        )
        result = await self.db.execute(stmt)
        type_counts = {row[0]: row[1] for row in result.all()}

        # 计算总数
        total = sum(type_counts.values())

        return UnreadCountResponse(
            total=total,
            appointment=type_counts.get("appointment", 0),
            consultation=type_counts.get("consultation", 0),
            schedule=type_counts.get("schedule", 0),
            system=type_counts.get("system", 0),
            stop_clinic=type_counts.get("stop_clinic", 0),
            feedback=type_counts.get("feedback", 0),
        )

    async def mark_as_read(self, message_id: str, user_id: str) -> bool:
        """标记单条消息为已读"""
        result = await self.db.execute(
            update(NotificationRecipient)
            .where(
                and_(
                    NotificationRecipient.id == message_id,
                    NotificationRecipient.user_id == user_id,
                )
            )
            .values(is_read=READ_STATUS_READ, read_at=datetime.utcnow())
        )
        await self.db.commit()
        return result.rowcount > 0

    async def mark_all_as_read(
        self, user_id: str, user_type: str, message_type: str | None = None
    ) -> int:
        """标记所有消息为已读"""
        stmt = (
            update(NotificationRecipient)
            .where(
                and_(
                    NotificationRecipient.user_id == user_id,
                    NotificationRecipient.user_type == user_type,
                    NotificationRecipient.is_read == READ_STATUS_UNREAD,
                )
            )
            .values(is_read=READ_STATUS_READ, read_at=datetime.utcnow())
        )

        if message_type:
            # 需要 join NotificationGroup 来过滤 message_type
            # SQLAlchemy update 不直接支持 join，使用 subquery
            group_ids = select(NotificationGroup.id).where(
                NotificationGroup.message_type == message_type
            )
            stmt = stmt.where(NotificationRecipient.group_id.in_(group_ids))

        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def delete(self, message_id: str, user_id: str) -> bool:
        """删除单条消息（软删除：标记为已删除）

        新表使用 NotificationRecipient，删除 = 将 is_read 标记为 READ_STATUS_DELETED。
        """
        result = await self.db.execute(
            update(NotificationRecipient)
            .where(
                and_(
                    NotificationRecipient.id == message_id,
                    NotificationRecipient.user_id == user_id,
                )
            )
            .values(is_read=READ_STATUS_DELETED)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def delete_all_read(self, user_id: str, user_type: str) -> int:
        """删除所有已读消息（软删除：标记为已删除）"""
        result = await self.db.execute(
            update(NotificationRecipient)
            .where(
                and_(
                    NotificationRecipient.user_id == user_id,
                    NotificationRecipient.user_type == user_type,
                    NotificationRecipient.is_read == READ_STATUS_READ,
                )
            )
            .values(is_read=READ_STATUS_DELETED)
        )
        await self.db.commit()
        return result.rowcount

    async def get_by_id(self, message_id: str, user_id: str) -> NotificationRecipient | None:
        """获取单条消息详情

        Args:
            message_id: 消息 ID
            user_id: 用户 ID（用于权限校验）

        Returns:
            消息对象，不存在或无权限返回 None
        """
        from sqlalchemy import select

        stmt = select(NotificationRecipient).where(
            and_(
                NotificationRecipient.id == message_id,
                NotificationRecipient.user_id == user_id,
                NotificationRecipient.is_read != READ_STATUS_DELETED,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
