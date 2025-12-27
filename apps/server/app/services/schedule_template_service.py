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
from app.utils.schedule_utils import (
    get_month_week,
    get_year_week,
    should_generate_schedule,
    get_time_slot_from_time,
    split_time_range,
)


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
        from app.services.schedule_service import ScheduleService
        
        schedule_service = ScheduleService(self.db)
        created_count = 0
        
        for template_id in data.template_ids:
            # 使用内部方法，不自动commit
            count = await schedule_service._generate_from_template_internal(
                template_id=template_id,
                start_date=data.start_date,
                end_date=data.end_date,
                check_rest_day=True,
                auto_commit=False
            )
            created_count += count
        
        # 统一提交
        await self.db.commit()
        return created_count
    
    async def batch_add_schedules(self, data: ScheduleBatchAddRequest) -> int:
        """
        批量添加排班（不依赖模板）
        @deprecated 此方法已废弃，请使用 ScheduleService 的相关方法
        """
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
