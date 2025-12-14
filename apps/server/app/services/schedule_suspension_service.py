from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import date
import uuid
import json

from app.models.schedule_suspension import ScheduleSuspension
from app.models.schedule import Schedule
from app.models.custom_schedule import CustomSchedule
from app.models.doctor import Doctor
from app.models.store import Store
from app.schemas.schedule_suspension import ScheduleSuspensionCreate, AvailableScheduleForSuspension


class ScheduleSuspensionService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, suspension_id: str) -> Optional[ScheduleSuspension]:
        result = await self.db.execute(
            select(ScheduleSuspension)
            .options(
                selectinload(ScheduleSuspension.store),
                selectinload(ScheduleSuspension.doctor)
            )
            .where(ScheduleSuspension.id == suspension_id)
        )
        return result.scalar_one_or_none()
    
    async def get_list(
        self,
        store_id: Optional[str] = None,
        doctor_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[int] = None,
        page: int = 1,
        page_size: int = 10
    ) -> tuple[List[ScheduleSuspension], int]:
        query = select(ScheduleSuspension).options(
            selectinload(ScheduleSuspension.store),
            selectinload(ScheduleSuspension.doctor)
        )
        count_query = select(func.count(ScheduleSuspension.id))
        
        conditions = []
        if store_id:
            conditions.append(ScheduleSuspension.store_id == store_id)
        if doctor_id:
            conditions.append(ScheduleSuspension.doctor_id == doctor_id)
        if start_date:
            conditions.append(ScheduleSuspension.suspension_date >= start_date)
        if end_date:
            conditions.append(ScheduleSuspension.suspension_date <= end_date)
        if status is not None:
            conditions.append(ScheduleSuspension.status == status)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        query = query.order_by(ScheduleSuspension.suspension_date.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)
        
        return list(result.scalars().all()), count_result.scalar() or 0
    
    async def create(self, data: ScheduleSuspensionCreate) -> ScheduleSuspension:
        """创建停诊"""
        suspension = ScheduleSuspension(
            id=str(uuid.uuid4()),
            store_id=data.store_id,
            doctor_id=data.doctor_id,
            title=data.title,
            suspension_date=data.suspension_date,
            schedule_ids=json.dumps(data.schedule_ids) if data.schedule_ids else None,
            time_slots=json.dumps(data.time_slots) if data.time_slots else None,
            status=1
        )
        self.db.add(suspension)
        await self.db.commit()
        await self.db.refresh(suspension)
        return suspension
    
    async def delete(self, suspension_id: str) -> bool:
        """删除停诊记录"""
        suspension = await self.get_by_id(suspension_id)
        if not suspension:
            return False
        
        await self.db.delete(suspension)
        await self.db.commit()
        return True
    
    async def cancel(self, suspension_id: str) -> Optional[ScheduleSuspension]:
        """取消停诊"""
        suspension = await self.get_by_id(suspension_id)
        if not suspension:
            return None
        
        suspension.status = 0
        await self.db.commit()
        await self.db.refresh(suspension)
        return suspension
    
    async def get_available_schedules(
        self,
        store_id: str,
        doctor_id: str,
        suspension_date: date
    ) -> List[AvailableScheduleForSuspension]:
        """获取指定日期的可选排班（用于停诊选择）"""
        schedules = []
        
        # 1. 获取普通排班
        normal_result = await self.db.execute(
            select(Schedule).where(
                and_(
                    Schedule.doctor_id == doctor_id,
                    Schedule.schedule_date == suspension_date,
                    Schedule.status == 1
                )
            ).order_by(Schedule.start_time)
        )
        normal_schedules = normal_result.scalars().all()
        
        for s in normal_schedules:
            start_str = s.start_time.strftime('%H:%M') if s.start_time else ''
            end_str = s.end_time.strftime('%H:%M') if s.end_time else ''
            time_slot = f"{start_str}-{end_str}" if start_str and end_str else s.time_slot
            
            schedules.append(AvailableScheduleForSuspension(
                schedule_id=s.id,
                time_slot=time_slot,
                schedule_type="normal",
                booked_count=s.booked_slots,
                max_patients=s.total_slots
            ))
        
        # 2. 获取自定义排班
        custom_result = await self.db.execute(
            select(CustomSchedule).where(
                and_(
                    CustomSchedule.doctor_id == doctor_id,
                    CustomSchedule.schedule_date == suspension_date,
                    CustomSchedule.status == 1
                )
            ).order_by(CustomSchedule.start_time)
        )
        custom_schedules = custom_result.scalars().all()
        
        for s in custom_schedules:
            time_slot = f"{s.start_time.strftime('%H:%M')}-{s.end_time.strftime('%H:%M')}"
            schedules.append(AvailableScheduleForSuspension(
                schedule_id=s.id,
                time_slot=time_slot,
                schedule_type="custom",
                booked_count=s.booked_count,
                max_patients=s.max_patients
            ))
        
        return schedules
    
    async def check_suspension(
        self,
        doctor_id: str,
        suspension_date: date,
        time_slot: Optional[str] = None
    ) -> Optional[ScheduleSuspension]:
        """检查指定时间是否已停诊"""
        result = await self.db.execute(
            select(ScheduleSuspension).where(
                and_(
                    ScheduleSuspension.doctor_id == doctor_id,
                    ScheduleSuspension.suspension_date == suspension_date,
                    ScheduleSuspension.status == 1
                )
            )
        )
        suspensions = result.scalars().all()
        
        for s in suspensions:
            # 如果没有指定时段，说明全天停诊
            if s.time_slots is None:
                return s
            
            # 如果指定了时段，检查是否匹配
            if time_slot:
                try:
                    time_slots_list = json.loads(s.time_slots)
                    if time_slot in time_slots_list:
                        return s
                except:
                    pass
        
        return None
