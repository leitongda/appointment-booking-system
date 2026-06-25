"""考勤班次管理服务"""

import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant_context import get_current_tenant_id
from app.models.attendance import AttendanceShift
from app.utils.audit import set_create_audit, set_update_audit


class AttendanceShiftService:
    """考勤班次服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        enabled: bool | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[AttendanceShift], int]:
        """获取考勤班次列表"""
        tenant_id = get_current_tenant_id()
        conditions = [AttendanceShift.tenant_id == tenant_id]

        if enabled is not None:
            conditions.append(AttendanceShift.enabled == enabled)

        if keyword:
            conditions.append(
                (AttendanceShift.name.ilike(f"%{keyword}%"))
                | (AttendanceShift.code.ilike(f"%{keyword}%"))
            )

        count_query = select(func.count(AttendanceShift.id)).where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one() or 0

        query = (
            select(AttendanceShift)
            .where(and_(*conditions))
            .order_by(AttendanceShift.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_by_id(self, shift_id: str) -> AttendanceShift | None:
        """获取考勤班次详情"""
        tenant_id = get_current_tenant_id()
        result = await self.db.execute(
            select(AttendanceShift).where(
                AttendanceShift.id == shift_id,
                AttendanceShift.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> AttendanceShift | None:
        """根据代码获取考勤班次"""
        tenant_id = get_current_tenant_id()
        result = await self.db.execute(
            select(AttendanceShift).where(
                AttendanceShift.code == code,
                AttendanceShift.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict, operator_id: str | None = None) -> AttendanceShift:
        """创建考勤班次

        Raises:
            ValueError: 代码已存在
        """
        tenant_id = get_current_tenant_id()

        existing = await self.get_by_code(data["code"])
        if existing:
            raise ValueError(f"班次代码 '{data['code']}' 已存在")

        shift = AttendanceShift(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            **data,
        )
        set_create_audit(shift, operator_id)

        self.db.add(shift)
        await self.db.commit()
        await self.db.refresh(shift)

        return shift

    async def update(self, shift_id: str, data: dict, operator_id: str | None = None) -> AttendanceShift | None:
        """更新考勤班次"""
        shift = await self.get_by_id(shift_id)
        if not shift:
            return None

        for key, value in data.items():
            if value is not None and hasattr(shift, key):
                setattr(shift, key, value)

        set_update_audit(shift, operator_id)

        await self.db.commit()
        await self.db.refresh(shift)

        return shift

    async def delete(self, shift_id: str) -> bool:
        """删除考勤班次"""
        shift = await self.get_by_id(shift_id)
        if not shift:
            return False

        await self.db.delete(shift)
        await self.db.commit()

        return True

    async def get_all_enabled(self) -> list[AttendanceShift]:
        """获取所有启用的考勤班次（用于下拉选择）"""
        tenant_id = get_current_tenant_id()
        result = await self.db.execute(
            select(AttendanceShift)
            .where(
                AttendanceShift.tenant_id == tenant_id,
                AttendanceShift.enabled == True,
            )
            .order_by(AttendanceShift.code.asc())
        )
        return list(result.scalars().all())
