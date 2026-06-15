"""Read-oriented schedule template queries."""


from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from app.middleware.tenant_context import get_current_tenant_id
from app.models.schedule_generation_log import ScheduleGenerationLog
from app.models.schedule_template import ScheduleTemplate


class ScheduleTemplateQueryMixin:
    async def _get_template_with_tenant(self, template_id: str) -> ScheduleTemplate | None:
        """根据 ID 查询排班模板，同时过滤租户。"""
        conditions = [ScheduleTemplate.id == template_id]
        tenant_id = get_current_tenant_id()
        if tenant_id is not None:
            conditions.append(ScheduleTemplate.tenant_id == tenant_id)

        result = await self.db.execute(
            select(ScheduleTemplate)
            .options(
                selectinload(ScheduleTemplate.store),
                selectinload(ScheduleTemplate.doctor),
                selectinload(ScheduleTemplate.department),
                selectinload(ScheduleTemplate.shift_type),
            )
            .where(and_(*conditions))
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, template_id: str) -> ScheduleTemplate | None:
        return await self._get_template_with_tenant(template_id)

    async def get_list(
        self,
        store_id: str | None = None,
        doctor_id: str | None = None,
        department_id: str | None = None,
        status: int | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[ScheduleTemplate], int]:
        query = select(ScheduleTemplate).options(
            selectinload(ScheduleTemplate.store),
            selectinload(ScheduleTemplate.doctor),
            selectinload(ScheduleTemplate.department),
            selectinload(ScheduleTemplate.shift_type),
        )
        count_query = select(func.count(ScheduleTemplate.id))

        # 租户隔离
        tenant_id = get_current_tenant_id()
        if tenant_id is not None:
            query = query.where(ScheduleTemplate.tenant_id == tenant_id)
            count_query = count_query.where(ScheduleTemplate.tenant_id == tenant_id)

        if store_id:
            query = query.where(ScheduleTemplate.store_id == store_id)
            count_query = count_query.where(ScheduleTemplate.store_id == store_id)
        if doctor_id:
            query = query.where(ScheduleTemplate.doctor_id == doctor_id)
            count_query = count_query.where(ScheduleTemplate.doctor_id == doctor_id)
        if department_id:
            query = query.where(ScheduleTemplate.department_id == department_id)
            count_query = count_query.where(ScheduleTemplate.department_id == department_id)
        if status is not None:
            query = query.where(ScheduleTemplate.status == status)
            count_query = count_query.where(ScheduleTemplate.status == status)

        query = (
            query.order_by(ScheduleTemplate.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)
        return list(result.scalars().all()), count_result.scalar() or 0

    async def get_generation_logs(
        self,
        template_id: str,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[ScheduleGenerationLog], int]:
        # 先验证模板属于当前租户
        template = await self._get_template_with_tenant(template_id)
        if not template:
            return [], 0

        query = select(ScheduleGenerationLog).where(
            ScheduleGenerationLog.template_id == template_id
        ).order_by(ScheduleGenerationLog.created_at.desc())

        count_query = select(func.count(ScheduleGenerationLog.id)).where(
            ScheduleGenerationLog.template_id == template_id
        )

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)
        return list(result.scalars().all()), count_result.scalar() or 0
