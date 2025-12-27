from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
from datetime import date, timedelta, time
import uuid
import json

from app.models.schedule_template import ScheduleTemplate
from app.models.schedule import Schedule
from app.schemas.schedule_template import (
    ScheduleTemplateCreate,
    ScheduleTemplateUpdate,
    ScheduleGenerateRequest,
    ScheduleBatchAddRequest,
)


def get_month_week(d: date) -> int:
    """获取日期在月内的周数
    1-7号为第1周，8-14号为第2周，15-21号为第3周，22-28号为第4周，29号-月底为第5周
    """
    return (d.day - 1) // 7 + 1


def get_year_week(d: date) -> int:
    """获取日期在年内的周数"""
    return d.isocalendar()[1]


def should_generate_schedule(d: date, schedule_mode: str) -> bool:
    """判断指定日期是否应该生成排班"""
    month_week = get_month_week(d)
    year_week = get_year_week(d)
    
    if schedule_mode == "weekly":
        return True
    elif schedule_mode == "month_week_1":
        return month_week == 1
    elif schedule_mode == "month_week_2":
        return month_week == 2
    elif schedule_mode == "month_week_3":
        return month_week == 3
    elif schedule_mode == "month_week_4":
        return month_week == 4
    elif schedule_mode == "month_week_5":
        return month_week == 5
    elif schedule_mode == "year_odd_week":
        return year_week % 2 == 1
    elif schedule_mode == "year_even_week":
        return year_week % 2 == 0
    return False


def get_time_slot_from_time(start_time) -> str:
    """根据开始时间判断时段"""
    hour = start_time.hour
    if hour < 12:
        return "morning"
    elif hour < 18:
        return "afternoon"
    else:
        return "evening"


def split_time_range(start: time, end: time, count: int) -> List[Tuple[time, time]]:
    """将时间区间均分为多个班次
    
    Args:
        start: 开始时间
        end: 结束时间
        count: 班次数量
    
    Returns:
        班次时间列表，如 [(09:00, 11:00), (11:00, 13:00), ...]
    """
    if count <= 0:
        return [(start, end)]
    
    # 计算总分钟数
    start_minutes = start.hour * 60 + start.minute
    end_minutes = end.hour * 60 + end.minute
    total_minutes = end_minutes - start_minutes
    
    if total_minutes <= 0:
        return [(start, end)]
    
    # 每个班次的分钟数
    slot_minutes = total_minutes // count
    
    slots = []
    current_start = start
    
    for i in range(count):
        # 计算当前班次的结束时间
        current_start_minutes = current_start.hour * 60 + current_start.minute
        current_end_minutes = current_start_minutes + slot_minutes
        
        # 最后一个班次使用结束时间，确保覆盖完整区间
        if i == count - 1:
            current_end = end
        else:
            current_end_hour = current_end_minutes // 60
            current_end_minute = current_end_minutes % 60
            current_end = time(current_end_hour, current_end_minute)
        
        slots.append((current_start, current_end))
        current_start = current_end
    
    return slots


class ScheduleTemplateService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, template_id: str) -> Optional[ScheduleTemplate]:
        """获取模板详情"""
        result = await self.db.execute(
            select(ScheduleTemplate)
            .options(
                selectinload(ScheduleTemplate.store),
                selectinload(ScheduleTemplate.doctor),
                selectinload(ScheduleTemplate.department)
            )
            .where(ScheduleTemplate.id == template_id)
        )
        return result.scalar_one_or_none()
    
    async def get_list(
        self,
        store_id: Optional[str] = None,
        doctor_id: Optional[str] = None,
        department_id: Optional[str] = None,
        status: Optional[int] = None,
        page: int = 1,
        page_size: int = 10
    ) -> tuple[List[ScheduleTemplate], int]:
        """获取模板列表"""
        query = select(ScheduleTemplate).options(
            selectinload(ScheduleTemplate.store),
            selectinload(ScheduleTemplate.doctor),
            selectinload(ScheduleTemplate.department)
        )
        count_query = select(func.count(ScheduleTemplate.id))
        
        if store_id:
            query = query.where(ScheduleTemplate.store_id == store_id)
            count_query = count_query.where(ScheduleTemplate.store_id == store_id)
        if doctor_id:
            query = query.where(ScheduleTemplate.doctor_id == doctor_id)
            count_query = count_query.where(ScheduleTemplate.doctor_id == doctor_id)
        if department_id:
            query = query.where(ScheduleTemplate.department_id == department_id)
            count_query = count_query.where(ScheduleTemplate.department_id == department_id)
        if status is not None:
            query = query.where(ScheduleTemplate.status == status)
            count_query = count_query.where(ScheduleTemplate.status == status)
        
        query = query.order_by(ScheduleTemplate.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)
        
        return list(result.scalars().all()), count_result.scalar() or 0
    
    async def create(self, data: ScheduleTemplateCreate) -> ScheduleTemplate:
        """创建排班模板"""
        template = ScheduleTemplate(
            id=str(uuid.uuid4()),
            name=data.name,
            store_id=data.store_id,
            doctor_id=data.doctor_id,
            department_id=data.department_id,
            weekdays=json.dumps(data.weekdays),
            appointment_type=data.appointment_type.value,
            start_time=data.start_time,
            end_time=data.end_time,
            slot_count=data.slot_count,
            slot_capacity=data.slot_capacity,
            schedule_mode=data.schedule_mode.value,
            status=1
        )
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template
    
    async def update(self, template_id: str, data: ScheduleTemplateUpdate) -> Optional[ScheduleTemplate]:
        """更新排班模板"""
        template = await self.get_by_id(template_id)
        if not template:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        
        # 处理枚举类型
        if 'appointment_type' in update_data and update_data['appointment_type']:
            update_data['appointment_type'] = update_data['appointment_type'].value
        if 'schedule_mode' in update_data and update_data['schedule_mode']:
            update_data['schedule_mode'] = update_data['schedule_mode'].value
        
        # 处理 weekdays 数组
        if 'weekdays' in update_data and update_data['weekdays'] is not None:
            update_data['weekdays'] = json.dumps(update_data['weekdays'])
        
        for field, value in update_data.items():
            setattr(template, field, value)
        
        await self.db.commit()
        await self.db.refresh(template)
        return template
    
    async def delete(self, template_id: str) -> bool:
        """删除排班模板"""
        template = await self.get_by_id(template_id)
        if not template:
            return False
        
        await self.db.delete(template)
        await self.db.commit()
        return True
    
    async def generate_schedules(self, data: ScheduleGenerateRequest) -> int:
        """根据模板批量生成排班"""
        created_count = 0
        
        for template_id in data.template_ids:
            template = await self.get_by_id(template_id)
            if not template or template.status != 1:
                continue
            
            # 获取星期列表
            weekdays = template.weekday_list
            
            # 均分时间生成多个班次
            time_slots = split_time_range(template.start_time, template.end_time, template.slot_count)
            
            current_date = data.start_date
            while current_date <= data.end_date:
                weekday = current_date.isoweekday()  # 1-7 代表周一到周日
                
                # 检查星期是否匹配（支持多选）
                if weekday in weekdays:
                    # 检查排班方式是否匹配
                    if should_generate_schedule(current_date, template.schedule_mode):
                        # 为每个班次生成排班记录
                        for slot_start, slot_end in time_slots:
                            time_slot = get_time_slot_from_time(slot_start)
                            # 检查是否已存在
                            existing = await self.db.execute(
                                select(Schedule).where(
                                    and_(
                                        Schedule.doctor_id == template.doctor_id,
                                        Schedule.schedule_date == current_date,
                                        Schedule.start_time == slot_start,
                                        Schedule.end_time == slot_end
                                    )
                                )
                            )
                            if not existing.scalar_one_or_none():
                                schedule = Schedule(
                                    id=str(uuid.uuid4()),
                                    doctor_id=template.doctor_id,
                                    store_id=template.store_id,
                                    template_id=template.id,
                                    schedule_date=current_date,
                                    time_slot=time_slot,
                                    start_time=slot_start,
                                    end_time=slot_end,
                                    total_slots=template.slot_capacity,
                                    appointment_type=template.appointment_type,
                                    booked_slots=0,
                                    status=1
                                )
                                self.db.add(schedule)
                                created_count += 1
                
                current_date += timedelta(days=1)
        
        await self.db.commit()
        return created_count
    
    async def batch_add_schedules(self, data: ScheduleBatchAddRequest) -> int:
        """批量添加排班（不依赖模板）"""
        created_count = 0
        
        # 均分时间生成多个班次
        time_slots = split_time_range(data.start_time, data.end_time, data.slot_count)
        
        current_date = data.start_date
        while current_date <= data.end_date:
            weekday = current_date.isoweekday()  # 1-7 代表周一到周日
            
            # 检查星期是否在选择列表中
            if weekday in data.weekdays:
                # 检查排班方式是否匹配
                if should_generate_schedule(current_date, data.schedule_mode.value):
                    # 为每个班次生成排班记录
                    for slot_start, slot_end in time_slots:
                        time_slot = get_time_slot_from_time(slot_start)
                        # 检查是否已存在
                        existing = await self.db.execute(
                            select(Schedule).where(
                                and_(
                                    Schedule.doctor_id == data.doctor_id,
                                    Schedule.schedule_date == current_date,
                                    Schedule.start_time == slot_start,
                                    Schedule.end_time == slot_end
                                )
                            )
                        )
                        if not existing.scalar_one_or_none():
                            schedule = Schedule(
                                id=str(uuid.uuid4()),
                                doctor_id=data.doctor_id,
                                store_id=data.store_id,
                                schedule_date=current_date,
                                time_slot=time_slot,
                                start_time=slot_start,
                                end_time=slot_end,
                                total_slots=data.slot_capacity,
                                appointment_type=data.appointment_type.value,
                                booked_slots=0,
                                status=1
                            )
                            self.db.add(schedule)
                            created_count += 1
            
            current_date += timedelta(days=1)
        
        await self.db.commit()
        return created_count
