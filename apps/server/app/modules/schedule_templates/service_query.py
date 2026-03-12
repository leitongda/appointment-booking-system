"""Read-oriented schedule template queries."""

from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.schedule_generation_log import ScheduleGenerationLog
from app.models.schedule_template import ScheduleTemplate


class ScheduleTemplateQueryMixin:
    async def get_by_id(self, template_id: str) -> Optional[ScheduleTemplate]:
        result = await self.db.execute(
            select(ScheduleTemplate)
            .options(
                selectinload(ScheduleTemplate.store),
                selectinload(ScheduleTemplate.doctor),
                selectinload(ScheduleTemplate.department),
            )
            .where(ScheduleTemplate.id == template_id)
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        store_id: Optional[str] = None,
        doctor_id: Optional[str] = None,
        department_id: Optional[str] = None,
        status: Optional[int] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[List[ScheduleTemplate], int]:
        query = select(ScheduleTemplate).options(
            selectinload(ScheduleTemplate.store),
            selectinload(ScheduleTemplate.doctor),
            selectinload(ScheduleTemplate.department),
        )
        count_query = select(func.count(ScheduleTemplate.id))

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
    ) -> tuple[List[ScheduleGenerationLog], int]:
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
