"""Doctor-level consultation-fee operations."""

import uuid

from sqlalchemy import and_, delete, select
from sqlalchemy.orm import selectinload

from app.models.consultation_fee import DoctorConsultationFee
from app.models.doctor import Doctor
from app.schemas.consultation_fee import (
    DoctorConsultationFeeBatchCreate,
    DoctorConsultationFeeCreate,
    DoctorConsultationFeeUpdate,
)
from app.utils.audit import set_create_audit, set_update_audit

from .service_types import store_tenant_id


class ConsultationFeeDoctorMixin:
    async def get_doctor_fees(
        self,
        doctor_id: str | None = None,
        store_id: str | None = None,
        department_id: str | None = None,
    ) -> list[DoctorConsultationFee]:
        query = select(DoctorConsultationFee).options(
            selectinload(DoctorConsultationFee.doctor),
            selectinload(DoctorConsultationFee.store),
            selectinload(DoctorConsultationFee.department),
            selectinload(DoctorConsultationFee.fee_type),
        )
        if doctor_id:
            query = query.where(DoctorConsultationFee.doctor_id == doctor_id)
        if store_id:
            query = query.where(DoctorConsultationFee.store_id == store_id)
        if department_id:
            query = query.join(DoctorConsultationFee.doctor).where(
                DoctorConsultationFee.doctor.has(department_id=department_id)
            )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_doctor_fee_by_id(self, fee_id: str) -> DoctorConsultationFee | None:
        result = await self.db.execute(
            select(DoctorConsultationFee)
            .options(
                selectinload(DoctorConsultationFee.doctor),
                selectinload(DoctorConsultationFee.store),
                selectinload(DoctorConsultationFee.department),
                selectinload(DoctorConsultationFee.fee_type),
            )
            .where(DoctorConsultationFee.id == fee_id)
        )
        return result.scalar_one_or_none()

    async def get_doctor_fee_unique(
        self,
        doctor_id: str,
        store_id: str,
        department_id: str,
        fee_type_id: str,
    ) -> DoctorConsultationFee | None:
        # 自然键为 (doctor_id, store_id, department_id, fee_type_id)，已有唯一约束保证唯一。
        result = await self.db.execute(
            select(DoctorConsultationFee)
            .where(
                and_(
                    DoctorConsultationFee.doctor_id == doctor_id,
                    DoctorConsultationFee.store_id == store_id,
                    DoctorConsultationFee.department_id == department_id,
                    DoctorConsultationFee.fee_type_id == fee_type_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create_doctor_fee(
        self, data: DoctorConsultationFeeCreate, operator_id: str | None = None
    ) -> DoctorConsultationFee:
        fee = DoctorConsultationFee(
            id=str(uuid.uuid4()),
            doctor_id=data.doctor_id,
            store_id=data.store_id,
            tenant_id=await store_tenant_id(self.db, data.store_id),
            department_id=data.department_id,
            fee_type_id=data.fee_type_id,
            initial_fee=data.initial_fee,
            follow_up_fee=data.follow_up_fee,
            use_template=data.use_template,
            status=data.status,
        )
        set_create_audit(fee, operator_id)
        self.db.add(fee)
        await self.db.commit()
        await self.db.refresh(fee)
        return fee

    async def update_doctor_fee(
        self, fee_id: str, data: DoctorConsultationFeeUpdate, operator_id: str | None = None
    ) -> DoctorConsultationFee | None:
        fee = await self.get_doctor_fee_by_id(fee_id)
        if not fee:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(fee, field):
                setattr(fee, field, value)

        set_update_audit(fee, operator_id)
        await self.db.commit()
        await self.db.refresh(fee)
        return fee

    async def batch_save_doctor_fees(
        self, data: DoctorConsultationFeeBatchCreate, operator_id: str | None = None
    ) -> list[DoctorConsultationFee]:
        result = []
        tenant_id = await store_tenant_id(self.db, data.store_id)
        for item in data.fees:
            existing = await self.get_doctor_fee_unique(
                data.doctor_id, data.store_id, data.department_id, item.fee_type_id
            )
            if existing:
                existing.initial_fee = item.initial_fee
                existing.follow_up_fee = item.follow_up_fee
                # 手动填写的金额 → 不沿用模板
                existing.use_template = 0
                set_update_audit(existing, operator_id)
                fee = existing
            else:
                fee = DoctorConsultationFee(
                    id=str(uuid.uuid4()),
                    doctor_id=data.doctor_id,
                    store_id=data.store_id,
                    tenant_id=tenant_id,
                    department_id=data.department_id,
                    fee_type_id=item.fee_type_id,
                    initial_fee=item.initial_fee,
                    follow_up_fee=item.follow_up_fee,
                    use_template=0,
                    status=1,
                )
                set_create_audit(fee, operator_id)
                self.db.add(fee)
            result.append(fee)

        await self.db.commit()
        return result

    async def delete_doctor_fee(self, fee_id: str) -> bool:
        fee = await self.get_doctor_fee_by_id(fee_id)
        if not fee:
            return False
        await self.db.delete(fee)
        await self.db.commit()
        return True

    async def delete_doctor_fees_by_store_department(
        self, store_id: str, department_id: str | None = None
    ) -> int:
        query = delete(DoctorConsultationFee).where(DoctorConsultationFee.store_id == store_id)
        if department_id:
            query = query.where(
                DoctorConsultationFee.doctor_id.in_(
                    select(DoctorConsultationFee.doctor_id).where(
                        DoctorConsultationFee.doctor.has(department_id=department_id)
                    )
                )
            )
        result = await self.db.execute(query)
        await self.db.commit()
        return result.rowcount or 0

    async def get_doctor_fee_setting(self, doctor_id: str) -> dict:
        # doctor_name/use_fee_template 为 router 契约键（此前缺失导致端点恒 500）
        doctor = await self.db.get(Doctor, doctor_id)
        fees = await self.get_doctor_fees(doctor_id=doctor_id)
        use_template = 1
        if fees:
            use_template = fees[0].use_template
        return {
            "doctor_id": doctor_id,
            "doctor_name": doctor.name if doctor else None,
            "use_template": use_template,
            "use_fee_template": use_template,
            "fees": fees,
        }

    async def update_doctor_use_template(self, doctor_id: str, use_template: int) -> bool:
        fees = await self.get_doctor_fees(doctor_id=doctor_id)
        for fee in fees:
            fee.use_template = use_template
        await self.db.commit()
        return True

    async def get_doctor_fees_grouped(self, doctor_id: str) -> list[dict]:
        fees = await self.get_doctor_fees(doctor_id=doctor_id)
        grouped = {}
        for fee in fees:
            store_id = fee.store_id
            grouped.setdefault(
                store_id,
                {
                    "store_id": store_id,
                    "store_name": fee.store.name if fee.store else None,
                    "fees": [],
                },
            )
            grouped[store_id]["fees"].append(fee)
        return list(grouped.values())
