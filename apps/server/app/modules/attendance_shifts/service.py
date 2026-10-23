"""考勤班次管理服务"""

import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant_context import get_current_tenant_id
from app.models.attendance import AttendanceShift
from app.utils.audit import set_create_audit, set_update_audit


class AttendanceShiftService:
    """考勤班次服务

    Args:
        db: 数据库会话
        tenant_id: 管理员账号租户锚点（R1-11）。查询/写入以锚点强过滤；
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

    async def get_list(
        self,
        enabled: bool | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[AttendanceShift], int]:
        """获取考勤班次列表"""
        tenant_id = self._tenant()
        conditions = []
        if tenant_id:
            conditions.append(AttendanceShift.tenant_id == tenant_id)

        if enabled is not None:
            conditions.append(AttendanceShift.enabled == enabled)

        if keyword:
            conditions.append(
                (AttendanceShift.name.ilike(f"%{keyword}%"))
                | (AttendanceShift.code.ilike(f"%{keyword}%"))
            )

        count_query = select(func.count(AttendanceShift.id))
        query = select(AttendanceShift)
        if conditions:
            count_query = count_query.where(and_(*conditions))
            query = query.where(and_(*conditions))

        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one() or 0

        query = (
            query.order_by(AttendanceShift.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_by_id(self, shift_id: str) -> AttendanceShift | None:
        """获取考勤班次详情"""
        stmt = select(AttendanceShift).where(AttendanceShift.id == shift_id)
        tenant_id = self._tenant()
        if tenant_id:
            stmt = stmt.where(AttendanceShift.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> AttendanceShift | None:
        """根据代码获取考勤班次"""
        stmt = select(AttendanceShift).where(AttendanceShift.code == code)
        tenant_id = self._tenant()
        if tenant_id:
            stmt = stmt.where(AttendanceShift.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: dict, operator_id: str | None = None) -> AttendanceShift:
        """创建考勤班次

        Raises:
            ValueError: 代码已存在
        """
        tenant_id = self._tenant()

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
        stmt = select(AttendanceShift).where(AttendanceShift.enabled.is_(True))
        tenant_id = self._tenant()
        if tenant_id:
            stmt = stmt.where(AttendanceShift.tenant_id == tenant_id)
        result = await self.db.execute(stmt.order_by(AttendanceShift.code.asc()))
        return list(result.scalars().all())
