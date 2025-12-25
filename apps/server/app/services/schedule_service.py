from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import date, timedelta
import uuid

from app.models.schedule import Schedule
from app.models.doctor import Doctor
from app.schemas.schedule import ScheduleCreate, ScheduleBatchCreate, ScheduleUpdate

class ScheduleService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, schedule_id: str) -> Optional[Schedule]:
        result = await self.db.execute(
            select(Schedule).options(selectinload(Schedule.doctor)).where(Schedule.id == schedule_id)
        )
        return result.scalar_one_or_none()
    
    async def get_list(
        self,
        doctor_id: Optional[str] = None,
        store_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[int] = None,
        page: int = 1,
        page_size: int = 10
    ) -> tuple[List[Schedule], int]:
        query = select(Schedule).options(selectinload(Schedule.doctor))
        count_query = select(func.count(Schedule.id))
        
        if doctor_id:
            query = query.where(Schedule.doctor_id == doctor_id)
            count_query = count_query.where(Schedule.doctor_id == doctor_id)
        if store_id:
            query = query.where(Schedule.store_id == store_id)
            count_query = count_query.where(Schedule.store_id == store_id)
        if start_date:
            query = query.where(Schedule.schedule_date >= start_date)
            count_query = count_query.where(Schedule.schedule_date >= start_date)
        if end_date:
            query = query.where(Schedule.schedule_date <= end_date)
            count_query = count_query.where(Schedule.schedule_date <= end_date)
        if status is not None:
            query = query.where(Schedule.status == status)
            count_query = count_query.where(Schedule.status == status)
        
        query = query.order_by(Schedule.schedule_date, Schedule.time_slot).offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)
        
        return list(result.scalars().all()), count_result.scalar() or 0
    
    async def get_available(self, doctor_id: str, days: int = 14) -> List[Schedule]:
        """获取可预约排班"""
        today = date.today()
        end_date = today + timedelta(days=days)
        
        result = await self.db.execute(
            select(Schedule)
            .where(
                and_(
                    Schedule.doctor_id == doctor_id,
                    Schedule.schedule_date >= today,
                    Schedule.schedule_date <= end_date,
                    Schedule.status == 1,
                    Schedule.booked_slots < Schedule.total_slots
                )
            )
            .order_by(Schedule.schedule_date, Schedule.time_slot)
        )
        return list(result.scalars().all())
    
    async def create(self, data: ScheduleCreate) -> Schedule:
        # 检查是否已存在
        existing = await self.db.execute(
            select(Schedule).where(
                and_(
                    Schedule.doctor_id == data.doctor_id,
                    Schedule.schedule_date == data.schedule_date,
                    Schedule.time_slot == data.time_slot
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("该时段排班已存在")
        
        # 如果没有传递 store_id，从医生信息中获取
        store_id = data.store_id
        if not store_id:
            doctor_result = await self.db.execute(
                select(Doctor).where(Doctor.id == data.doctor_id)
            )
            doctor = doctor_result.scalar_one_or_none()
            if doctor:
                store_id = doctor.store_id
        
        schedule = Schedule(
            id=str(uuid.uuid4()),
            doctor_id=data.doctor_id,
            store_id=store_id,
            schedule_date=data.schedule_date,
            time_slot=data.time_slot,
            start_time=data.start_time,
            end_time=data.end_time,
            total_slots=data.total_slots,
            booked_slots=0,
            status=data.status
        )
        self.db.add(schedule)
        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule
    
    async def batch_create(self, data: ScheduleBatchCreate) -> int:
        """批量创建排班"""
        # 先获取医生的 store_id
        doctor_result = await self.db.execute(
            select(Doctor).where(Doctor.id == data.doctor_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        store_id = doctor.store_id if doctor else None
        
        created_count = 0
        current_date = data.start_date
        
        while current_date <= data.end_date:
            weekday = current_date.isoweekday()  # 1-7 代表周一到周日
            
            if weekday in data.weekdays:
                for time_slot in data.time_slots:
                    # 检查是否已存在
                    existing = await self.db.execute(
                        select(Schedule).where(
                            and_(
                                Schedule.doctor_id == data.doctor_id,
                                Schedule.schedule_date == current_date,
                                Schedule.time_slot == time_slot
                            )
                        )
                    )
                    if not existing.scalar_one_or_none():
                        schedule = Schedule(
                            id=str(uuid.uuid4()),
                            doctor_id=data.doctor_id,
                            store_id=store_id,
                            schedule_date=current_date,
                            time_slot=time_slot,
                            total_slots=data.total_slots,
                            booked_slots=0,
                            status=1
                        )
                        self.db.add(schedule)
                        created_count += 1
            
            current_date += timedelta(days=1)
        
        await self.db.commit()
        return created_count
    
    async def update(self, schedule_id: str, data: ScheduleUpdate) -> Optional[Schedule]:
        schedule = await self.get_by_id(schedule_id)
        if not schedule:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        
        # 校验号源数不能小于已预约数
        if 'total_slots' in update_data and update_data['total_slots'] < schedule.booked_slots:
            raise ValueError("总号源数不能小于已预约数")
        
        for field, value in update_data.items():
            setattr(schedule, field, value)
        
        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule
    
    async def suspend(self, schedule_id: str) -> Optional[Schedule]:
        """停诊"""
        schedule = await self.get_by_id(schedule_id)
        if not schedule:
            return None
        
        schedule.status = 0
        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule

    async def resume(self, schedule_id: str) -> Optional[Schedule]:
        """恢复排班"""
        schedule = await self.get_by_id(schedule_id)
        if not schedule:
            return None
        
        schedule.status = 1
        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule

