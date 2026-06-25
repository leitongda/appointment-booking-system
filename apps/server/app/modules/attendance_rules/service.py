"""考勤规则管理服务"""

import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant_context import get_current_tenant_id
from app.models.attendance import AttendanceRule
from app.utils.audit import set_create_audit, set_update_audit


class AttendanceRuleService:
    """考勤规则服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[AttendanceRule], int]:
        """获取考勤规则列表"""
        tenant_id = get_current_tenant_id()
        conditions = [AttendanceRule.tenant_id == tenant_id]

        if keyword:
            conditions.append(AttendanceRule.name.ilike(f"%{keyword}%"))

        count_query = select(func.count(AttendanceRule.id)).where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one() or 0

        query = (
            select(AttendanceRule)
            .where(and_(*conditions))
            .order_by(AttendanceRule.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_by_id(self, rule_id: str) -> AttendanceRule | None:
        """获取考勤规则详情"""
        tenant_id = get_current_tenant_id()
        result = await self.db.execute(
            select(AttendanceRule).where(
                AttendanceRule.id == rule_id,
                AttendanceRule.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict, operator_id: str | None = None) -> AttendanceRule:
        """创建考勤规则"""
        tenant_id = get_current_tenant_id()

        rule = AttendanceRule(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            **data,
        )
        set_create_audit(rule, operator_id)

        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)

        return rule

    async def update(self, rule_id: str, data: dict, operator_id: str | None = None) -> AttendanceRule | None:
        """更新考勤规则"""
        rule = await self.get_by_id(rule_id)
        if not rule:
            return None

        for key, value in data.items():
            if value is not None and hasattr(rule, key):
                setattr(rule, key, value)

        set_update_audit(rule, operator_id)

        await self.db.commit()
        await self.db.refresh(rule)

        return rule

    async def delete(self, rule_id: str) -> bool:
        """删除考勤规则"""
        rule = await self.get_by_id(rule_id)
        if not rule:
            return False

        await self.db.delete(rule)
        await self.db.commit()

        return True
