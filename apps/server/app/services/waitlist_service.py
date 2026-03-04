"""
候补队列服务

处理候补队列的添加、移除、自动递补等逻辑
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, update
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.models.waitlist import WaitlistEntry
from app.models.schedule import Schedule
from app.models.appointment import Appointment
from app.models.rule_set import RuleCapacityPolicy
from app.models.rest_day import RestDay
from app.services.rule_engine_service import RuleEngineService
from app.services.appointment_service import AppointmentService
from app.utils.audit import set_create_audit, set_update_audit


class WaitlistService:
    """候补队列服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_to_waitlist(
        self,
        user_id: str,
        patient_id: str,
        schedule_id: str,
        symptom_description: Optional[str] = None,
        priority: int = 100,
        operator_id: Optional[str] = None
    ) -> WaitlistEntry:
        """添加到候补队列

        Args:
            user_id: 用户ID
            patient_id: 就诊人ID
            schedule_id: 排班ID
            symptom_description: 症状描述
            priority: 优先级（值越小优先级越高）
            operator_id: 操作人ID

        Returns:
            WaitlistEntry: 创建的候补记录

        Raises:
            ValueError: 如果候补队列已满或已存在
        """
        # 检查是否已在候补队列中
        existing = await self.db.execute(
            select(WaitlistEntry).where(
                and_(
                    WaitlistEntry.user_id == user_id,
                    WaitlistEntry.patient_id == patient_id,
                    WaitlistEntry.schedule_id == schedule_id,
                    WaitlistEntry.status == 'WAITING'
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError('您已在候补队列中，请勿重复添加')

        # 获取排班信息
        schedule_result = await self.db.execute(
            select(Schedule).where(Schedule.id == schedule_id)
        )
        schedule = schedule_result.scalar_one_or_none()
        if not schedule:
            raise ValueError('排班不存在')

        # 检查是否为休息日（自定义排班不受休息日影响）
        # 自定义排班（template_id=None）优先级高于休息日设置
        if schedule.template_id is not None:
            is_rest_day = await self._check_rest_day(
                schedule.schedule_date,
                schedule.store_id,
                schedule.doctor_id
            )
            if is_rest_day:
                raise ValueError('该日期为休息日，无法加入候补')

        # 获取容量策略以检查候补队列大小限制
        if schedule.shift_type_id:
            rule_engine = RuleEngineService(self.db)
            capacity_policy = await rule_engine.get_capacity_policy(schedule.shift_type_id)
            if capacity_policy and capacity_policy.waitlist_max_size > 0:
                # 检查当前候补队列大小
                count_result = await self.db.execute(
                    select(func.count(WaitlistEntry.id)).where(
                        and_(
                            WaitlistEntry.schedule_id == schedule_id,
                            WaitlistEntry.status == 'WAITING'
                        )
                    )
                )
                current_count = count_result.scalar() or 0
                if current_count >= capacity_policy.waitlist_max_size:
                    raise ValueError(f'候补队列已满（最多{capacity_policy.waitlist_max_size}人）')

        # 计算队列位置
        position_result = await self.db.execute(
            select(func.max(WaitlistEntry.position)).where(
                and_(
                    WaitlistEntry.schedule_id == schedule_id,
                    WaitlistEntry.status == 'WAITING'
                )
            )
        )
        max_position = position_result.scalar() or 0
        position = max_position + 1

        # 创建候补记录
        entry = WaitlistEntry(
            id=str(uuid.uuid4()),
            user_id=user_id,
            patient_id=patient_id,
            schedule_id=schedule_id,
            shift_type_id=schedule.shift_type_id,
            status='WAITING',
            position=position,
            priority=priority,
            symptom_description=symptom_description,
            operator_id=operator_id,
            operator_type='USER' if not operator_id or operator_id == user_id else 'ADMIN'
        )
        set_create_audit(entry, operator_id or user_id)

        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)

        return entry

    async def cancel_waitlist(
        self,
        entry_id: str,
        user_id: str,
        is_admin: bool = False,
        operator_id: Optional[str] = None
    ) -> Optional[WaitlistEntry]:
        """取消候补

        Args:
            entry_id: 候补记录ID
            user_id: 用户ID
            is_admin: 是否为管理员
            operator_id: 操作人ID

        Returns:
            WaitlistEntry or None
        """
        result = await self.db.execute(
            select(WaitlistEntry).where(WaitlistEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()

        if not entry:
            return None

        # 非管理员只能取消自己的候补
        if not is_admin and entry.user_id != user_id:
            return None

        # 只能取消等待中的候补
        if entry.status != 'WAITING':
            raise ValueError('只能取消等待中的候补')

        entry.status = 'CANCELLED'
        import pytz
        local_tz = pytz.timezone('Asia/Shanghai')
        entry.cancelled_at = datetime.now(local_tz)
        entry.operator_id = operator_id or user_id
        set_update_audit(entry, operator_id or user_id)

        # 重新计算队列位置
        await self._recalculate_positions(entry.schedule_id)

        await self.db.commit()
        await self.db.refresh(entry)

        return entry

    async def get_waitlist_position(
        self,
        schedule_id: str,
        user_id: str
    ) -> Optional[int]:
        """获取用户在候补队列中的位置

        Args:
            schedule_id: 排班ID
            user_id: 用户ID

        Returns:
            位置（从1开始），如果不在队列中返回 None
        """
        result = await self.db.execute(
            select(WaitlistEntry.position).where(
                and_(
                    WaitlistEntry.schedule_id == schedule_id,
                    WaitlistEntry.user_id == user_id,
                    WaitlistEntry.status == 'WAITING'
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_waitlist_for_schedule(
        self,
        schedule_id: str,
        status: str = 'WAITING'
    ) -> List[WaitlistEntry]:
        """获取排班的候补队列

        Args:
            schedule_id: 排班ID
            status: 状态筛选

        Returns:
            候补列表（按位置排序）
        """
        result = await self.db.execute(
            select(WaitlistEntry).where(
                and_(
                    WaitlistEntry.schedule_id == schedule_id,
                    WaitlistEntry.status == status
                )
            ).order_by(WaitlistEntry.position)
        )
        return list(result.scalars().all())

    async def promote_next(
        self,
        schedule_id: str,
        operator_id: Optional[str] = None
    ) -> Optional[Appointment]:
        """手动递补下一个候补用户

        Args:
            schedule_id: 排班ID
            operator_id: 操作人ID

        Returns:
            创建的预约，如果没有候补用户返回 None
        """
        # 获取队列中的第一个用户
        waitlist_result = await self.db.execute(
            select(WaitlistEntry).where(
                and_(
                    WaitlistEntry.schedule_id == schedule_id,
                    WaitlistEntry.status == 'WAITING'
                )
            ).order_by(WaitlistEntry.position)
            .limit(1)
        )
        entry = waitlist_result.scalar_one_or_none()

        if not entry:
            return None

        # 创建预约
        return await self._promote_to_appointment(entry, operator_id=operator_id or 'SYSTEM')

    async def auto_promote(
        self,
        schedule_id: str,
        reason: str = 'APPOINTMENT_CANCELLED'
    ) -> List[Appointment]:
        """自动递补候补用户

        当有号源释放时，自动递补候补队列中的用户

        Args:
            schedule_id: 排班ID
            reason: 触发原因

        Returns:
            创建的预约列表
        """
        # 获取排班信息
        schedule_result = await self.db.execute(
            select(Schedule).where(Schedule.id == schedule_id)
        )
        schedule = schedule_result.scalar_one_or_none()
        if not schedule:
            return []

        # 检查是否启用自动递补
        if schedule.shift_type_id:
            rule_engine = RuleEngineService(self.db)
            capacity_policy = await rule_engine.get_capacity_policy(schedule.shift_type_id)
            if not capacity_policy or not capacity_policy.waitlist_enabled:
                return []
            if capacity_policy.waitlist_promote_policy != 'AUTO':
                return []

        # 计算可递补数量（剩余容量）
        available_slots = schedule.total_slots - schedule.booked_slots
        if available_slots <= 0:
            return []

        # 获取候补队列
        waitlist_entries = await self.get_waitlist_for_schedule(schedule_id)
        promoted = []

        for entry in waitlist_entries[:available_slots]:
            try:
                appointment = await self._promote_to_appointment(
                    entry,
                    operator_id='SYSTEM',
                    auto_promote=True
                )
                if appointment:
                    promoted.append(appointment)
            except Exception as e:
                # 记录错误但继续处理下一个
                print(f'递补候补用户失败: {entry.id}, 错误: {e}')

        return promoted

    async def _promote_to_appointment(
        self,
        entry: WaitlistEntry,
        operator_id: Optional[str] = None,
        auto_promote: bool = False
    ) -> Optional[Appointment]:
        """将候补记录转为预约

        Args:
            entry: 候补记录
            operator_id: 操作人ID
            auto_promote: 是否为自动递补

        Returns:
            创建的预约

        Raises:
            ValueError: 如果创建预约失败
        """
        from app.schemas.appointment import AppointmentCreate
        import pytz

        local_tz = pytz.timezone('Asia/Shanghai')

        # 使用数据库事务确保原子性
        # 先标记候补状态为"处理中"，防止并发递补
        entry.status = 'PROCESSING'
        await self.db.flush()

        try:
            # 创建预约
            appointment_service = AppointmentService(self.db)
            appointment = await appointment_service.create(
                user_id=entry.user_id,
                data=AppointmentCreate(
                    schedule_id=entry.schedule_id,
                    patient_id=entry.patient_id,
                    symptom_description=entry.symptom_description
                ),
                operator_id=operator_id
            )

            # 预约创建成功，更新候补状态
            entry.status = 'PROMOTED'
            entry.promoted_at = datetime.now(local_tz)
            entry.operator_id = operator_id or 'SYSTEM'
            entry.operator_type = 'SYSTEM' if auto_promote else 'ADMIN'
            set_update_audit(entry, operator_id or 'SYSTEM')

            # 重新计算队列位置
            await self._recalculate_positions(entry.schedule_id)

            await self.db.commit()

            return appointment

        except Exception as e:
            # 创建预约失败，回滚候补状态
            entry.status = 'WAITING'
            entry.promoted_at = None
            await self.db.rollback()
            raise ValueError(f'候补转预约失败: {e}')

    async def _recalculate_positions(self, schedule_id: str):
        """重新计算队列位置

        当有候补记录被取消或转预约后，重新计算位置

        Args:
            schedule_id: 排班ID
        """
        # 获取所有等待中的候补记录，按创建时间排序
        result = await self.db.execute(
            select(WaitlistEntry).where(
                and_(
                    WaitlistEntry.schedule_id == schedule_id,
                    WaitlistEntry.status == 'WAITING'
                )
            ).order_by(WaitlistEntry.created_at, WaitlistEntry.priority)
        )
        entries = result.scalars().all()

        # 更新位置
        for index, entry in enumerate(entries, start=1):
            entry.position = index

        await self.db.flush()

    async def cleanup_expired(self):
        """清理过期的候补记录

        清理条件：
        1. 班次已结束
        2. 状态仍为 WAITING

        定时任务调用
        """
        # 获取已结束班次的候补记录
        result = await self.db.execute(
            select(WaitlistEntry)
            .join(Schedule, WaitlistEntry.schedule_id == Schedule.id)
            .where(
                and_(
                    WaitlistEntry.status == 'WAITING',
                    Schedule.status == 0  # 已结束
                )
            )
        )
        entries = result.scalars().all()

        for entry in entries:
            entry.status = 'EXPIRED'
            entry.operator_id = 'SYSTEM'
            entry.operator_type = 'SYSTEM'
            set_update_audit(entry, 'SYSTEM')

        await self.db.commit()

    async def _check_rest_day(
        self,
        check_date,
        store_id: Optional[str] = None,
        doctor_id: Optional[str] = None
    ) -> bool:
        """检查指定日期是否为休息日
        
        Args:
            check_date: 要检查的日期
            store_id: 门店ID
            doctor_id: 医生ID
            
        Returns:
            True 表示是休息日，False 表示不是
        """
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

        return len(entries)
