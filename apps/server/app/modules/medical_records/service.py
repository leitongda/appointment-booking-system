"""病历服务"""
import uuid
from datetime import date, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.middleware.tenant_context import get_current_tenant_id
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.medical_record import MedicalRecord
from app.schemas.medical_record import MedicalRecordCreate, MedicalRecordUpdate
from app.utils.audit import set_create_audit, set_update_audit


def generate_record_no() -> str:
    """生成病历号"""
    now = datetime.now()
    return f"MR{now.strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4].upper()}"


class MedicalRecordService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, doctor_id: str, data: MedicalRecordCreate) -> MedicalRecord:
        """创建病历"""
        tenant_id = get_current_tenant_id()

        # 获取预约信息
        appointment = await self.db.get(Appointment, data.appointment_id)
        if not appointment:
            raise ValueError("预约不存在")

        # 校验预约状态：仅已签到(2)、就诊中(4)、已完成(5)可创建病历
        allowed_statuses = {2, 4, 5}
        if appointment.status not in allowed_statuses:
            raise ValueError("预约状态不允许创建病历，需已签到/就诊中/已完成")

        # 检查是否已存在病历（含软删除过滤）
        existing = await self.db.execute(
            select(MedicalRecord).where(
                MedicalRecord.appointment_id == data.appointment_id,
                MedicalRecord.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("该预约已有病历记录")

        # 获取医生信息
        doctor = await self.db.get(Doctor, doctor_id)
        if not doctor:
            raise ValueError("医生不存在")

        record = MedicalRecord(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            record_no=generate_record_no(),
            appointment_id=data.appointment_id,
            patient_id=appointment.patient_id,
            doctor_id=doctor_id,
            department_id=doctor.department_id,
            chief_complaint=data.chief_complaint,
            present_illness=data.present_illness,
            past_history=data.past_history,
            allergy_history=data.allergy_history,
            family_history=data.family_history,
            medication_history=data.medication_history,
            physical_exam=data.physical_exam,
            auxiliary_exam=data.auxiliary_exam,
            diagnosis=data.diagnosis,
            treatment=data.treatment,
            prescription=data.prescription,
            advice=data.advice,
            total_fee=data.total_fee or 0,
            status=data.status,
            visit_date=data.visit_date or datetime.now(),
        )
        set_create_audit(record, doctor_id)

        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)

        # 自动生成随访任务
        if data.follow_up_plan_id:
            from app.modules.follow_up.service import FollowUpTaskService
            follow_up_service = FollowUpTaskService(self.db)
            try:
                await follow_up_service.generate_from_plan(
                    patient_id=record.patient_id,
                    doctor_id=doctor_id,
                    department_id=record.department_id,
                    plan_id=data.follow_up_plan_id,
                    appointment_id=record.appointment_id,
                    medical_record_id=record.id,
                    operator_id=doctor_id,
                )
            except ValueError:
                pass  # 计划不存在时不阻塞病历创建

        return record

    async def get_by_id(self, record_id: str) -> MedicalRecord | None:
        """根据ID获取病历"""
        stmt = (
            select(MedicalRecord)
            .options(
                joinedload(MedicalRecord.patient),
                joinedload(MedicalRecord.doctor),
                joinedload(MedicalRecord.department),
            )
            .where(MedicalRecord.id == record_id, MedicalRecord.deleted_at.is_(None))
        )
        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(MedicalRecord.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_by_appointment(self, appointment_id: str) -> MedicalRecord | None:
        """根据预约ID获取病历"""
        stmt = (
            select(MedicalRecord)
            .options(
                joinedload(MedicalRecord.patient),
                joinedload(MedicalRecord.doctor),
                joinedload(MedicalRecord.department),
            )
            .where(MedicalRecord.appointment_id == appointment_id, MedicalRecord.deleted_at.is_(None))
        )
        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(MedicalRecord.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_list(
        self,
        doctor_id: str | None = None,
        patient_id: str | None = None,
        department_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        status: int | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[MedicalRecord], int]:
        """获取病历列表"""
        query = select(MedicalRecord).options(
            joinedload(MedicalRecord.patient),
            joinedload(MedicalRecord.doctor),
            joinedload(MedicalRecord.department),
        )

        conditions = [MedicalRecord.deleted_at.is_(None)]
        tenant_id = get_current_tenant_id()
        if tenant_id:
            conditions.append(MedicalRecord.tenant_id == tenant_id)

        if doctor_id:
            conditions.append(MedicalRecord.doctor_id == doctor_id)
        if patient_id:
            conditions.append(MedicalRecord.patient_id == patient_id)
        if department_id:
            conditions.append(MedicalRecord.department_id == department_id)
        if start_date:
            conditions.append(func.date(MedicalRecord.visit_date) >= start_date)
        if end_date:
            conditions.append(func.date(MedicalRecord.visit_date) <= end_date)
        if status:
            conditions.append(MedicalRecord.status == status)
        if keyword:
            conditions.append(
                MedicalRecord.diagnosis.ilike(f"%{keyword}%") |
                MedicalRecord.chief_complaint.ilike(f"%{keyword}%")
            )

        if conditions:
            query = query.where(and_(*conditions))

        # 统计总数
        count_query = select(func.count(MedicalRecord.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = await self.db.scalar(count_query)

        # 分页查询
        query = query.order_by(MedicalRecord.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        records = result.unique().scalars().all()

        return list(records), total or 0

    async def get_patient_records(
        self,
        patient_id: str,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[MedicalRecord], int]:
        """获取患者的病历列表"""
        return await self.get_list(patient_id=patient_id, page=page, page_size=page_size)

    async def update(self, record_id: str, data: MedicalRecordUpdate, operator_id: str | None = None) -> MedicalRecord | None:
        """更新病历"""
        record = await self.db.get(MedicalRecord, record_id)
        if not record:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(record, key, value)

        set_update_audit(record, operator_id)
        await self.db.commit()
        await self.db.refresh(record)

        return record

    async def delete(self, record_id: str, operator_id: str | None = None) -> bool:
        """软删除病历"""
        record = await self.db.get(MedicalRecord, record_id)
        if not record or record.deleted_at is not None:
            return False

        record.deleted_at = datetime.now()
        set_update_audit(record, operator_id)
        await self.db.commit()
        return True
