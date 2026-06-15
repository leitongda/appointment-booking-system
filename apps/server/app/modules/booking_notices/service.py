"""预约须知服务"""
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant_context import get_current_tenant_id
from app.models.booking_notice import BookingNotice
from app.schemas.booking_notice import BookingNoticeCreate, BookingNoticeUpdate
from app.utils.audit import set_create_audit, set_update_audit


class BookingNoticeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _tenant_filter(self, stmt):
        """为查询添加租户过滤"""
        tenant_id = get_current_tenant_id()
        if tenant_id:
            return stmt.where(BookingNotice.tenant_id == tenant_id)
        return stmt

    async def get_by_id(self, notice_id: str) -> BookingNotice | None:
        """根据ID获取预约须知"""
        stmt = self._tenant_filter(
            select(BookingNotice).where(BookingNotice.id == notice_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_list(
        self,
        notice_type: str | None = None,
        status: int | None = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list[BookingNotice], int]:
        """获取预约须知列表"""
        query = self._tenant_filter(select(BookingNotice))
        count_query = self._tenant_filter(select(func.count(BookingNotice.id)))

        if notice_type:
            query = query.where(BookingNotice.type == notice_type)
            count_query = count_query.where(BookingNotice.type == notice_type)

        if status is not None:
            query = query.where(BookingNotice.status == status)
            count_query = count_query.where(BookingNotice.status == status)

        query = query.order_by(BookingNotice.sort_order.asc(), BookingNotice.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)

        return list(result.scalars().all()), count_result.scalar() or 0

    async def get_active_list(self, notice_type: str | None = None) -> list[BookingNotice]:
        """获取生效的预约须知列表（供小程序端调用）"""
        query = self._tenant_filter(select(BookingNotice).where(BookingNotice.status == 1))

        if notice_type:
            query = query.where(BookingNotice.type == notice_type)

        query = query.order_by(BookingNotice.sort_order.asc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, data: BookingNoticeCreate, operator_id: str | None = None) -> BookingNotice:
        """创建预约须知"""
        notice = BookingNotice(
            id=str(uuid.uuid4()),
            tenant_id=get_current_tenant_id(),
            type=data.type,
            title=data.title,
            content=data.content,
            sort_order=data.sort_order,
            status=data.status
        )
        set_create_audit(notice, operator_id)
        self.db.add(notice)

        await self.db.commit()
        await self.db.refresh(notice)
        return notice

    async def update(self, notice_id: str, data: BookingNoticeUpdate, operator_id: str | None = None) -> BookingNotice | None:
        """更新预约须知"""
        notice = await self.get_by_id(notice_id)
        if not notice:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(notice, key, value)

        set_update_audit(notice, operator_id)

        await self.db.commit()
        await self.db.refresh(notice)
        return notice

    async def delete(self, notice_id: str) -> bool:
        """删除预约须知"""
        notice = await self.get_by_id(notice_id)
        if not notice:
            return False

        await self.db.delete(notice)
        await self.db.commit()
        return True

    async def update_status(self, notice_id: str, status: int, operator_id: str | None = None) -> BookingNotice | None:
        """更新预约须知状态"""
        notice = await self.get_by_id(notice_id)
        if not notice:
            return None

        notice.status = status
        set_update_audit(notice, operator_id)

        await self.db.commit()
        await self.db.refresh(notice)
        return notice
