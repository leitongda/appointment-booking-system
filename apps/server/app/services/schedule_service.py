from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload, joinedload
from typing import Optional, List, Tuple
from datetime import date, timedelta, time
import uuid
import logging

from app.models.schedule import Schedule
from app.models.doctor import Doctor
from app.models.rest_day import RestDay
from app.models.appointment import Appointment
from app.schemas.schedule import ScheduleCreate, ScheduleBatchCreate, ScheduleUpdate
from app.utils.schedule_utils import get_time_slot_from_time
from app.utils.audit import set_create_audit, set_update_audit
from app.services.message_service import MessageService

logger = logging.getLogger(__name__)

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
        """获取可预约排班（会过滤休息日）"""
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
        schedules = list(result.scalars().all())
        
        # 过滤休息日的排班（自定义排班不受休息日影响）
        filtered_schedules = []
        for schedule in schedules:
            # 自定义排班（template_id=None）优先级高于休息日设置，不过滤
            if schedule.template_id is None:
                filtered_schedules.append(schedule)
                continue
            
            # 普通排班需要检查休息日
            is_rest_day = await self._check_rest_day(
                schedule.schedule_date, 
                schedule.store_id, 
                doctor_id
            )
            if not is_rest_day:
                filtered_schedules.append(schedule)
        
        # 同时段去重：按 (日期, 开始时间, 结束时间) 分组，优先保留自定义排班
        schedule_map = {}
        for schedule in filtered_schedules:
            key = (schedule.schedule_date, schedule.start_time, schedule.end_time)
            if key not in schedule_map:
                schedule_map[key] = schedule
            elif schedule.template_id is None:
                # 自定义排班优先级更高，覆盖已有的普通排班
                schedule_map[key] = schedule
        
        # 按日期和时间排序返回
        available_schedules = sorted(
            schedule_map.values(), 
            key=lambda s: (s.schedule_date, s.start_time or s.time_slot)
        )
        
        return available_schedules
    
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
        existing_schedule = existing.scalar_one_or_none()
        
        if existing_schedule:
            # 优先级处理：停诊 > 自定义排班 > 普通排班
            is_new_custom = data.template_id is None
            is_existing_normal = existing_schedule.template_id is not None
            is_existing_suspended = existing_schedule.status == 0
            
            # 如果已存在的排班已停诊，任何新排班都不能覆盖（停诊优先级最高）
            if is_existing_suspended:
                raise ValueError("该时段已停诊，无法创建排班")
            
            if is_new_custom and is_existing_normal:
                # 自定义排班覆盖普通排班（仅限未停诊的）
                if existing_schedule.booked_slots > 0:
                    raise ValueError("该时段普通排班已有预约，无法覆盖")
                # 删除已存在的普通排班
                await self.db.delete(existing_schedule)
                await self.db.flush()  # 确保删除生效
            else:
                # 其他情况（自定义排班覆盖自定义排班、普通排班覆盖任何排班）都不允许
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
        
        # 发送排班创建通知给医生（仅自定义排班，即 template_id 为 None）
        if data.template_id is None:
            await self._send_schedule_notification_to_doctor(
                doctor_id=data.doctor_id,
                title="新增排班通知",
                content=f"您有新增排班：{data.schedule_date.strftime('%Y年%m月%d日')}，请及时查看。",
                schedule_id=schedule.id
            )
        
        return schedule
    
    async def batch_create(self, data: ScheduleBatchCreate, operator_id: Optional[str] = None) -> int:
        """
        批量创建排班
        
        Args:
            data: 批量创建数据
            operator_id: 操作人ID（用于审计）
            
        Returns:
            成功创建的数量
            
        Raises:
            ValueError: 医生不存在
        """
        # 先获取医生信息并验证存在性
        doctor_result = await self.db.execute(
            select(Doctor).where(Doctor.id == data.doctor_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor:
            raise ValueError("医生不存在")
        
        store_id = doctor.store_id
        
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
                            appointment_type="normal",
                            status=1
                        )
                        set_create_audit(schedule, operator_id)
                        self.db.add(schedule)
                        created_count += 1
            
            current_date += timedelta(days=1)
        
        await self.db.commit()
        
        # 发送批量排班创建通知给医生
        if created_count > 0:
            await self._send_schedule_notification_to_doctor(
                doctor_id=data.doctor_id,
                title="批量排班通知",
                content=f"您有 {created_count} 个新排班已创建（{data.start_date.strftime('%Y年%m月%d日')} 至 {data.end_date.strftime('%Y年%m月%d日')}），请及时查看。",
                schedule_id=None
            )
        
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
            select(Schedule)
            .options(selectinload(Schedule.doctor))
            .where(
                and_(
                    Schedule.id.in_(schedule_ids),
                    Schedule.status == 1  # 只停诊正常状态的排班
                )
            )
        )
        schedules = result.scalars().all()
        
        affected_count = 0
        affected_schedule_ids = []
        for schedule in schedules:
            schedule.status = 0  # 设置为停诊状态
            affected_count += 1
            affected_schedule_ids.append(schedule.id)
        
        if affected_count > 0:
            await self.db.commit()
            
            # 发送停诊通知给受影响的患者
            await self._send_batch_suspend_notifications(schedules, reason)
        
        return affected_count
    
    async def _send_batch_suspend_notifications(
        self,
        schedules: List[Schedule],
        reason: Optional[str] = None
    ):
        """发送批量停诊通知给受影响的患者和医生"""
        try:
            schedule_ids = [s.id for s in schedules]
            if not schedule_ids:
                return
            
            message_service = MessageService(self.db)
            
            # 1. 给医生发送停诊通知
            doctor_schedules = {}  # doctor_id -> list of schedules
            for schedule in schedules:
                if schedule.doctor_id not in doctor_schedules:
                    doctor_schedules[schedule.doctor_id] = []
                doctor_schedules[schedule.doctor_id].append(schedule)
            
            for doctor_id, doc_schedules in doctor_schedules.items():
                try:
                    dates = sorted(set(s.schedule_date for s in doc_schedules))
                    if len(dates) == 1:
                        date_str = dates[0].strftime('%Y年%m月%d日')
                    else:
                        date_str = f"{dates[0].strftime('%Y年%m月%d日')} 至 {dates[-1].strftime('%Y年%m月%d日')}"
                    
                    reason_text = f"（原因：{reason}）" if reason else ""
                    
                    await message_service.send_schedule_notification(
                        doctor_id=doctor_id,
                        title="排班停诊通知",
                        content=f"您的 {len(doc_schedules)} 个排班已被停诊（{date_str}）{reason_text}。如有疑问请联系管理员。",
                        schedule_id=doc_schedules[0].id if len(doc_schedules) == 1 else None
                    )
                except Exception as e:
                    logger.warning(f"医生停诊通知发送失败 (doctor_id={doctor_id}): {e}")
            
            # 2. 给患者发送停诊通知
            appointments_result = await self.db.execute(
                select(Appointment)
                .options(selectinload(Appointment.schedule))
                .where(
                    and_(
                        Appointment.schedule_id.in_(schedule_ids),
                        Appointment.status.in_([1, 2])  # 1=已预约, 2=已签到
                    )
                )
            )
            appointments = appointments_result.scalars().all()
            
            if not appointments:
                return
            
            # 构建 schedule_id 到 schedule 的映射
            schedule_map = {s.id: s for s in schedules}
            
            for appointment in appointments:
                try:
                    schedule = schedule_map.get(appointment.schedule_id)
                    if not schedule:
                        continue
                    
                    doctor_name = schedule.doctor.name if schedule.doctor else appointment.doctor_name or "医生"
                    schedule_date_str = schedule.schedule_date.strftime('%Y年%m月%d日')
                    
                    # 格式化时段显示
                    time_slot_display = {
                        'AM': '上午',
                        'PM': '下午',
                        'morning': '上午',
                        'afternoon': '下午',
                        'evening': '晚间',
                        'NIGHT': '夜间',
                    }.get(schedule.time_slot, schedule.time_slot or "")
                    
                    reason_text = f"原因：{reason}" if reason else "请重新预约其他时间"
                    
                    await message_service.send_stop_clinic_notification(
                        user_id=appointment.user_id,
                        user_type="patient",
                        title="停诊通知",
                        content=f"您预约的{doctor_name}医生（{schedule_date_str} {time_slot_display}）因故停诊。{reason_text}，给您带来不便敬请谅解。",
                        appointment_id=appointment.id
                    )
                except Exception as e:
                    logger.warning(f"停诊通知发送失败 (appointment_id={appointment.id}): {e}")
                    
        except Exception as e:
            # 消息通知失败不影响停诊操作
            logger.warning(f"批量停诊通知发送失败: {e}")
    
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
    
    async def delete(self, schedule_id: str) -> bool:
        """
        删除单个排班
        
        Args:
            schedule_id: 排班ID
            
        Returns:
            是否删除成功
            
        Raises:
            ValueError: 排班不存在或有预约记录无法删除
        """
        from app.models.appointment import Appointment
        
        schedule = await self.get_by_id(schedule_id)
        if not schedule:
            raise ValueError("排班不存在")
        
        # 检查是否有预约记录
        appointments_result = await self.db.execute(
            select(Appointment.id).where(
                Appointment.schedule_id == schedule_id
            ).limit(1)
        )
        if appointments_result.scalar_one_or_none():
            raise ValueError("该排班已有预约记录，无法删除")
        
        await self.db.delete(schedule)
        await self.db.commit()
        return True
    
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
        """
        检查指定日期是否为休息日
        
        Args:
            check_date: 要检查的日期
            store_id: 门店ID（可选）
            doctor_id: 医生ID（可选）
            
        Returns:
            True 表示是休息日，False 表示不是
        """
        import json
        import logging
        
        logger = logging.getLogger(__name__)
        
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
                # 如果没有指定医生ID，或者休息日配置为所有医生（doctor_ids 为 NULL）
                if not doctor_id or rd.doctor_ids is None:
                    return True
                # 检查医生是否在休息日列表中
                try:
                    doctor_ids_list = json.loads(rd.doctor_ids)
                    if doctor_id in doctor_ids_list:
                        return True
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"解析休息日医生列表失败: rest_day_id={rd.id}, error={e}")
            
            return False
        except Exception as e:
            logger.error(f"检查休息日失败: date={check_date}, store_id={store_id}, error={e}")
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
    
    async def _send_schedule_notification_to_doctor(
        self,
        doctor_id: str,
        title: str,
        content: str,
        schedule_id: Optional[str] = None
    ):
        """发送排班相关通知给医生"""
        try:
            message_service = MessageService(self.db)
            await message_service.send_schedule_notification(
                doctor_id=doctor_id,
                title=title,
                content=content,
                schedule_id=schedule_id
            )
        except Exception as e:
            # 消息通知失败不影响主流程
            logger.warning(f"排班通知发送失败 (doctor_id={doctor_id}): {e}")

