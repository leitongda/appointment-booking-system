import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.middleware.tenant_context import get_current_tenant_id
from app.models.schedule import Schedule
from app.models.schedule_room import ScheduleRoom
from app.utils.audit import set_create_audit, set_update_audit


class ScheduleRoomService:
    """诊室服务

    Args:
        db: 数据库会话
        tenant_id: 管理员账号租户锚点（R1-13）。查询/写入以锚点强过滤；
            未传入时才回退请求上下文（兼容内部调用）。
    """

    def __init__(self, db: AsyncSession, tenant_id: str | None = None):
        self.db = db
        self.tenant_id = tenant_id

    def _tenant(self) -> str | None:
        """账号锚点优先，未提供时回退请求上下文。"""
        if self.tenant_id is not None:
            return self.tenant_id
        return get_current_tenant_id()

    async def get_by_id(self, room_id: str) -> ScheduleRoom | None:
        conditions = [ScheduleRoom.id == room_id]
        tenant_id = self._tenant()
        if tenant_id is not None:
            conditions.append(ScheduleRoom.tenant_id == tenant_id)

        result = await self.db.execute(
            select(ScheduleRoom)
            .options(selectinload(ScheduleRoom.store), selectinload(ScheduleRoom.department))
            .where(and_(*conditions))
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        name: str | None = None,
        status: int | None = None,
        store_id: str | None = None,
        department_id: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[ScheduleRoom], int]:
        query = select(ScheduleRoom).options(
            selectinload(ScheduleRoom.store), selectinload(ScheduleRoom.department)
        )
        count_query = select(func.count(ScheduleRoom.id))

        # 租户过滤
        tenant_id = self._tenant()
        if tenant_id is not None:
            query = query.where(ScheduleRoom.tenant_id == tenant_id)
            count_query = count_query.where(ScheduleRoom.tenant_id == tenant_id)

        if name:
            query = query.where(ScheduleRoom.name.contains(name))
            count_query = count_query.where(ScheduleRoom.name.contains(name))
        if status is not None:
            query = query.where(ScheduleRoom.status == status)
            count_query = count_query.where(ScheduleRoom.status == status)
        if store_id is not None:
            query = query.where(ScheduleRoom.store_id == store_id)
            count_query = count_query.where(ScheduleRoom.store_id == store_id)
        if department_id is not None:
            query = query.where(ScheduleRoom.department_id == department_id)
            count_query = count_query.where(ScheduleRoom.department_id == department_id)

        query = query.order_by(ScheduleRoom.created_at.desc()).offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)

        return list(result.scalars().all()), count_result.scalar() or 0

    async def create(self, data, operator_id: str | None = None) -> ScheduleRoom:
        tenant_id = self._tenant()

        room = ScheduleRoom(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            store_id=data.store_id,
            name=data.name,
            room_number=data.room_number,
            floor=data.floor,
            department_id=data.department_id or None,
            capacity=data.capacity,
            status=data.status,
            remark=data.remark,
        )
        set_create_audit(room, operator_id)
        self.db.add(room)
        await self.db.commit()
        await self.db.refresh(room)
        # 加载关联
        result = await self.db.execute(
            select(ScheduleRoom)
            .options(selectinload(ScheduleRoom.store), selectinload(ScheduleRoom.department))
            .where(ScheduleRoom.id == room.id)
        )
        return result.scalar_one()

    async def update(self, room_id: str, data, operator_id: str | None = None) -> ScheduleRoom | None:
        room = await self.get_by_id(room_id)
        if not room:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # 空字符串外键转 None
        for fk_field in ['department_id']:
            if fk_field in update_data and update_data[fk_field] == '':
                update_data[fk_field] = None

        for field, value in update_data.items():
            setattr(room, field, value)

        set_update_audit(room, operator_id)
        await self.db.commit()
        # 重新加载关联
        result = await self.db.execute(
            select(ScheduleRoom)
            .options(selectinload(ScheduleRoom.store), selectinload(ScheduleRoom.department))
            .where(ScheduleRoom.id == room_id)
        )
        return result.scalar_one()

    async def delete(self, room_id: str) -> bool:
        room = await self.get_by_id(room_id)
        if not room:
            return False

        # 检查是否有关联排班
        conditions = [Schedule.room_id == room_id]
        tenant_id = self._tenant()
        if tenant_id is not None:
            conditions.append(Schedule.tenant_id == tenant_id)
        result = await self.db.execute(
            select(func.count(Schedule.id)).where(and_(*conditions))
        )
        if result.scalar() > 0:
            raise ValueError("该诊室下存在排班记录，无法删除")

        await self.db.delete(room)
        await self.db.commit()
        return True
