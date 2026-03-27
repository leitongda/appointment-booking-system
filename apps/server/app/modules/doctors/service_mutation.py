"""Mutation helpers for doctors."""

import random
import string
import uuid
from typing import List, Optional

from pypinyin import lazy_pinyin
from sqlalchemy import select

from app.core.security import get_password_hash
from app.models.doctor import Doctor
from app.models.user import User
from app.schemas.doctor import DoctorCreate, DoctorUpdate
from app.utils.audit import set_create_audit, set_update_audit


class DoctorMutationMixin:
    async def create(self, data: DoctorCreate, operator_id: Optional[str] = None) -> Doctor:
        # 配额检查（获取当前租户ID）
        from app.common.quota import check_quota
        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()
        await check_quota(tenant_id, "doctors", self.db)

        user_id = None
        password = data.password or "123456"
        password_hash = get_password_hash(password)

        if data.phone:
            user = User(
                id=str(uuid.uuid4()),
                phone=data.phone,
                password_hash=password_hash,
                nickname=data.name,
                gender=data.gender,
                status=1,
            )
            set_create_audit(user, operator_id)
            self.db.add(user)
            await self.db.flush()
            user_id = user.id

        doctor = Doctor(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            store_id=data.store_id,
            department_id=data.department_id,
            name=data.name,
            username=data.username,
            phone=data.phone,
            password_hash=password_hash,
            gender=data.gender,
            avatar=data.avatar,
            banner=data.banner,
            title=data.title,
            years_of_experience=data.years_of_experience,
            education=data.education,
            graduate_school=data.graduate_school,
            license_number=data.license_number,
            license_image=data.license_image,
            honors=data.honors,
            schedule_desc=data.schedule_desc,
            max_daily_appointments=data.max_daily_appointments,
            online_consult_enabled=data.online_consult_enabled,
            online_consult_fee=data.online_consult_fee,
            page_style=data.page_style,
            promo_video=data.promo_video,
            tags=data.tags,
            specialty=data.specialty,
            introduction=data.introduction,
            is_recommended=data.is_recommended,
            sort_order=data.sort_order,
            status=data.status,
            use_fee_template=data.use_fee_template,
        )
        set_create_audit(doctor, operator_id)
        self.db.add(doctor)
        await self.db.commit()
        await self.db.refresh(doctor)
        return doctor

    async def update(
        self, doctor_id: str, data: DoctorUpdate, operator_id: Optional[str] = None
    ) -> Optional[Doctor]:
        doctor = await self.get_by_id(doctor_id)
        if not doctor:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if "password" in update_data and update_data["password"]:
            update_data["password_hash"] = get_password_hash(update_data["password"])
            del update_data["password"]

        for field, value in update_data.items():
            if hasattr(doctor, field):
                setattr(doctor, field, value)

        set_update_audit(doctor, operator_id)
        await self.db.commit()
        await self.db.refresh(doctor)
        return doctor

    async def delete(self, doctor_id: str) -> bool:
        doctor = await self.get_by_id(doctor_id)
        if not doctor:
            return False
        await self.db.delete(doctor)
        await self.db.commit()
        return True

    async def check_username_exists(self, username: str, exclude_id: Optional[str] = None) -> bool:
        from app.middleware.tenant_context import get_current_tenant_id
        query = select(Doctor).where(Doctor.username == username)
        tenant_id = get_current_tenant_id()
        if tenant_id:
            query = query.where(Doctor.tenant_id == tenant_id)
        if exclude_id:
            query = query.where(Doctor.id != exclude_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    def name_to_pinyin(self, name: str) -> str:
        return "".join(lazy_pinyin(name))

    async def generate_username(self, name: str) -> str:
        base_username = self.name_to_pinyin(name)
        username = base_username
        if await self.check_username_exists(username):
            for _ in range(10):
                suffix = "_" + "".join(random.choices(string.digits, k=3))
                username = base_username + suffix
                if not await self.check_username_exists(username):
                    break
        return username

    async def suggest_usernames(self, base_username: str, count: int = 3) -> List[str]:
        suggestions = []
        attempts = 0
        max_attempts = count * 5
        while len(suggestions) < count and attempts < max_attempts:
            suffix = "_" + "".join(random.choices(string.digits, k=3))
            candidate = base_username + suffix
            if not await self.check_username_exists(candidate) and candidate not in suggestions:
                suggestions.append(candidate)
            attempts += 1
        return suggestions

    async def batch_update_sort_order(self, items: List[dict]) -> int:
        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()
        count = 0
        for item in items:
            doctor_id = item.get("id")
            sort_order = item.get("sort_order")
            if doctor_id and sort_order is not None:
                query = select(Doctor).where(Doctor.id == doctor_id)
                if tenant_id:
                    query = query.where(Doctor.tenant_id == tenant_id)
                result = await self.db.execute(query)
                doctor = result.scalar_one_or_none()
                if doctor:
                    doctor.sort_order = sort_order
                    count += 1
        await self.db.commit()
        return count
