from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import date, time, timedelta
import uuid
import json

from app.models.custom_schedule import CustomSchedule
from app.models.doctor import Doctor
from app.models.store import Store
from app.models.department import Department
from app.schemas.custom_schedule import CustomScheduleCreate, TimePeriod


def add_minutes(t: time, minutes: int) -> time:
    """给时间添加分钟"""
    total_minutes = t.hour * 60 + t.minute + minutes
    return time(hour=total_minutes // 60, minute=total_minutes % 60)


def generate_time_slots(start_time: time, end_time: time, slot_count: int) -> List[dict]:
    """根据总时间段和数量自动均分"""
    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute
    total_minutes = end_minutes - start_minutes
    slot_minutes = total_minutes // slot_count
    
    slots = []
    current = start_time
    for i in range(slot_count):
        slot_end = add_minutes(current, slot_minutes)
        slots.append({"start_time": current, "end_time": slot_end})
        current = slot_end
    return slots


class CustomScheduleService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, schedule_id: str) -> Optional[CustomSchedule]:
        result = await self.db.execute(
            select(CustomSchedule)
            .options(
                selectinload(CustomSchedule.store),
                selectinload(CustomSchedule.department),
                selectinload(CustomSchedule.doctor)
            )
            .where(CustomSchedule.id == schedule_id)
        )
        return result.scalar_one_or_none()
    
    async def get_list(
        self,
        store_id: Optional[str] = None,
        department_id: Optional[str] = None,
        doctor_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        appointment_type: Optional[str] = None,
        status: Optional[int] = None,
        page: int = 1,
        page_size: int = 10
    ) -> tuple[List[CustomSchedule], int]:
        query = select(CustomSchedule).options(
            selectinload(CustomSchedule.store),
            selectinload(CustomSchedule.department),
            selectinload(CustomSchedule.doctor)
        )
        count_query = select(func.count(CustomSchedule.id))
        
        conditions = []
        if store_id:
            conditions.append(CustomSchedule.store_id == store_id)
        if department_id:
            conditions.append(CustomSchedule.department_id == department_id)
        if doctor_id:
            conditions.append(CustomSchedule.doctor_id == doctor_id)
        if start_date:
            conditions.append(CustomSchedule.schedule_date >= start_date)
        if end_date:
            conditions.append(CustomSchedule.schedule_date <= end_date)
        if appointment_type:
            conditions.append(CustomSchedule.appointment_type == appointment_type)
        if status is not None:
            conditions.append(CustomSchedule.status == status)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        query = query.order_by(CustomSchedule.schedule_date, CustomSchedule.start_time)
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)
        
        return list(result.scalars().all()), count_result.scalar() or 0
    
    async def create(self, data: CustomScheduleCreate) -> List[CustomSchedule]:
        """创建自定义排班（支持批量）"""
        created_schedules = []
        
        for schedule_date in data.schedule_dates:
            for period in data.time_periods:
                # 判断是否需要均分时段
                if period.slot_count and period.slot_count > 1:
                    # 自动均分时段
                    slots = generate_time_slots(
                        period.start_time, 
                        period.end_time, 
                        period.slot_count
                    )
                    for slot in slots:
                        schedule = CustomSchedule(
                            id=str(uuid.uuid4()),
                            store_id=data.store_id,
                            department_id=data.department_id,
                            doctor_id=data.doctor_id,
                            schedule_date=schedule_date,
                            start_time=slot["start_time"],
                            end_time=slot["end_time"],
                            appointment_type=period.appointment_type.value,
                            max_patients=period.max_patients,
                            booked_count=0,
                            status=1
                        )
                        self.db.add(schedule)
                        created_schedules.append(schedule)
                else:
                    # 不均分，直接使用指定的时间段
                    schedule = CustomSchedule(
                        id=str(uuid.uuid4()),
                        store_id=data.store_id,
                        department_id=data.department_id,
                        doctor_id=data.doctor_id,
                        schedule_date=schedule_date,
                        start_time=period.start_time,
                        end_time=period.end_time,
                        appointment_type=period.appointment_type.value,
                        max_patients=period.max_patients,
                        booked_count=0,
                        status=1
                    )
                    self.db.add(schedule)
                    created_schedules.append(schedule)
        
        await self.db.commit()
        
        # 重新加载关联数据
        for s in created_schedules:
            await self.db.refresh(s)
        
        return created_schedules
    
    async def delete(self, schedule_id: str) -> bool:
        """删除自定义排班"""
        schedule = await self.get_by_id(schedule_id)
        if not schedule:
            return False
        
        # 检查是否有预约
        if schedule.booked_count > 0:
            raise ValueError("该排班已有预约，无法删除")
        
        await self.db.delete(schedule)
        await self.db.commit()
        return True
    
    async def get_effective_schedules(
        self,
        store_id: Optional[str] = None,
        doctor_id: Optional[str] = None,
        start_date: date = None,
        end_date: date = None
    ) -> List[CustomSchedule]:
        """获取生效的自定义排班"""
        query = select(CustomSchedule).options(
            selectinload(CustomSchedule.store),
            selectinload(CustomSchedule.department),
            selectinload(CustomSchedule.doctor)
        ).where(CustomSchedule.status == 1)
        
        conditions = []
        if store_id:
            conditions.append(CustomSchedule.store_id == store_id)
        if doctor_id:
            conditions.append(CustomSchedule.doctor_id == doctor_id)
        if start_date:
            conditions.append(CustomSchedule.schedule_date >= start_date)
        if end_date:
            conditions.append(CustomSchedule.schedule_date <= end_date)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(CustomSchedule.schedule_date, CustomSchedule.start_time)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def check_custom_schedule(
        self,
        doctor_id: str,
        schedule_date: date,
        start_time: time,
        end_time: time
    ) -> Optional[CustomSchedule]:
        """检查指定时间是否存在自定义排班"""
        result = await self.db.execute(
            select(CustomSchedule).where(
                and_(
                    CustomSchedule.doctor_id == doctor_id,
                    CustomSchedule.schedule_date == schedule_date,
                    CustomSchedule.status == 1,
                    or_(
                        and_(
                            CustomSchedule.start_time <= start_time,
                            CustomSchedule.end_time > start_time
                        ),
                        and_(
                            CustomSchedule.start_time < end_time,
                            CustomSchedule.end_time >= end_time
                        ),
                        and_(
                            CustomSchedule.start_time >= start_time,
                            CustomSchedule.end_time <= end_time
                        )
                    )
                )
            )
        )
        return result.scalar_one_or_none()
