"""考勤规则管理服务"""

import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant_context import get_current_tenant_id
from app.models.attendance import AttendanceRule
from app.utils.audit import set_create_audit, set_update_audit


class AttendanceRuleService:
    """考勤规则服务

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
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[AttendanceRule], int]:
        """获取考勤规则列表"""
        tenant_id = self._tenant()
        conditions = []
        if tenant_id:
            conditions.append(AttendanceRule.tenant_id == tenant_id)

        if keyword:
            conditions.append(AttendanceRule.name.ilike(f"%{keyword}%"))

        count_query = select(func.count(AttendanceRule.id))
        query = select(AttendanceRule)
        if conditions:
            count_query = count_query.where(and_(*conditions))
            query = query.where(and_(*conditions))

        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one() or 0

        query = (
            query.order_by(AttendanceRule.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_by_id(self, rule_id: str) -> AttendanceRule | None:
        """获取考勤规则详情"""
        stmt = select(AttendanceRule).where(AttendanceRule.id == rule_id)
        tenant_id = self._tenant()
        if tenant_id:
            stmt = stmt.where(AttendanceRule.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: dict, operator_id: str | None = None) -> AttendanceRule:
        """创建考勤规则"""
        tenant_id = self._tenant()

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
