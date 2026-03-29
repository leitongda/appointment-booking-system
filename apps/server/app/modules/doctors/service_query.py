"""Read and auth helpers for doctors."""

from datetime import date, timedelta
from typing import Dict, List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from app.core.security import verify_password
from app.middleware.tenant_context import get_current_tenant_id
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.rest_day import RestDay
from app.models.schedule import Schedule


class DoctorQueryMixin:
    async def get_by_phone(self, phone: str) -> Optional[Doctor]:
        query = (
            select(Doctor)
            .options(selectinload(Doctor.department), selectinload(Doctor.store))
            .where(Doctor.phone == phone, Doctor.deleted_at.is_(None))
        )
        tenant_id = get_current_tenant_id()
        if tenant_id:
            query = query.where(Doctor.tenant_id == tenant_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[Doctor]:
        query = (
            select(Doctor)
            .options(selectinload(Doctor.department), selectinload(Doctor.store))
            .where(Doctor.username == username, Doctor.deleted_at.is_(None))
        )
        tenant_id = get_current_tenant_id()
        if tenant_id:
            query = query.where(Doctor.tenant_id == tenant_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def authenticate(self, phone: str, password: str) -> Optional[Doctor]:
        doctor = await self.get_by_phone(phone)
        if not doctor:
            doctor = await self.get_by_username(phone)
        if not doctor or not doctor.password_hash:
            return None
        if not verify_password(password, doctor.password_hash):
            return None
        return doctor

    async def update_login_info(self, doctor_id: str, ip: str) -> None:
        query = select(Doctor).where(Doctor.id == doctor_id, Doctor.deleted_at.is_(None))
        tenant_id = get_current_tenant_id()
        if tenant_id:
            query = query.where(Doctor.tenant_id == tenant_id)
        result = await self.db.execute(query)
        doctor = result.scalar_one_or_none()
        if doctor:
            from datetime import datetime

            doctor.last_login_at = datetime.now()
            doctor.last_login_ip = ip
            await self.db.commit()

    async def get_by_id(self, doctor_id: str) -> Optional[Doctor]:
        query = (
            select(Doctor)
            .options(selectinload(Doctor.department), selectinload(Doctor.store))
            .where(Doctor.id == doctor_id, Doctor.deleted_at.is_(None))
        )
        tenant_id = get_current_tenant_id()
        if tenant_id:
            query = query.where(Doctor.tenant_id == tenant_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_list(
        self,
        name: Optional[str] = None,
        store_id: Optional[str] = None,
        department_id: Optional[str] = None,
        status: Optional[int] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[List[Doctor], int]:
        tenant_id = get_current_tenant_id()
        query = select(Doctor).options(selectinload(Doctor.department), selectinload(Doctor.store))
        count_query = select(func.count(Doctor.id))

        # 软删除过滤
        query = query.where(Doctor.deleted_at.is_(None))
        count_query = count_query.where(Doctor.deleted_at.is_(None))

        if tenant_id:
            query = query.where(Doctor.tenant_id == tenant_id)
            count_query = count_query.where(Doctor.tenant_id == tenant_id)

        if name:
            query = query.where(Doctor.name.contains(name))
            count_query = count_query.where(Doctor.name.contains(name))
        if store_id:
            query = query.where(Doctor.store_id == store_id)
            count_query = count_query.where(Doctor.store_id == store_id)
        if department_id:
            query = query.where(Doctor.department_id == department_id)
            count_query = count_query.where(Doctor.department_id == department_id)
        if status is not None:
            query = query.where(Doctor.status == status)
            count_query = count_query.where(Doctor.status == status)

        query = query.order_by(Doctor.sort_order.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)
        return list(result.scalars().all()), count_result.scalar() or 0

    async def get_recommended(self, limit: int = 6, store_id: Optional[str] = None) -> List[Doctor]:
        tenant_id = get_current_tenant_id()
        query = (
            select(Doctor)
            .options(selectinload(Doctor.department), selectinload(Doctor.store))
            .where(Doctor.is_recommended == 1, Doctor.status == 1, Doctor.deleted_at.is_(None))
        )
        if tenant_id:
            query = query.where(Doctor.tenant_id == tenant_id)
        if store_id:
            query = query.where(Doctor.store_id == store_id)
        query = query.order_by(Doctor.sort_order.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_department(
        self, department_id: str, store_id: Optional[str] = None
    ) -> List[Doctor]:
        tenant_id = get_current_tenant_id()
        query = (
            select(Doctor)
            .options(selectinload(Doctor.department), selectinload(Doctor.store))
            .where(Doctor.department_id == department_id, Doctor.status == 1, Doctor.deleted_at.is_(None))
        )
        if tenant_id:
            query = query.where(Doctor.tenant_id == tenant_id)
        if store_id:
            query = query.where(Doctor.store_id == store_id)
        query = query.order_by(Doctor.sort_order.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_all_active(self, store_id: Optional[str] = None) -> List[Doctor]:
        tenant_id = get_current_tenant_id()
        query = select(Doctor).options(
            selectinload(Doctor.department), selectinload(Doctor.store)
        ).where(Doctor.status == 1, Doctor.deleted_at.is_(None))
        if tenant_id:
            query = query.where(Doctor.tenant_id == tenant_id)
        if store_id:
            query = query.where(Doctor.store_id == store_id)
        query = query.order_by(Doctor.sort_order.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_doctors_availability(self, doctor_ids: List[str], days: int = 7) -> Dict[str, bool]:
        if not doctor_ids:
            return {}

        tenant_id = get_current_tenant_id()
        today = date.today()
        end_date = today + timedelta(days=days)
        schedules_query = select(
            Schedule.doctor_id, Schedule.schedule_date, Schedule.store_id, Schedule.template_id
        ).where(
            and_(
                Schedule.doctor_id.in_(doctor_ids),
                Schedule.schedule_date >= today,
                Schedule.schedule_date <= end_date,
                Schedule.status == 1,
                Schedule.booked_slots < Schedule.total_slots,
            )
        )
        if tenant_id:
            schedules_query = schedules_query.where(Schedule.tenant_id == tenant_id)
        schedules_result = await self.db.execute(schedules_query)
        schedules = schedules_result.all()

        rest_days_result = await self.db.execute(
            select(RestDay).where(
                and_(RestDay.status == 1, RestDay.start_date <= end_date, RestDay.end_date >= today)
            )
        )
        rest_days = rest_days_result.scalars().all()

        availability = {doctor_id: False for doctor_id in doctor_ids}
        for schedule in schedules:
            if schedule.template_id is None:
                availability[schedule.doctor_id] = True
                continue

            is_rest_day = False
            for rest_day in rest_days:
                if not (rest_day.start_date <= schedule.schedule_date <= rest_day.end_date):
                    continue
                if schedule.store_id and rest_day.store_id != schedule.store_id:
                    continue
                if rest_day.doctor_ids is None:
                    is_rest_day = True
                    break
                import json

                try:
                    if schedule.doctor_id in json.loads(rest_day.doctor_ids):
                        is_rest_day = True
                        break
                except Exception:
                    continue

            if not is_rest_day:
                availability[schedule.doctor_id] = True

        return availability
