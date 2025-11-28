"""病历服务"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload, joinedload
from typing import Optional, List, Tuple
from datetime import datetime, date
import uuid

from app.models.medical_record import MedicalRecord
from app.models.appointment import Appointment
from app.models.user import Patient
from app.models.doctor import Doctor
from app.models.department import Department
from app.schemas.medical_record import MedicalRecordCreate, MedicalRecordUpdate


def generate_record_no() -> str:
    """生成病历号"""
    now = datetime.now()
    return f"MR{now.strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4].upper()}"


class MedicalRecordService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, doctor_id: str, data: MedicalRecordCreate) -> MedicalRecord:
        """创建病历"""
        # 获取预约信息
        appointment = await self.db.get(Appointment, data.appointment_id)
        if not appointment:
            raise ValueError("预约不存在")
        
        # 检查是否已存在病历
        existing = await self.db.execute(
            select(MedicalRecord).where(MedicalRecord.appointment_id == data.appointment_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError("该预约已有病历记录")
        
        # 获取医生信息
        doctor = await self.db.get(Doctor, doctor_id)
        if not doctor:
            raise ValueError("医生不存在")
        
        record = MedicalRecord(
            id=str(uuid.uuid4()),
            record_no=generate_record_no(),
            appointment_id=data.appointment_id,
            patient_id=appointment.patient_id,
            doctor_id=doctor_id,
            department_id=doctor.department_id,
            chief_complaint=data.chief_complaint,
            present_illness=data.present_illness,
            past_history=data.past_history,
            allergy_history=data.allergy_history,
            physical_exam=data.physical_exam,
            auxiliary_exam=data.auxiliary_exam,
            diagnosis=data.diagnosis,
            treatment=data.treatment,
            prescription=data.prescription,
            advice=data.advice,
            total_fee=data.total_fee or 0,
            status=data.status,
            visit_date=datetime.now(),
        )
        
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        
        return record

    async def get_by_id(self, record_id: str) -> Optional[MedicalRecord]:
        """根据ID获取病历"""
        result = await self.db.execute(
            select(MedicalRecord)
            .options(
                joinedload(MedicalRecord.patient),
                joinedload(MedicalRecord.doctor),
                joinedload(MedicalRecord.department),
            )
            .where(MedicalRecord.id == record_id)
        )
        return result.unique().scalar_one_or_none()

    async def get_by_appointment(self, appointment_id: str) -> Optional[MedicalRecord]:
        """根据预约ID获取病历"""
        result = await self.db.execute(
            select(MedicalRecord)
            .options(
                joinedload(MedicalRecord.patient),
                joinedload(MedicalRecord.doctor),
                joinedload(MedicalRecord.department),
            )
            .where(MedicalRecord.appointment_id == appointment_id)
        )
        return result.unique().scalar_one_or_none()

    async def get_list(
        self,
        doctor_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        department_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[int] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[MedicalRecord], int]:
        """获取病历列表"""
        query = select(MedicalRecord).options(
            joinedload(MedicalRecord.patient),
            joinedload(MedicalRecord.doctor),
            joinedload(MedicalRecord.department),
        )
        
        conditions = []
        
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
    ) -> Tuple[List[MedicalRecord], int]:
        """获取患者的病历列表"""
        return await self.get_list(patient_id=patient_id, page=page, page_size=page_size)

    async def update(self, record_id: str, data: MedicalRecordUpdate) -> Optional[MedicalRecord]:
        """更新病历"""
        record = await self.db.get(MedicalRecord, record_id)
        if not record:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(record, key, value)
        
        await self.db.commit()
        await self.db.refresh(record)
        
        return record

    async def delete(self, record_id: str) -> bool:
        """删除病历"""
        record = await self.db.get(MedicalRecord, record_id)
        if not record:
            return False
        
        await self.db.delete(record)
        await self.db.commit()
        return True

