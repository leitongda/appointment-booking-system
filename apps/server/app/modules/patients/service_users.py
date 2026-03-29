"""User-level patient management services for admin usage."""

import uuid
from datetime import datetime
from typing import Optional, Tuple, List

from sqlalchemy import and_, func, or_, select, case

from app.models.appointment import Appointment
from app.models.user import Patient, User
from app.modules.patients.common import PatientsServiceBase
from app.modules.appointments.common import APPOINTMENT_STATUS
from app.utils.audit import set_create_audit, set_update_audit


class UserManageService(PatientsServiceBase):
    async def get_list(
        self,
        keyword: Optional[str] = None,
        status: Optional[int] = None,
        store_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[dict], int]:
        tenant_id = self._current_tenant_id()
        query = select(User)
        conditions = []
        if tenant_id:
            conditions.append(User.tenant_id == tenant_id)
        if keyword:
            conditions.append(or_(User.phone.ilike(f"%{keyword}%"), User.nickname.ilike(f"%{keyword}%")))
        if status is not None:
            conditions.append(User.status == status)
        if store_id:
            users_with_cards_in_store = select(Patient.user_id).where(or_(Patient.store_id == store_id, Patient.store_id.is_(None))).distinct()
            all_users_with_cards = select(Patient.user_id).distinct()
            conditions.append(or_(User.id.in_(users_with_cards_in_store), ~User.id.in_(all_users_with_cards)))
        if conditions:
            query = query.where(and_(*conditions))

        count_query = select(func.count(User.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = await self.db.scalar(count_query)

        query = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        users = result.scalars().all()

        if not users:
            return [], total or 0

        user_ids = [u.id for u in users]

        # 批量获取 cardCount
        card_count_subq = (
            select(Patient.user_id, func.count(Patient.id).label("cnt"))
            .where(Patient.user_id.in_(user_ids))
            .group_by(Patient.user_id)
        )
        if tenant_id:
            card_count_subq = card_count_subq.where(Patient.tenant_id == tenant_id)
        card_result = await self.db.execute(card_count_subq)
        card_count_map = dict(card_result.all())

        # 批量获取 appointmentCount（通过 Patient 关联）
        appt_count_subq = (
            select(Patient.user_id, func.count(Appointment.id).label("cnt"))
            .join(Patient, Appointment.patient_id == Patient.id)
            .where(Patient.user_id.in_(user_ids))
            .group_by(Patient.user_id)
        )
        if tenant_id:
            appt_count_subq = appt_count_subq.where(
                Appointment.tenant_id == tenant_id,
                Patient.tenant_id == tenant_id,
            )
        appt_result = await self.db.execute(appt_count_subq)
        appt_count_map = dict(appt_result.all())

        user_data = [
            {
                "id": user.id,
                "phone": user.phone,
                "nickname": user.nickname or "微信用户",
                "avatar": user.avatar,
                "gender": user.gender,
                "status": user.status,
                "points": user.points or 0,
                "cardCount": card_count_map.get(user.id, 0),
                "appointmentCount": appt_count_map.get(user.id, 0),
                "createdAt": user.created_at.isoformat() if user.created_at else None,
            }
            for user in users
        ]
        return user_data, total or 0

    async def get_detail(self, user_id: str) -> Optional[dict]:
        tenant_id = self._current_tenant_id()
        query = select(User).where(User.id == user_id)
        if tenant_id:
            query = query.where(User.tenant_id == tenant_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            return None

        cards_query = select(Patient).where(Patient.user_id == user_id)
        if tenant_id:
            cards_query = cards_query.where(Patient.tenant_id == tenant_id)
        cards_result = await self.db.execute(
            cards_query.order_by(Patient.is_default.desc(), Patient.created_at.asc())
        )
        cards = cards_result.scalars().all()

        card_ids = [c.id for c in cards]

        if card_ids:
            # 批量获取每张卡的 appointmentCount
            card_appt_subq = (
                select(Appointment.patient_id, func.count(Appointment.id).label("cnt"))
                .where(Appointment.patient_id.in_(card_ids))
                .group_by(Appointment.patient_id)
            )
            if tenant_id:
                card_appt_subq = card_appt_subq.where(Appointment.tenant_id == tenant_id)
            card_appt_result = await self.db.execute(card_appt_subq)
            card_appt_map = dict(card_appt_result.all())

            # 批量获取每张卡的 noShowCount
            card_noshow_subq = (
                select(Appointment.patient_id, func.count(Appointment.id).label("cnt"))
                .where(
                    and_(
                        Appointment.patient_id.in_(card_ids),
                        Appointment.status == APPOINTMENT_STATUS["NO_SHOW"],
                    )
                )
                .group_by(Appointment.patient_id)
            )
            if tenant_id:
                card_noshow_subq = card_noshow_subq.where(Appointment.tenant_id == tenant_id)
            card_noshow_result = await self.db.execute(card_noshow_subq)
            card_noshow_map = dict(card_noshow_result.all())
        else:
            card_appt_map = {}
            card_noshow_map = {}

        cards_data = [
            {
                "id": card.id,
                "cardNo": card.card_no,
                "name": card.name,
                "phone": card.phone,
                "idCard": card.id_card,
                "gender": card.gender,
                "age": card.age,
                "birthday": card.birthday.isoformat() if card.birthday else None,
                "relationship": card.relationship,
                "isDefault": card.is_default,
                "source": card.source or 1,
                "appointmentCount": card_appt_map.get(card.id, 0),
                "noShowCount": card_noshow_map.get(card.id, 0),
                "createdAt": card.created_at.isoformat() if card.created_at else None,
            }
            for card in cards
        ]

        # 总预约数和总爽约数（通过所有卡汇总）
        total_appointment_count = sum(card_appt_map.get(c.id, 0) for c in cards)
        total_no_show_count = sum(card_noshow_map.get(c.id, 0) for c in cards)

        return {
            "id": user.id,
            "phone": user.phone,
            "nickname": user.nickname or "微信用户",
            "avatar": user.avatar,
            "gender": user.gender,
            "openid": user.openid,
            "unionid": user.unionid,
            "wechatNickname": user.wechat_nickname,
            "wechatAvatar": user.wechat_avatar,
            "wechatSyncedAt": user.wechat_synced_at.isoformat() if user.wechat_synced_at else None,
            "status": user.status,
            "points": user.points or 0,
            "createdAt": user.created_at.isoformat() if user.created_at else None,
            "updatedAt": user.updated_at.isoformat() if user.updated_at else None,
            "cardCount": len(cards_data),
            "appointmentCount": total_appointment_count,
            "noShowCount": total_no_show_count,
            "cards": cards_data,
        }

    async def update_status(self, user_id: str, status: int, operator_id: Optional[str] = None) -> bool:
        query = select(User).where(User.id == user_id)
        tenant_id = self._current_tenant_id()
        if tenant_id:
            query = query.where(User.tenant_id == tenant_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            return False
        user.status = status
        set_update_audit(user, operator_id)
        await self.db.commit()
        return True

    async def delete_user(self, user_id: str, operator_id: Optional[str] = None) -> bool:
        tenant_id = self._current_tenant_id()
        query = select(User).where(User.id == user_id)
        if tenant_id:
            query = query.where(User.tenant_id == tenant_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            return False

        appt_count_query = select(func.count(Appointment.id)).join(Patient, Appointment.patient_id == Patient.id).where(Patient.user_id == user_id)
        if tenant_id:
            appt_count_query = appt_count_query.where(
                Appointment.tenant_id == tenant_id,
                Patient.tenant_id == tenant_id,
            )
        appt_count = await self.db.scalar(appt_count_query)
        if appt_count and appt_count > 0:
            raise ValueError("该用户有预约记录，无法删除")

        cards_query = select(Patient).where(Patient.user_id == user_id)
        if tenant_id:
            cards_query = cards_query.where(Patient.tenant_id == tenant_id)
        cards_result = await self.db.execute(cards_query)
        cards = cards_result.scalars().all()
        for card in cards:
            await self.db.delete(card)
        await self.db.delete(user)
        await self.db.commit()
        return True

    async def update_user(self, user_id: str, data, operator_id: Optional[str] = None) -> Optional[dict]:
        query = select(User).where(User.id == user_id)
        tenant_id = self._current_tenant_id()
        if tenant_id:
            query = query.where(User.tenant_id == tenant_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            return None
        update_data = data.model_dump(exclude_unset=True)
        allowed_fields = ["nickname", "avatar", "gender", "phone"]
        for key, value in update_data.items():
            field_name = key if hasattr(user, key) else None
            if field_name and field_name in allowed_fields:
                setattr(user, field_name, value)
        set_update_audit(user, operator_id)
        await self.db.commit()
        await self.db.refresh(user)
        return await self.get_detail(user_id)

    async def create_card(self, user_id: str, data, operator_id: Optional[str] = None) -> Optional[dict]:
        tenant_id = self._current_tenant_id()
        query = select(User).where(User.id == user_id)
        if tenant_id:
            query = query.where(User.tenant_id == tenant_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            return None

        existing_query = select(Patient).where(and_(Patient.user_id == user_id, Patient.name == data.name))
        if tenant_id:
            existing_query = existing_query.where(Patient.tenant_id == tenant_id)
        existing = await self.db.execute(existing_query)
        if existing.scalar_one_or_none():
            raise ValueError(f"该用户下已存在名为 {data.name} 的就诊卡")

        birthday = None
        if data.birthday:
            try:
                birthday = datetime.strptime(data.birthday, "%Y-%m-%d")
            except ValueError:
                pass

        if data.is_default:
            from sqlalchemy import update as sql_update

            await self.db.execute(sql_update(Patient).where(Patient.user_id == user_id).values(is_default=False))

        card = Patient(
            id=str(uuid.uuid4()),
            user_id=user_id,
            tenant_id=tenant_id or user.tenant_id,
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
        set_create_audit(card, operator_id)
        self.db.add(card)
        await self.db.commit()
        return {
            "id": card.id,
            "userId": card.user_id,
            "cardNo": card.card_no,
            "name": card.name,
            "phone": card.phone,
            "idCard": card.id_card,
            "gender": card.gender,
            "birthday": card.birthday.isoformat() if card.birthday else None,
            "relationship": card.relationship,
            "isDefault": card.is_default,
            "appointmentCount": 0,
            "noShowCount": 0,
            "createdAt": card.created_at.isoformat() if card.created_at else None,
        }

    async def update_card(self, user_id: str, card_id: str, data, operator_id: Optional[str] = None) -> Optional[dict]:
        result = await self.db.execute(select(Patient).where(and_(Patient.id == card_id, Patient.user_id == user_id)))
        card = result.scalar_one_or_none()
        if not card:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if update_data.get("is_default"):
            from sqlalchemy import update as sql_update

            await self.db.execute(
                sql_update(Patient).where(and_(Patient.user_id == user_id, Patient.id != card_id)).values(is_default=False)
            )
        for key, value in update_data.items():
            if hasattr(card, key):
                setattr(card, key, value)
        set_update_audit(card, operator_id)
        await self.db.commit()
        await self.db.refresh(card)

        appointment_count = await self.db.scalar(select(func.count(Appointment.id)).where(Appointment.patient_id == card_id))
        no_show_count = await self.db.scalar(
            select(func.count(Appointment.id)).where(and_(Appointment.patient_id == card_id, Appointment.status == APPOINTMENT_STATUS["NO_SHOW"]))
        )
        return {
            "id": card.id,
            "userId": card.user_id,
            "cardNo": card.card_no,
            "name": card.name,
            "phone": card.phone,
            "idCard": card.id_card,
            "gender": card.gender,
            "age": card.age,
            "birthday": card.birthday.isoformat() if card.birthday else None,
            "relationship": card.relationship,
            "isDefault": card.is_default,
            "source": card.source or 1,
            "appointmentCount": appointment_count or 0,
            "noShowCount": no_show_count or 0,
            "createdAt": card.created_at.isoformat() if card.created_at else None,
        }

    async def delete_card(self, user_id: str, card_id: str) -> bool:
        result = await self.db.execute(select(Patient).where(and_(Patient.id == card_id, Patient.user_id == user_id)))
        card = result.scalar_one_or_none()
        if not card:
            return False

        card_count = await self.db.scalar(select(func.count(Patient.id)).where(Patient.user_id == user_id))
        if card_count and card_count <= 1:
            raise ValueError("用户至少需要保留一张就诊卡")

        appt_count = await self.db.scalar(select(func.count(Appointment.id)).where(Appointment.patient_id == card_id))
        if appt_count and appt_count > 0:
            raise ValueError("该就诊卡有预约记录，无法删除")

        if card.is_default:
            other_card = await self.db.execute(
                select(Patient).where(and_(Patient.user_id == user_id, Patient.id != card_id)).limit(1)
            )
            other = other_card.scalar_one_or_none()
            if other:
                other.is_default = True

        await self.db.delete(card)
        await self.db.commit()
        return True
