from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
from datetime import date, timedelta, time, datetime
import uuid
import json

from app.models.schedule_template import ScheduleTemplate
from app.models.schedule import Schedule
from app.models.schedule_generation_log import ScheduleGenerationLog
from app.schemas.schedule_template import (
    ScheduleTemplateCreate,
    ScheduleTemplateUpdate,
    ScheduleGenerateRequest,
    ScheduleBatchAddRequest,
)
from app.schemas.schedule_generation_log import (
    BatchOperateRequest,
    CheckGeneratedResponse,
)
from app.utils.schedule_utils import (
    get_month_week,
    get_year_week,
    should_generate_schedule,
    get_time_slot_from_time,
    split_time_range,
    split_time_range_with_breaks,
)
from app.utils.audit import set_create_audit, set_update_audit


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
        from app.models.store import Store
        from app.models.doctor import Doctor
        from app.models.department import Department
        import logging
        
        logger = logging.getLogger(__name__)
        
        # 验证必填字段
        if not data.name or not data.name.strip():
            raise ValueError("模板名称不能为空")
        if not data.store_id:
            raise ValueError("门店ID不能为空")
        if not data.doctor_id:
            raise ValueError("医生ID不能为空")
        if not data.department_id:
            raise ValueError("科室ID不能为空")
        if not data.weekdays or len(data.weekdays) == 0:
            raise ValueError("星期数组不能为空")
        if not data.start_time:
            raise ValueError("开始时间不能为空")
        if not data.end_time:
            raise ValueError("结束时间不能为空")
        
        # 验证门店是否存在
        store_result = await self.db.execute(
            select(Store).where(Store.id == data.store_id)
        )
        if not store_result.scalar_one_or_none():
            raise ValueError("门店不存在")
        
        # 验证医生是否存在
        doctor_result = await self.db.execute(
            select(Doctor).where(Doctor.id == data.doctor_id)
        )
        if not doctor_result.scalar_one_or_none():
            raise ValueError("医生不存在")
        
        # 验证科室是否存在
        department_result = await self.db.execute(
            select(Department).where(Department.id == data.department_id)
        )
        if not department_result.scalar_one_or_none():
            raise ValueError("科室不存在")
        
        # 确保时间对象正确
        start_time = data.start_time
        end_time = data.end_time
        
        # 如果是字符串，尝试解析
        if isinstance(start_time, str):
            try:
                from datetime import datetime
                start_time = datetime.strptime(start_time, "%H:%M").time()
            except ValueError:
                try:
                    start_time = datetime.strptime(start_time, "%H:%M:%S").time()
                except ValueError:
                    raise ValueError(f"开始时间格式错误: {start_time}")
        
        if isinstance(end_time, str):
            try:
                from datetime import datetime
                end_time = datetime.strptime(end_time, "%H:%M").time()
            except ValueError:
                try:
                    end_time = datetime.strptime(end_time, "%H:%M:%S").time()
                except ValueError:
                    raise ValueError(f"结束时间格式错误: {end_time}")
        
        # 处理 break_times
        break_times_json = None
        if data.break_times:
            break_times_list = []
            for bt in data.break_times:
                bt_dict = {
                    "startTime": bt.start_time.strftime("%H:%M") if hasattr(bt.start_time, 'strftime') else str(bt.start_time),
                    "endTime": bt.end_time.strftime("%H:%M") if hasattr(bt.end_time, 'strftime') else str(bt.end_time)
                }
                break_times_list.append(bt_dict)
            break_times_json = json.dumps(break_times_list)
        
        template = ScheduleTemplate(
            id=str(uuid.uuid4()),
            name=data.name,
            store_id=data.store_id,
            doctor_id=data.doctor_id,
            department_id=data.department_id,
            weekdays=json.dumps(data.weekdays),
            appointment_type=data.appointment_type.value if hasattr(data.appointment_type, 'value') else str(data.appointment_type),
            start_time=start_time,
            end_time=end_time,
            slot_count=data.slot_count or 1,
            slot_capacity=data.slot_capacity or 10,
            schedule_mode=data.schedule_mode.value if hasattr(data.schedule_mode, 'value') else str(data.schedule_mode),
            break_times=break_times_json,
            status=1
        )
        set_create_audit(template, data.operator_id if hasattr(data, 'operator_id') else None)
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template
    
    async def update(self, template_id: str, data: ScheduleTemplateUpdate, operator_id: Optional[str] = None) -> Optional[ScheduleTemplate]:
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
        
        # 处理 break_times 数组
        if 'break_times' in update_data:
            if update_data['break_times'] is not None:
                break_times_list = []
                for bt in update_data['break_times']:
                    if hasattr(bt, 'start_time'):
                        # bt 是 BreakTime 对象
                        bt_dict = {
                            "startTime": bt.start_time.strftime("%H:%M") if hasattr(bt.start_time, 'strftime') else str(bt.start_time),
                            "endTime": bt.end_time.strftime("%H:%M") if hasattr(bt.end_time, 'strftime') else str(bt.end_time)
                        }
                    elif isinstance(bt, dict):
                        # bt 是字典（从 model_dump 返回），需要处理其中可能的 time 对象
                        start_time = bt.get('start_time') or bt.get('startTime')
                        end_time = bt.get('end_time') or bt.get('endTime')
                        bt_dict = {
                            "startTime": start_time.strftime("%H:%M") if hasattr(start_time, 'strftime') else str(start_time),
                            "endTime": end_time.strftime("%H:%M") if hasattr(end_time, 'strftime') else str(end_time)
                        }
                    else:
                        bt_dict = bt
                    break_times_list.append(bt_dict)
                update_data['break_times'] = json.dumps(break_times_list)
            else:
                update_data['break_times'] = None
        
        for field, value in update_data.items():
            setattr(template, field, value)
        
        set_update_audit(template, operator_id)
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
        now = datetime.now()
        
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
            
            # 如果有生成排班，更新模板的 last_generated_at
            if count > 0:
                template = await self.get_by_id(template_id)
                if template:
                    template.last_generated_at = now
        
        # 统一提交
        await self.db.commit()
        return created_count
    
    async def batch_add_schedules(self, data: ScheduleBatchAddRequest) -> int:
        """
        批量添加排班
        会先自动创建一个排班规则模板，然后基于模板生成排班
        这样可以通过批量停诊/删除功能管理这些排班
        """
        now = datetime.now()
        
        # 处理 break_times
        break_times_json = None
        break_times_list = []
        if data.break_times:
            for bt in data.break_times:
                bt_dict = {
                    "startTime": bt.start_time.strftime("%H:%M") if hasattr(bt.start_time, 'strftime') else str(bt.start_time),
                    "endTime": bt.end_time.strftime("%H:%M") if hasattr(bt.end_time, 'strftime') else str(bt.end_time)
                }
                break_times_list.append(bt_dict)
            break_times_json = json.dumps(break_times_list)
        
        # 1. 先创建一个排班规则模板
        template_name = f"批量添加-{data.start_date}至{data.end_date}"
        template = ScheduleTemplate(
            id=str(uuid.uuid4()),
            name=template_name,
            store_id=data.store_id,
            doctor_id=data.doctor_id,
            department_id=data.department_id,
            weekdays=json.dumps(data.weekdays) if data.weekdays else "[]",
            appointment_type=data.appointment_type.value,
            start_time=data.start_time,
            end_time=data.end_time,
            slot_count=data.slot_count,
            slot_capacity=data.slot_capacity,
            schedule_mode=data.schedule_mode.value,
            break_times=break_times_json,
            status=1
        )
        self.db.add(template)
        await self.db.flush()  # 确保 template.id 已生成
        
        template_id = template.id
        created_count = 0
        
        # 2. 均分时间生成多个班次（考虑排除时间）
        time_slots = split_time_range_with_breaks(data.start_time, data.end_time, data.slot_count, break_times_list)
        
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
                                template_id=template_id,  # 关联模板ID
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
        
        # 如果有生成排班，更新模板的 last_generated_at
        if created_count > 0:
            template.last_generated_at = now
        
        await self.db.commit()
        return created_count
    
    async def check_generated(
        self,
        template_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> CheckGeneratedResponse:
        """检查规则是否已生成过排班"""
        # 查询该模板生成的所有排班
        query = select(Schedule).where(Schedule.template_id == template_id)
        
        if start_date:
            query = query.where(Schedule.schedule_date >= start_date)
        if end_date:
            query = query.where(Schedule.schedule_date <= end_date)
        
        result = await self.db.execute(query)
        schedules = result.scalars().all()
        
        if not schedules:
            return CheckGeneratedResponse(
                has_generated=False,
                schedule_count=0,
                date_range_count=0
            )
        
        # 统计信息
        all_dates = [s.schedule_date for s in schedules]
        
        return CheckGeneratedResponse(
            has_generated=True,
            schedule_count=len(schedules),
            date_range_count=len(schedules),
            earliest_date=min(all_dates) if all_dates else None,
            latest_date=max(all_dates) if all_dates else None
        )
    
    async def batch_delete_schedules(
        self,
        template_id: str,
        operator_id: Optional[str] = None,
        operator_name: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        future_only: bool = True
    ) -> int:
        """批量删除规则生成的排班"""
        today = date.today()
        
        # 构建查询条件
        conditions = [Schedule.template_id == template_id]
        
        if future_only:
            conditions.append(Schedule.schedule_date >= today)
        if start_date:
            conditions.append(Schedule.schedule_date >= start_date)
        if end_date:
            conditions.append(Schedule.schedule_date <= end_date)
        
        # 只删除没有预约的排班
        conditions.append(Schedule.booked_slots == 0)
        
        # 先统计数量
        count_query = select(func.count(Schedule.id)).where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        affected_count = count_result.scalar() or 0
        
        if affected_count > 0:
            # 删除排班
            delete_stmt = delete(Schedule).where(and_(*conditions))
            await self.db.execute(delete_stmt)
            
            # 记录日志
            log = ScheduleGenerationLog(
                id=str(uuid.uuid4()),
                template_id=template_id,
                operator_id=operator_id,
                operator_name=operator_name,
                action_type="delete",
                start_date=start_date or (today if future_only else None),
                end_date=end_date,
                affected_count=affected_count,
                remark=f"批量删除排班，删除 {affected_count} 条记录"
            )
            self.db.add(log)
            await self.db.commit()
        
        return affected_count
    
    async def batch_suspend_schedules(
        self,
        template_id: str,
        operator_id: Optional[str] = None,
        operator_name: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        future_only: bool = True
    ) -> int:
        """批量停诊规则生成的排班"""
        today = date.today()
        
        # 构建查询条件
        conditions = [
            Schedule.template_id == template_id,
            Schedule.status == 1  # 只停诊正常状态的排班
        ]
        
        if future_only:
            conditions.append(Schedule.schedule_date >= today)
        if start_date:
            conditions.append(Schedule.schedule_date >= start_date)
        if end_date:
            conditions.append(Schedule.schedule_date <= end_date)
        
        # 查询符合条件的排班
        query = select(Schedule).where(and_(*conditions))
        result = await self.db.execute(query)
        schedules = result.scalars().all()
        
        affected_count = 0
        for schedule in schedules:
            schedule.status = 0  # 设置为停诊状态
            affected_count += 1
        
        if affected_count > 0:
            # 记录日志
            log = ScheduleGenerationLog(
                id=str(uuid.uuid4()),
                template_id=template_id,
                operator_id=operator_id,
                operator_name=operator_name,
                action_type="suspend",
                start_date=start_date or (today if future_only else None),
                end_date=end_date,
                affected_count=affected_count,
                remark=f"批量停诊，停诊 {affected_count} 条记录"
            )
            self.db.add(log)
            await self.db.commit()
        
        return affected_count
    
    async def get_generation_logs(
        self,
        template_id: str,
        page: int = 1,
        page_size: int = 10
    ) -> Tuple[List[ScheduleGenerationLog], int]:
        """获取生成历史记录"""
        query = select(ScheduleGenerationLog).where(
            ScheduleGenerationLog.template_id == template_id
        ).order_by(ScheduleGenerationLog.created_at.desc())
        
        count_query = select(func.count(ScheduleGenerationLog.id)).where(
            ScheduleGenerationLog.template_id == template_id
        )
        
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)
        
        return list(result.scalars().all()), count_result.scalar() or 0
    
    async def log_generation(
        self,
        template_id: str,
        action_type: str,
        affected_count: int,
        operator_id: Optional[str] = None,
        operator_name: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        remark: Optional[str] = None
    ) -> ScheduleGenerationLog:
        """记录生成日志"""
        log = ScheduleGenerationLog(
            id=str(uuid.uuid4()),
            template_id=template_id,
            operator_id=operator_id,
            operator_name=operator_name,
            action_type=action_type,
            start_date=start_date,
            end_date=end_date,
            affected_count=affected_count,
            remark=remark
        )
        self.db.add(log)
        await self.db.commit()
        return log
    
    async def generate_schedules_with_capacity(
        self,
        template_ids: List[str],
        start_date: date,
        end_date: date,
        capacity_overrides: dict = None
    ) -> int:
        """根据模板批量生成排班，支持自定义班次容量
        
        Args:
            template_ids: 模板ID列表
            start_date: 开始日期
            end_date: 结束日期
            capacity_overrides: 容量覆盖字典，key为(日期, 开始时间, 结束时间)元组
        """
        created_count = 0
        now = datetime.now()
        
        for template_id in template_ids:
            template = await self.get_by_id(template_id)
            if not template or template.status != 1:
                continue
            
            # 获取星期列表
            weekdays = template.weekday_list
            if not weekdays:
                continue
            
            # 获取排除时间列表
            break_times = template.break_times_list or []
            
            # 均分时间生成多个班次（考虑排除时间）
            time_slots = split_time_range_with_breaks(
                template.start_time,
                template.end_time,
                template.slot_count,
                break_times
            )
            
            current_date = start_date
            while current_date <= end_date:
                weekday = current_date.isoweekday()
                
                if weekday in weekdays:
                    if should_generate_schedule(current_date, template.schedule_mode):
                        for slot_start, slot_end in time_slots:
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
                                time_slot = get_time_slot_from_time(slot_start)
                                
                                # 检查是否有自定义容量
                                capacity = template.slot_capacity
                                if capacity_overrides:
                                    key = (
                                        current_date.isoformat(),
                                        slot_start.strftime("%H:%M"),
                                        slot_end.strftime("%H:%M")
                                    )
                                    if key in capacity_overrides:
                                        capacity = capacity_overrides[key]
                                
                                schedule = Schedule(
                                    id=str(uuid.uuid4()),
                                    doctor_id=template.doctor_id,
                                    store_id=template.store_id,
                                    template_id=template.id,
                                    schedule_date=current_date,
                                    time_slot=time_slot,
                                    start_time=slot_start,
                                    end_time=slot_end,
                                    total_slots=capacity,
                                    appointment_type=template.appointment_type,
                                    booked_slots=0,
                                    status=1
                                )
                                self.db.add(schedule)
                                created_count += 1
                
                current_date += timedelta(days=1)
            
            # 更新模板的 last_generated_at
            if created_count > 0:
                template.last_generated_at = now
        
        await self.db.commit()
        return created_count
