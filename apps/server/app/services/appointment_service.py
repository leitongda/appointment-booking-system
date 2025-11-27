from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime, date
import uuid

from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.user import Patient
from app.schemas.appointment import AppointmentCreate, AppointmentStatistics

# 预约状态
APPOINTMENT_STATUS = {
    'PENDING': 1,      # 待就诊
    'SIGNED_IN': 2,    # 已签到
    'IN_PROGRESS': 3,  # 就诊中
    'PASSED': 4,       # 已过号
    'COMPLETED': 5,    # 已完成
    'CANCELLED': 6,    # 已取消
    'NO_SHOW': 7       # 已爽约
}

class AppointmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, appointment_id: str) -> Optional[Appointment]:
        result = await self.db.execute(
            select(Appointment)
            .options(selectinload(Appointment.schedule))
            .where(Appointment.id == appointment_id)
        )
        return result.scalar_one_or_none()
    
    async def get_list(
        self,
        user_id: Optional[str] = None,
        doctor_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        status: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        page: int = 1,
        page_size: int = 10
    ) -> tuple[List[Appointment], int]:
        query = select(Appointment).options(selectinload(Appointment.schedule))
        count_query = select(func.count(Appointment.id))
        
        if user_id:
            query = query.where(Appointment.user_id == user_id)
            count_query = count_query.where(Appointment.user_id == user_id)
        if doctor_id:
            query = query.where(Appointment.doctor_id == doctor_id)
            count_query = count_query.where(Appointment.doctor_id == doctor_id)
        if patient_id:
            query = query.where(Appointment.patient_id == patient_id)
            count_query = count_query.where(Appointment.patient_id == patient_id)
        if status is not None:
            query = query.where(Appointment.status == status)
            count_query = count_query.where(Appointment.status == status)
        
        query = query.order_by(Appointment.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)
        
        return list(result.scalars().all()), count_result.scalar() or 0
    
    async def get_today_by_doctor(self, doctor_id: str) -> List[Appointment]:
        """获取医生今日预约"""
        today = date.today()
        
        result = await self.db.execute(
            select(Appointment)
            .join(Schedule)
            .where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Schedule.schedule_date == today,
                    Appointment.status.in_([1, 2, 3, 4])
                )
            )
            .order_by(Appointment.queue_number)
        )
        return list(result.scalars().all())
    
    async def get_statistics(self, doctor_id: Optional[str] = None, start_date: Optional[date] = None, end_date: Optional[date] = None) -> AppointmentStatistics:
        """获取预约统计"""
        base_query = select(Appointment.status, func.count(Appointment.id))
        
        if doctor_id:
            base_query = base_query.where(Appointment.doctor_id == doctor_id)
        
        base_query = base_query.group_by(Appointment.status)
        
        result = await self.db.execute(base_query)
        status_counts = dict(result.all())
        
        return AppointmentStatistics(
            total=sum(status_counts.values()),
            pending=status_counts.get(1, 0),
            signed_in=status_counts.get(2, 0),
            in_progress=status_counts.get(3, 0),
            completed=status_counts.get(5, 0),
            cancelled=status_counts.get(6, 0),
            no_show=status_counts.get(7, 0)
        )
    
    async def create(self, user_id: str, data: AppointmentCreate) -> Appointment:
        # 获取排班信息
        schedule_result = await self.db.execute(
            select(Schedule).options(selectinload(Schedule.doctor)).where(Schedule.id == data.schedule_id)
        )
        schedule = schedule_result.scalar_one_or_none()
        
        if not schedule:
            raise ValueError("排班不存在")
        if schedule.status != 1:
            raise ValueError("该排班已停诊")
        if schedule.booked_slots >= schedule.total_slots:
            raise ValueError("号源已满")
        
        # 验证就诊人
        patient_result = await self.db.execute(
            select(Patient).where(Patient.id == data.patient_id, Patient.user_id == user_id)
        )
        patient = patient_result.scalar_one_or_none()
        if not patient:
            raise ValueError("就诊人不存在")
        
        # 检查是否重复预约
        existing = await self.db.execute(
            select(Appointment).where(
                and_(
                    Appointment.patient_id == data.patient_id,
                    Appointment.schedule_id == data.schedule_id,
                    Appointment.status.in_([1, 2, 3])
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("该就诊人已预约此时段")
        
        # 生成预约号
        appointment_no = f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4].upper()}"
        
        # 获取队列号
        queue_result = await self.db.execute(
            select(func.max(Appointment.queue_number)).where(Appointment.schedule_id == data.schedule_id)
        )
        max_queue = queue_result.scalar() or 0
        queue_number = max_queue + 1
        
        # 创建预约
        appointment = Appointment(
            id=str(uuid.uuid4()),
            appointment_no=appointment_no,
            user_id=user_id,
            patient_id=data.patient_id,
            doctor_id=schedule.doctor_id,
            schedule_id=data.schedule_id,
            queue_number=queue_number,
            status=APPOINTMENT_STATUS['PENDING']
        )
        self.db.add(appointment)
        
        # 更新排班已预约数
        schedule.booked_slots += 1
        
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment
    
    async def cancel(self, appointment_id: str, user_id: str, reason: Optional[str] = None) -> Optional[Appointment]:
        """取消预约"""
        appointment = await self.get_by_id(appointment_id)
        if not appointment or appointment.user_id != user_id:
            return None
        
        if appointment.status not in [1, 2]:
            raise ValueError("当前状态不可取消")
        
        appointment.status = APPOINTMENT_STATUS['CANCELLED']
        appointment.cancel_time = datetime.now()
        appointment.cancel_reason = reason
        
        # 恢复号源
        schedule = appointment.schedule
        if schedule:
            schedule.booked_slots = max(0, schedule.booked_slots - 1)
        
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment
    
    async def sign_in(self, appointment_id: str) -> Optional[Appointment]:
        """签到"""
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None
        
        if appointment.status != APPOINTMENT_STATUS['PENDING']:
            raise ValueError("当前状态不可签到")
        
        appointment.status = APPOINTMENT_STATUS['SIGNED_IN']
        appointment.sign_in_time = datetime.now()
        
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment
    
    async def call_patient(self, appointment_id: str) -> Optional[Appointment]:
        """叫号"""
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None
        
        if appointment.status != APPOINTMENT_STATUS['SIGNED_IN']:
            raise ValueError("患者未签到")
        
        appointment.status = APPOINTMENT_STATUS['IN_PROGRESS']
        appointment.call_time = datetime.now()
        
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment
    
    async def complete(self, appointment_id: str) -> Optional[Appointment]:
        """完成就诊"""
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None
        
        appointment.status = APPOINTMENT_STATUS['COMPLETED']
        appointment.complete_time = datetime.now()
        
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment

