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
from app.utils.audit import set_create_audit, set_update_audit

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
    
    async def get_by_appointment_no(self, appointment_no: str) -> Optional[Appointment]:
        """按预约号获取预约"""
        result = await self.db.execute(
            select(Appointment)
            .options(selectinload(Appointment.schedule))
            .where(Appointment.appointment_no == appointment_no)
        )
        return result.scalar_one_or_none()
    
    async def get_list(
        self,
        user_id: Optional[str] = None,
        doctor_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        store_id: Optional[str] = None,
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
        if store_id:
            # 通过关联的 Schedule 表的 store_id 进行过滤
            query = query.join(Schedule).where(Schedule.store_id == store_id)
            count_query = count_query.join(Schedule).where(Schedule.store_id == store_id)
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
    
    async def create(self, user_id: str, data: AppointmentCreate, operator_id: Optional[str] = None) -> Appointment:
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
        # 设置创建人（如果是用户自己创建，使用 user_id；如果是管理员创建，使用 operator_id）
        set_create_audit(appointment, operator_id or user_id)
        self.db.add(appointment)
        
        # 更新排班已预约数
        schedule.booked_slots += 1
        
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment
    
    async def cancel(self, appointment_id: str, user_id: str, reason: Optional[str] = None, is_admin: bool = False, operator_id: Optional[str] = None) -> Optional[Appointment]:
        """取消预约"""
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None
        
        # 非管理员只能取消自己的预约
        if not is_admin and appointment.user_id != user_id:
            return None
        
        if appointment.status not in [1, 2]:
            raise ValueError("当前状态不可取消")
        
        appointment.status = APPOINTMENT_STATUS['CANCELLED']
        appointment.cancel_time = datetime.now()
        appointment.cancel_reason = reason
        set_update_audit(appointment, operator_id or user_id)
        
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

    async def pass_number(self, appointment_id: str) -> Optional[Appointment]:
        """过号（患者未到，跳过）"""
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None
        
        if appointment.status not in [APPOINTMENT_STATUS['SIGNED_IN'], APPOINTMENT_STATUS['IN_PROGRESS']]:
            raise ValueError("当前状态不可过号")
        
        appointment.status = APPOINTMENT_STATUS['PASSED']
        
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment

    async def recall(self, appointment_id: str) -> Optional[Appointment]:
        """重新叫号（过号后再次呼叫）"""
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None
        
        if appointment.status != APPOINTMENT_STATUS['PASSED']:
            raise ValueError("只有过号状态可以重新叫号")
        
        appointment.status = APPOINTMENT_STATUS['IN_PROGRESS']
        appointment.call_time = datetime.now()
        
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment

    async def mark_no_show(self, appointment_id: str) -> Optional[Appointment]:
        """标记爽约"""
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None
        
        if appointment.status not in [APPOINTMENT_STATUS['PENDING'], APPOINTMENT_STATUS['PASSED']]:
            raise ValueError("当前状态不可标记爽约")
        
        appointment.status = APPOINTMENT_STATUS['NO_SHOW']
        
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment

    async def get_queue_info(self, doctor_id: str) -> dict:
        """获取医生当前叫号信息"""
        today = date.today()
        
        # 当前就诊中的患者
        in_progress_result = await self.db.execute(
            select(Appointment)
            .join(Schedule)
            .options(selectinload(Appointment.patient))
            .where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Schedule.schedule_date == today,
                    Appointment.status == APPOINTMENT_STATUS['IN_PROGRESS']
                )
            )
        )
        current = in_progress_result.scalar_one_or_none()
        
        # 候诊队列（已签到）
        waiting_result = await self.db.execute(
            select(Appointment)
            .join(Schedule)
            .options(selectinload(Appointment.patient))
            .where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Schedule.schedule_date == today,
                    Appointment.status == APPOINTMENT_STATUS['SIGNED_IN']
                )
            )
            .order_by(Appointment.sign_in_time)
        )
        waiting_list = list(waiting_result.scalars().all())
        
        # 过号队列
        passed_result = await self.db.execute(
            select(Appointment)
            .join(Schedule)
            .options(selectinload(Appointment.patient))
            .where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Schedule.schedule_date == today,
                    Appointment.status == APPOINTMENT_STATUS['PASSED']
                )
            )
            .order_by(Appointment.queue_number)
        )
        passed_list = list(passed_result.scalars().all())
        
        return {
            'current': {
                'id': current.id,
                'queueNumber': current.queue_number,
                'patientName': current.patient.name if current and current.patient else None,
                'callTime': current.call_time.isoformat() if current and current.call_time else None,
            } if current else None,
            'waitingCount': len(waiting_list),
            'waitingList': [
                {
                    'id': a.id,
                    'queueNumber': a.queue_number,
                    'patientName': a.patient.name if a.patient else None,
                    'signInTime': a.sign_in_time.isoformat() if a.sign_in_time else None,
                }
                for a in waiting_list[:10]
            ],
            'passedCount': len(passed_list),
            'passedList': [
                {
                    'id': a.id,
                    'queueNumber': a.queue_number,
                    'patientName': a.patient.name if a.patient else None,
                }
                for a in passed_list
            ],
        }

