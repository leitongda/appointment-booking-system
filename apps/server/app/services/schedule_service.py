from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload, joinedload
from typing import Optional, List, Tuple
from datetime import date, timedelta, time
import uuid

from app.models.schedule import Schedule
from app.models.doctor import Doctor
from app.models.rest_day import RestDay
from app.schemas.schedule import ScheduleCreate, ScheduleBatchCreate, ScheduleUpdate
from app.utils.schedule_utils import get_time_slot_from_time
from app.utils.audit import set_create_audit, set_update_audit

class ScheduleService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, schedule_id: str) -> Optional[Schedule]:
        result = await self.db.execute(
            select(Schedule).options(
                selectinload(Schedule.doctor).selectinload(Doctor.department)
            ).where(Schedule.id == schedule_id)
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
        query = select(Schedule).options(
            selectinload(Schedule.doctor).selectinload(Doctor.department)
        )
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
    
    async def create(self, data: ScheduleCreate, operator_id: Optional[str] = None) -> Schedule:
        # 如果没有提供 time_slot，根据 start_time 自动计算
        time_slot = data.time_slot
        if not time_slot and data.start_time:
            time_slot = get_time_slot_from_time(data.start_time)
        elif not time_slot:
            raise ValueError("必须提供 time_slot 或 start_time")
        
        # 检查是否已存在
        conditions = [
            Schedule.doctor_id == data.doctor_id,
            Schedule.schedule_date == data.schedule_date,
        ]
        if data.start_time and data.end_time:
            conditions.append(Schedule.start_time == data.start_time)
            conditions.append(Schedule.end_time == data.end_time)
        else:
            conditions.append(Schedule.time_slot == time_slot)
        
        existing = await self.db.execute(
            select(Schedule).where(and_(*conditions))
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
            template_id=data.template_id,
            schedule_date=data.schedule_date,
            time_slot=time_slot,
            start_time=data.start_time,
            end_time=data.end_time,
            total_slots=data.total_slots,
            booked_slots=0,
            appointment_type=data.appointment_type or "normal",
            status=data.status
        )
        set_create_audit(schedule, operator_id)
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
    
    async def update(self, schedule_id: str, data: ScheduleUpdate, operator_id: Optional[str] = None) -> Optional[Schedule]:
        schedule = await self.get_by_id(schedule_id)
        if not schedule:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        
        # 校验号源数不能小于已预约数
        if 'total_slots' in update_data and update_data['total_slots'] < schedule.booked_slots:
            raise ValueError("总号源数不能小于已预约数")
        
        for field, value in update_data.items():
            setattr(schedule, field, value)
        
        set_update_audit(schedule, operator_id)
        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule
    
    async def batch_suspend(self, schedule_ids: List[str], reason: Optional[str] = None) -> int:
        """
        批量停诊排班
        
        Args:
            schedule_ids: 排班ID列表
            reason: 停诊原因
        
        Returns:
            成功停诊的数量
        """
        if not schedule_ids:
            return 0
        
        # 查询符合条件的排班（只停诊正常状态的排班）
        result = await self.db.execute(
            select(Schedule).where(
                and_(
                    Schedule.id.in_(schedule_ids),
                    Schedule.status == 1  # 只停诊正常状态的排班
                )
            )
        )
        schedules = result.scalars().all()
        
        affected_count = 0
        for schedule in schedules:
            schedule.status = 0  # 设置为停诊状态
            affected_count += 1
        
        if affected_count > 0:
            await self.db.commit()
        
        return affected_count
    
    async def batch_resume(self, schedule_ids: List[str]) -> int:
        """
        批量恢复排班
        
        Args:
            schedule_ids: 排班ID列表
        
        Returns:
            成功恢复的数量
        """
        if not schedule_ids:
            return 0
        
        # 查询符合条件的排班（只恢复停诊状态的排班）
        result = await self.db.execute(
            select(Schedule).where(
                and_(
                    Schedule.id.in_(schedule_ids),
                    Schedule.status == 0  # 只恢复停诊状态的排班
                )
            )
        )
        schedules = result.scalars().all()
        
        affected_count = 0
        for schedule in schedules:
            schedule.status = 1  # 设置为正常状态
            affected_count += 1
        
        if affected_count > 0:
            await self.db.commit()
        
        return affected_count
    
    async def batch_delete(self, schedule_ids: List[str]) -> int:
        """
        批量删除排班
        
        Args:
            schedule_ids: 排班ID列表
        
        Returns:
            成功删除的数量（不包括有预约的排班）
        """
        from app.models.appointment import Appointment
        
        if not schedule_ids:
            return 0
        
        # 查询哪些排班有关联的预约记录（包括所有状态的预约）
        # 注意：由于 schedule_id 是 NOT NULL 约束，删除排班会导致外键约束失败
        # 因此只要有任何预约记录关联到该排班，就不能删除
        appointments_result = await self.db.execute(
            select(Appointment.schedule_id).where(
                Appointment.schedule_id.in_(schedule_ids)
            ).distinct()
        )
        schedule_ids_with_appointments = {row[0] for row in appointments_result.fetchall()}
        
        # 过滤出可以删除的排班ID（没有任何预约记录的排班）
        deletable_schedule_ids = [sid for sid in schedule_ids if sid not in schedule_ids_with_appointments]
        
        if not deletable_schedule_ids:
            return 0
        
        # 查询这些排班记录
        result = await self.db.execute(
            select(Schedule).where(Schedule.id.in_(deletable_schedule_ids))
        )
        schedules = result.scalars().all()
        
        affected_count = 0
        for schedule in schedules:
            await self.db.delete(schedule)
            affected_count += 1
        
        if affected_count > 0:
            await self.db.commit()
        
        return affected_count
    
    async def _check_rest_day(self, check_date: date, store_id: Optional[str] = None, doctor_id: Optional[str] = None) -> bool:
        """检查指定日期是否为休息日"""
        try:
            query = select(RestDay).where(
                and_(
                    RestDay.status == 1,
                    RestDay.start_date <= check_date,
                    RestDay.end_date >= check_date
                )
            )
            
            if store_id:
                query = query.where(RestDay.store_id == store_id)
            
            result = await self.db.execute(query)
            rest_days = result.scalars().all()
            
            for rd in rest_days:
                # 如果没有指定医生ID，或者休息日配置为所有医生
                if not doctor_id or rd.doctor_ids is None:
                    return True
                # 检查医生是否在休息日列表中
                try:
                    import json
                    doctor_ids_list = json.loads(rd.doctor_ids)
                    if doctor_id in doctor_ids_list:
                        return True
                except:
                    pass
            
            return False
        except Exception:
            return False
    
    async def _create_schedule_if_not_exists(
        self,
        doctor_id: str,
        store_id: Optional[str],
        schedule_date: date,
        start_time: Optional[time],
        end_time: Optional[time],
        time_slot: str,
        total_slots: int,
        appointment_type: str = "normal",
        template_id: Optional[str] = None,
        check_rest_day: bool = True,
        check_duplicate: bool = True
    ) -> Tuple[Optional[Schedule], bool]:
        """
        创建排班（如果不存在）
        
        Args:
            doctor_id: 医生ID
            store_id: 门店ID
            schedule_date: 排班日期
            start_time: 开始时间
            end_time: 结束时间
            time_slot: 时段
            total_slots: 总号源
            appointment_type: 预约类型
            template_id: 模板ID
            check_rest_day: 是否检查休息日
            check_duplicate: 是否检查重复
        
        Returns:
            (Schedule对象, 是否创建成功)
        """
        # 检查休息日
        if check_rest_day:
            if await self._check_rest_day(schedule_date, store_id, doctor_id):
                return None, False
        
        # 检查是否已存在
        if check_duplicate:
            conditions = [
                Schedule.doctor_id == doctor_id,
                Schedule.schedule_date == schedule_date,
            ]
            
            if start_time and end_time:
                conditions.append(Schedule.start_time == start_time)
                conditions.append(Schedule.end_time == end_time)
            else:
                conditions.append(Schedule.time_slot == time_slot)
            
            existing = await self.db.execute(
                select(Schedule).where(and_(*conditions))
            )
            if existing.scalar_one_or_none():
                return None, False
        
        # 如果没有传递 store_id，从医生信息中获取
        if not store_id:
            doctor_result = await self.db.execute(
                select(Doctor).where(Doctor.id == doctor_id)
            )
            doctor = doctor_result.scalar_one_or_none()
            if doctor:
                store_id = doctor.store_id
        
        # 创建排班
        schedule = Schedule(
            id=str(uuid.uuid4()),
            doctor_id=doctor_id,
            store_id=store_id,
            template_id=template_id,
            schedule_date=schedule_date,
            time_slot=time_slot,
            start_time=start_time,
            end_time=end_time,
            total_slots=total_slots,
            appointment_type=appointment_type,
            booked_slots=0,
            status=1
        )
        self.db.add(schedule)
        return schedule, True
    
    async def _generate_from_template_internal(
        self,
        template_id: str,
        start_date: date,
        end_date: date,
        check_rest_day: bool = True,
        auto_commit: bool = True
    ) -> int:
        """
        根据模板生成排班（内部方法）
        
        Args:
            template_id: 模板ID
            start_date: 开始日期
            end_date: 结束日期
            check_rest_day: 是否检查休息日
            auto_commit: 是否自动提交
        
        Returns:
            创建的排班数量
        """
        from app.models.schedule_template import ScheduleTemplate
        from app.utils.schedule_utils import split_time_range_with_breaks, should_generate_schedule
        
        # 获取模板
        template_result = await self.db.execute(
            select(ScheduleTemplate).where(ScheduleTemplate.id == template_id)
        )
        template = template_result.scalar_one_or_none()
        if not template or template.status != 1:
            return 0
        
        # 获取星期列表
        weekdays = template.weekday_list
        if not weekdays:
            return 0
        
        # 获取排除时间列表
        break_times = template.break_times_list or []
        
        # 均分时间生成多个班次（考虑排除时间）
        time_slots = split_time_range_with_breaks(template.start_time, template.end_time, template.slot_count, break_times)
        
        created_count = 0
        current_date = start_date
        
        while current_date <= end_date:
            weekday = current_date.isoweekday()  # 1-7 代表周一到周日
            
            # 检查星期是否匹配（支持多选）
            if weekday in weekdays:
                # 检查排班方式是否匹配
                if should_generate_schedule(current_date, template.schedule_mode):
                    # 为每个班次生成排班记录
                    for slot_start, slot_end in time_slots:
                        time_slot = get_time_slot_from_time(slot_start)
                        schedule, created = await self._create_schedule_if_not_exists(
                            doctor_id=template.doctor_id,
                            store_id=template.store_id,
                            schedule_date=current_date,
                            start_time=slot_start,
                            end_time=slot_end,
                            time_slot=time_slot,
                            total_slots=template.slot_capacity,
                            appointment_type=template.appointment_type,
                            template_id=template.id,
                            check_rest_day=check_rest_day,
                            check_duplicate=True
                        )
                        if created:
                            created_count += 1
            
            current_date += timedelta(days=1)
        
        if auto_commit:
            await self.db.commit()
        return created_count
    
    async def generate_from_template(
        self,
        template_id: str,
        start_date: date,
        end_date: date,
        check_rest_day: bool = True
    ) -> int:
        """
        根据模板生成排班
        
        Args:
            template_id: 模板ID
            start_date: 开始日期
            end_date: 结束日期
            check_rest_day: 是否检查休息日
        
        Returns:
            创建的排班数量
        """
        return await self._generate_from_template_internal(
            template_id=template_id,
            start_date=start_date,
            end_date=end_date,
            check_rest_day=check_rest_day,
            auto_commit=True
        )

