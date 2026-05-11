"""Patient card management services for admin usage."""

import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_password_hash
from app.core.config import settings
from app.models.appointment import Appointment
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.models.store import Store
from app.models.user import Patient, User
from app.common.account_sync import AccountSyncService
from app.modules.patients.common import PatientsServiceBase
from app.modules.appointments.common import APPOINTMENT_STATUS
from app.schemas.user import FamilyMemberCreate, PatientCreateByAdmin, PatientUpdate
from app.utils.audit import set_create_audit, set_update_audit


class PatientManageService(PatientsServiceBase):
    async def get_list(
        self,
        keyword: Optional[str] = None,
        is_blacklist: Optional[bool] = None,
        store_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[dict], int]:
        tenant_id = self._current_tenant_id()
        query = select(Patient).options(selectinload(Patient.user))
        conditions = []
        if tenant_id:
            conditions.append(Patient.tenant_id == tenant_id)
        if keyword:
            conditions.append(
                or_(
                    Patient.name.ilike(f"%{keyword}%"),
                    Patient.phone.ilike(f"%{keyword}%"),
                    Patient.id_card.ilike(f"%{keyword}%"),
                    Patient.card_no.ilike(f"%{keyword}%"),
                )
            )
        if store_id:
            conditions.append(or_(Patient.store_id == store_id, Patient.store_id.is_(None)))
        if conditions:
            query = query.where(and_(*conditions))

        count_query = select(func.count(Patient.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = await self.db.scalar(count_query)

        query = query.order_by(Patient.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        patients = result.unique().scalars().all()

        if not patients:
            return [], total or 0

        patient_ids = [p.id for p in patients]

        # 批量获取 appointmentCount
        appt_count_subq = (
            select(Appointment.patient_id, func.count(Appointment.id).label("cnt"))
            .where(Appointment.patient_id.in_(patient_ids))
            .group_by(Appointment.patient_id)
        )
        if tenant_id:
            appt_count_subq = appt_count_subq.where(Appointment.tenant_id == tenant_id)
        appt_result = await self.db.execute(appt_count_subq)
        appt_count_map = dict(appt_result.all())

        # 批量获取 noShowCount
        noshow_count_subq = (
            select(Appointment.patient_id, func.count(Appointment.id).label("cnt"))
            .where(
                and_(
                    Appointment.patient_id.in_(patient_ids),
                    Appointment.status == APPOINTMENT_STATUS["NO_SHOW"],
                )
            )
            .group_by(Appointment.patient_id)
        )
        if tenant_id:
            noshow_count_subq = noshow_count_subq.where(Appointment.tenant_id == tenant_id)
        noshow_result = await self.db.execute(noshow_count_subq)
        noshow_count_map = dict(noshow_result.all())

        patient_data = []
        for patient in patients:
            user = patient.user
            is_in_blacklist = user.status == 0 if user else False
            if is_blacklist is not None:
                if is_blacklist and not is_in_blacklist:
                    continue
                if not is_blacklist and is_in_blacklist:
                    continue
            patient_data.append(
                {
                    "id": patient.id,
                    "userId": patient.user_id,
                    "cardNo": patient.card_no,
                    "name": patient.name,
                    "phone": patient.phone,
                    "idCard": patient.id_card,
                    "gender": patient.gender,
                    "age": patient.age,
                    "birthday": patient.birthday.isoformat() if patient.birthday else None,
                    "relationship": patient.relationship,
                    "isDefault": patient.is_default,
                    "source": patient.source or 1,
                    "appointmentCount": appt_count_map.get(patient.id, 0),
                    "noShowCount": noshow_count_map.get(patient.id, 0),
                    "isBlacklist": is_in_blacklist,
                    "createdAt": patient.created_at.isoformat() if patient.created_at else None,
                    "idCardType": patient.id_card_type or 1,
                    "ethnicity": patient.ethnicity or "汉族",
                    "province": patient.province,
                    "city": patient.city,
                    "district": patient.district,
                    "street": patient.street,
                    "address": patient.address,
                    "userPhone": user.phone if user else None,
                    "userNickname": user.nickname if user else None,
                }
            )

        return patient_data, total or 0

    async def get_patient_store_id(self, patient_id: str) -> Optional[str]:
        query = select(Patient.store_id).where(Patient.id == patient_id)
        tenant_id = self._current_tenant_id()
        if tenant_id:
            query = query.where(Patient.tenant_id == tenant_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_detail(self, patient_id: str) -> Optional[dict]:
        tenant_id = self._current_tenant_id()
        query = select(Patient).options(selectinload(Patient.user)).where(Patient.id == patient_id)
        if tenant_id:
            query = query.where(Patient.tenant_id == tenant_id)
        result = await self.db.execute(query)
        patient = result.unique().scalar_one_or_none()
        if not patient:
            return None

        user = patient.user
        appointment_count_query = select(func.count(Appointment.id)).where(Appointment.patient_id == patient_id)
        no_show_count_query = select(func.count(Appointment.id)).where(and_(Appointment.patient_id == patient_id, Appointment.status == APPOINTMENT_STATUS["NO_SHOW"]))
        completed_count_query = select(func.count(Appointment.id)).where(and_(Appointment.patient_id == patient_id, Appointment.status == 5))
        if tenant_id:
            appointment_count_query = appointment_count_query.where(Appointment.tenant_id == tenant_id)
            no_show_count_query = no_show_count_query.where(Appointment.tenant_id == tenant_id)
            completed_count_query = completed_count_query.where(Appointment.tenant_id == tenant_id)
        appointment_count = await self.db.scalar(appointment_count_query)
        no_show_count = await self.db.scalar(no_show_count_query)
        completed_count = await self.db.scalar(completed_count_query)

        last_appointment_query = (
            select(Appointment)
            .where(and_(Appointment.patient_id == patient_id, Appointment.status == 5))
            .order_by(Appointment.complete_time.desc())
            .limit(1)
        )
        if tenant_id:
            last_appointment_query = last_appointment_query.where(Appointment.tenant_id == tenant_id)
        last_appointment = await self.db.execute(last_appointment_query)
        last_appt = last_appointment.scalar_one_or_none()
        last_visit_date = last_appt.complete_time.isoformat() if last_appt and last_appt.complete_time else None

        family_query = select(Patient).where(Patient.user_id == patient.user_id)
        if tenant_id:
            family_query = family_query.where(Patient.tenant_id == tenant_id)
        family_result = await self.db.execute(
            family_query.order_by(Patient.is_default.desc(), Patient.created_at.asc())
        )
        family_members = family_result.scalars().all()

        # 批量获取家庭成员的预约统计
        member_ids = [m.id for m in family_members]
        if member_ids:
            member_appt_subq = (
                select(Appointment.patient_id, func.count(Appointment.id).label("cnt"))
                .where(Appointment.patient_id.in_(member_ids))
                .group_by(Appointment.patient_id)
            )
            if tenant_id:
                member_appt_subq = member_appt_subq.where(Appointment.tenant_id == tenant_id)
            member_appt_result = await self.db.execute(member_appt_subq)
            member_appt_map = dict(member_appt_result.all())

            member_noshow_subq = (
                select(Appointment.patient_id, func.count(Appointment.id).label("cnt"))
                .where(
                    and_(
                        Appointment.patient_id.in_(member_ids),
                        Appointment.status == APPOINTMENT_STATUS["NO_SHOW"],
                    )
                )
                .group_by(Appointment.patient_id)
            )
            if tenant_id:
                member_noshow_subq = member_noshow_subq.where(Appointment.tenant_id == tenant_id)
            member_noshow_result = await self.db.execute(member_noshow_subq)
            member_noshow_map = dict(member_noshow_result.all())
        else:
            member_appt_map = {}
            member_noshow_map = {}

        family_data = [
            {
                "id": member.id,
                "userId": member.user_id,
                "cardNo": member.card_no,
                "name": member.name,
                "phone": member.phone,
                "idCard": member.id_card,
                "gender": member.gender,
                "birthday": member.birthday.isoformat() if member.birthday else None,
                "relationship": member.relationship,
                "isDefault": member.is_default,
                "appointmentCount": member_appt_map.get(member.id, 0),
                "noShowCount": member_noshow_map.get(member.id, 0),
                "totalConsumption": float(member.total_consumption or 0),
                "isBlacklist": user.status == 0 if user else False,
                "createdAt": member.created_at.isoformat() if member.created_at else None,
            }
            for member in family_members
        ]

        return {
            "id": patient.id,
            "userId": patient.user_id,
            "cardNo": patient.card_no,
            "name": patient.name,
            "phone": patient.phone,
            "gender": patient.gender,
            "province": patient.province,
            "city": patient.city,
            "district": patient.district,
            "street": patient.street,
            "idCardType": patient.id_card_type or 1,
            "idCard": patient.id_card,
            "ethnicity": patient.ethnicity or "汉族",
            "birthday": patient.birthday.isoformat() if patient.birthday else None,
            "age": self._calculate_age(patient.birthday),
            "relationship": patient.relationship,
            "address": patient.address,
            "source": patient.source or 1,
            "totalConsumption": float(patient.total_consumption or 0),
            "lastVisitDate": last_visit_date,
            "isBlacklist": user.status == 0 if user else False,
            "createdAt": patient.created_at.isoformat() if patient.created_at else None,
            "nickname": user.nickname if user else None,
            "points": user.points if user else 0,
            "statistics": {
                "appointmentCount": appointment_count or 0,
                "completedCount": completed_count or 0,
                "noShowCount": no_show_count or 0,
            },
            "familyMembers": family_data,
        }

    async def update_patient(self, patient_id: str, data: PatientUpdate, operator_id: Optional[str] = None) -> Optional[dict]:
        query = select(Patient).where(Patient.id == patient_id)
        tenant_id = self._current_tenant_id()
        if tenant_id:
            query = query.where(Patient.tenant_id == tenant_id)
        result = await self.db.execute(query)
        patient = result.scalar_one_or_none()
        if not patient:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(patient, key):
                setattr(patient, key, value)
        set_update_audit(patient, operator_id)
        await self.db.commit()
        await self.db.refresh(patient)
        return await self.get_detail(patient_id)

    async def get_appointments(
        self,
        patient_id: str,
        doctor_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status: Optional[int] = None,
        is_admin_booked: Optional[bool] = None,
        is_follow_up: Optional[bool] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[dict], int]:
        tenant_id = self._current_tenant_id()
        query = select(Appointment).where(Appointment.patient_id == patient_id)
        conditions = [Appointment.patient_id == patient_id]
        if tenant_id:
            conditions.append(Appointment.tenant_id == tenant_id)
        if doctor_id:
            conditions.append(Appointment.doctor_id == doctor_id)
        if status is not None:
            conditions.append(Appointment.status == status)
        if start_date or end_date:
            query = query.join(Schedule, Appointment.schedule_id == Schedule.id)
            if start_date:
                conditions.append(Schedule.schedule_date >= start_date)
            if end_date:
                conditions.append(Schedule.schedule_date <= end_date)
        query = query.where(and_(*conditions))

        count_conditions = conditions.copy()
        count_query = select(func.count(Appointment.id)).join(Schedule, Appointment.schedule_id == Schedule.id) if (start_date or end_date) else select(func.count(Appointment.id))
        count_query = count_query.where(and_(*count_conditions))
        total = await self.db.scalar(count_query)

        query = query.order_by(Appointment.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        appointments = result.scalars().all()

        appointment_data = []
        for appt in appointments:
            schedule = await self.db.get(Schedule, appt.schedule_id) if appt.schedule_id else None
            doctor = await self.db.get(Doctor, appt.doctor_id) if appt.doctor_id else None
            department = await self.db.get(Department, doctor.department_id) if doctor and doctor.department_id else None
            store = await self.db.get(Store, doctor.store_id) if doctor and doctor.store_id else None
            appointment_data.append(
                {
                    "id": appt.id,
                    "appointmentNo": appt.appointment_no,
                    "storeName": store.name if store else None,
                    "departmentName": department.name if department else None,
                    "doctorId": appt.doctor_id,
                    "doctorName": doctor.name if doctor else None,
                    "scheduleDate": schedule.schedule_date.isoformat() if schedule and schedule.schedule_date else None,
                    "startTime": str(schedule.start_time) if schedule and schedule.start_time else None,
                    "endTime": str(schedule.end_time) if schedule and schedule.end_time else None,
                    "queueNumber": appt.queue_number,
                    "status": appt.status,
                    "isAdminBooked": False,
                    "isFollowUp": False,
                    "createdAt": appt.created_at.isoformat() if appt.created_at else None,
                }
            )
        return appointment_data, total or 0

    async def get_consumption_records(
        self,
        patient_id: str,
        item_name: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[dict], int]:
        tenant_id = self._current_tenant_id()
        conditions = [Appointment.patient_id == patient_id, Appointment.status == 5]
        if tenant_id:
            conditions.append(Appointment.tenant_id == tenant_id)
        query = select(Appointment).where(and_(*conditions))
        count_query = select(func.count(Appointment.id)).where(and_(*conditions))
        total = await self.db.scalar(count_query)
        query = query.order_by(Appointment.complete_time.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        appointments = result.scalars().all()

        records = []
        for appt in appointments:
            schedule = await self.db.get(Schedule, appt.schedule_id) if appt.schedule_id else None
            doctor = await self.db.get(Doctor, appt.doctor_id) if appt.doctor_id else None
            store = await self.db.get(Store, doctor.store_id) if doctor and doctor.store_id else None
            records.append(
                {
                    "id": appt.id,
                    "orderNo": appt.appointment_no,
                    "storeName": store.name if store else None,
                    "itemName": f"{doctor.name if doctor else ''}诊疗" if doctor else "诊疗服务",
                    "scheduleDate": schedule.schedule_date.isoformat() if schedule and schedule.schedule_date else None,
                    "startTime": str(schedule.start_time) if schedule and schedule.start_time else None,
                    "endTime": str(schedule.end_time) if schedule and schedule.end_time else None,
                    "status": appt.status,
                    "createdAt": appt.created_at.isoformat() if appt.created_at else None,
                }
            )
        return records, total or 0

    async def add_to_blacklist(self, patient_id: str, reason: str = None) -> bool:
        tenant_id = self._current_tenant_id()
        query = select(Patient).options(selectinload(Patient.user)).where(Patient.id == patient_id)
        if tenant_id:
            query = query.where(Patient.tenant_id == tenant_id)
        result = await self.db.execute(query)
        patient = result.unique().scalar_one_or_none()
        if not patient or not patient.user:
            return False
        patient.user.status = 0
        await self.db.commit()
        return True

    async def remove_from_blacklist(self, patient_id: str) -> bool:
        tenant_id = self._current_tenant_id()
        query = select(Patient).options(selectinload(Patient.user)).where(Patient.id == patient_id)
        if tenant_id:
            query = query.where(Patient.tenant_id == tenant_id)
        result = await self.db.execute(query)
        patient = result.unique().scalar_one_or_none()
        if not patient or not patient.user:
            return False
        patient.user.status = 1
        await self.db.commit()
        return True

    async def get_blacklist(
        self,
        store_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[dict], int]:
        tenant_id = self._current_tenant_id()
        conditions = [User.status == 0]
        if tenant_id:
            conditions.append(Patient.tenant_id == tenant_id)
        if store_id:
            conditions.append(or_(Patient.store_id == store_id, Patient.store_id.is_(None)))
        query = select(Patient).join(User).where(and_(*conditions))
        count_query = select(func.count(Patient.id)).join(User).where(and_(*conditions))
        total = await self.db.scalar(count_query)
        query = query.order_by(Patient.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        patients = result.scalars().all()

        patient_data = []
        for patient in patients:
            no_show_count_query = select(func.count(Appointment.id)).where(
                and_(Appointment.patient_id == patient.id, Appointment.status == APPOINTMENT_STATUS["NO_SHOW"])
            )
            if tenant_id:
                no_show_count_query = no_show_count_query.where(Appointment.tenant_id == tenant_id)
            no_show_count = await self.db.scalar(no_show_count_query)
            patient_data.append(
                {
                    "id": patient.id,
                    "name": patient.name,
                    "phone": patient.phone,
                    "idCard": patient.id_card,
                    "noShowCount": no_show_count or 0,
                    "createdAt": patient.created_at.isoformat() if patient.created_at else None,
                }
            )
        return patient_data, total or 0

    async def create_patient(
        self,
        data: PatientCreateByAdmin,
        store_id: Optional[str] = None,
        operator_id: Optional[str] = None,
    ) -> dict:
        tenant_id = self._current_tenant_id()
        user_query = select(User).where(User.phone == data.phone)
        if tenant_id:
            user_query = user_query.where(User.tenant_id == tenant_id)
        result = await self.db.execute(user_query)
        user = result.scalar_one_or_none()
        if user:
            existing_patient_query = select(Patient).where(and_(Patient.user_id == user.id, Patient.name == data.name))
            if tenant_id:
                existing_patient_query = existing_patient_query.where(Patient.tenant_id == tenant_id)
            existing_patient = await self.db.execute(existing_patient_query)
            if existing_patient.scalar_one_or_none():
                raise ValueError(f"该用户下已存在名为 {data.name} 的就诊人")
        else:
            user = User(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                phone=data.phone,
                password_hash=get_password_hash(settings.DEFAULT_USER_PASSWORD),
                nickname=data.name,
                status=1,
            )
            set_create_audit(user, operator_id)
            self.db.add(user)
            await self.db.flush()

            # 双写同步: 后台代建患者账号同步到 accounts
            await AccountSyncService.sync_user_to_account(
                self.db, user.id, operator_id=operator_id
            )

        birthday = None
        if data.birthday:
            try:
                birthday = datetime.strptime(data.birthday, "%Y-%m-%d")
            except ValueError:
                pass

        patient = Patient(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id or user.tenant_id,
            user_id=user.id,
            store_id=store_id,
            name=data.name,
            phone=data.phone,
            id_card=data.id_card,
            gender=data.gender,
            birthday=birthday,
            relationship=data.relationship or "本人",
            is_default=data.is_default,
            card_no=self._generate_card_no(),
            province=data.province,
            city=data.city,
            district=data.district,
            street=data.street,
            id_card_type=data.id_card_type,
            ethnicity=data.ethnicity,
            address=data.address,
            source=2,
        )
        set_create_audit(patient, operator_id)
        self.db.add(patient)
        await self.db.commit()
        return await self.get_detail(patient.id)

    async def add_family_member(self, patient_id: str, data: FamilyMemberCreate, operator_id: Optional[str] = None) -> Optional[dict]:
        tenant_id = self._current_tenant_id()
        patient_query = select(Patient).where(Patient.id == patient_id)
        if tenant_id:
            patient_query = patient_query.where(Patient.tenant_id == tenant_id)
        result = await self.db.execute(patient_query)
        patient = result.scalar_one_or_none()
        if not patient:
            return None

        existing_query = select(Patient).where(and_(Patient.user_id == patient.user_id, Patient.name == data.name))
        if tenant_id:
            existing_query = existing_query.where(Patient.tenant_id == tenant_id)
        existing = await self.db.execute(existing_query)
        if existing.scalar_one_or_none():
            raise ValueError(f"该用户下已存在名为 {data.name} 的就诊人")

        birthday = None
        if data.birthday:
            try:
                birthday = datetime.strptime(data.birthday, "%Y-%m-%d")
            except ValueError:
                pass

        member = Patient(
            id=str(uuid.uuid4()),
            tenant_id=patient.tenant_id,
            user_id=patient.user_id,
            store_id=patient.store_id,
            name=data.name,
            phone=data.phone,
            id_card=data.id_card,
            gender=data.gender,
            birthday=birthday,
            relationship=data.relationship,
            is_default=data.is_default,
            card_no=self._generate_card_no(),
            province=data.province,
            city=data.city,
            district=data.district,
            street=data.street,
            id_card_type=data.id_card_type,
            ethnicity=data.ethnicity,
            address=data.address,
            source=2,
        )
        set_create_audit(member, operator_id)

        if data.is_default:
            from sqlalchemy import update

            update_stmt = update(Patient).where(Patient.user_id == patient.user_id)
            if tenant_id:
                update_stmt = update_stmt.where(Patient.tenant_id == tenant_id)
            await self.db.execute(update_stmt.values(is_default=False))

        self.db.add(member)
        await self.db.commit()
        return {
            "id": member.id,
            "userId": member.user_id,
            "cardNo": member.card_no,
            "name": member.name,
            "phone": member.phone,
            "idCard": member.id_card,
            "gender": member.gender,
            "birthday": member.birthday.isoformat() if member.birthday else None,
            "relationship": member.relationship,
            "isDefault": member.is_default,
            "appointmentCount": 0,
            "noShowCount": 0,
            "isBlacklist": False,
            "createdAt": member.created_at.isoformat() if member.created_at else None,
        }

    async def update_family_member(
        self,
        patient_id: str,
        member_id: str,
        data: PatientUpdate,
        operator_id: Optional[str] = None,
    ) -> Optional[dict]:
        tenant_id = self._current_tenant_id()
        patient_query = select(Patient).where(Patient.id == patient_id)
        if tenant_id:
            patient_query = patient_query.where(Patient.tenant_id == tenant_id)
        result = await self.db.execute(patient_query)
        patient = result.scalar_one_or_none()
        if not patient:
            return None

        member_query = select(Patient).where(and_(Patient.id == member_id, Patient.user_id == patient.user_id))
        if tenant_id:
            member_query = member_query.where(Patient.tenant_id == tenant_id)
        result = await self.db.execute(member_query)
        member = result.scalar_one_or_none()
        if not member:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(member, key):
                setattr(member, key, value)

        set_update_audit(member, operator_id)
        await self.db.commit()
        await self.db.refresh(member)
        return {
            "id": member.id,
            "userId": member.user_id,
            "cardNo": member.card_no,
            "name": member.name,
            "phone": member.phone,
            "idCard": member.id_card,
            "gender": member.gender,
            "birthday": member.birthday.isoformat() if member.birthday else None,
            "relationship": member.relationship,
            "isDefault": member.is_default,
            "createdAt": member.created_at.isoformat() if member.created_at else None,
        }

    async def delete_family_member(self, patient_id: str, member_id: str) -> bool:
        tenant_id = self._current_tenant_id()
        patient_query = select(Patient).where(Patient.id == patient_id)
        if tenant_id:
            patient_query = patient_query.where(Patient.tenant_id == tenant_id)
        result = await self.db.execute(patient_query)
        patient = result.scalar_one_or_none()
        if not patient or patient_id == member_id:
            return False

        member_query = select(Patient).where(and_(Patient.id == member_id, Patient.user_id == patient.user_id))
        if tenant_id:
            member_query = member_query.where(Patient.tenant_id == tenant_id)
        result = await self.db.execute(member_query)
        member = result.scalar_one_or_none()
        if not member:
            return False

        appt_count_query = select(func.count(Appointment.id)).where(Appointment.patient_id == member_id)
        if tenant_id:
            appt_count_query = appt_count_query.where(Appointment.tenant_id == tenant_id)
        appt_count = await self.db.scalar(appt_count_query)
        if appt_count and appt_count > 0:
            raise ValueError("该就诊人有预约记录，无法删除")

        await self.db.delete(member)
        await self.db.commit()
        return True

    async def delete_patient(self, patient_id: str) -> bool:
        tenant_id = self._current_tenant_id()
        patient_query = select(Patient).options(selectinload(Patient.user)).where(Patient.id == patient_id)
        if tenant_id:
            patient_query = patient_query.where(Patient.tenant_id == tenant_id)
        result = await self.db.execute(patient_query)
        patient = result.unique().scalar_one_or_none()
        if not patient:
            return False

        appt_count_query = select(func.count(Appointment.id)).where(Appointment.patient_id == patient_id)
        if tenant_id:
            appt_count_query = appt_count_query.where(Appointment.tenant_id == tenant_id)
        appt_count = await self.db.scalar(appt_count_query)
        if appt_count and appt_count > 0:
            raise ValueError("该就诊卡有预约记录，无法删除")

        user_id = patient.user_id
        card_count_query = select(func.count(Patient.id)).where(Patient.user_id == user_id)
        if tenant_id:
            card_count_query = card_count_query.where(Patient.tenant_id == tenant_id)
        card_count = await self.db.scalar(card_count_query)
        if card_count and card_count <= 1:
            raise ValueError("用户至少需要保留一张就诊卡")

        if patient.is_default:
            other_card_query = select(Patient).where(and_(Patient.user_id == user_id, Patient.id != patient_id))
            if tenant_id:
                other_card_query = other_card_query.where(Patient.tenant_id == tenant_id)
            other_card = await self.db.execute(other_card_query.limit(1))
            other = other_card.scalar_one_or_none()
            if other:
                other.is_default = True

        await self.db.delete(patient)
        await self.db.commit()
        return True
