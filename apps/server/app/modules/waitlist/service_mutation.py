"""候补队列变更服务"""
from sqlalchemy import select, and_, func
from typing import Optional
from datetime import datetime
import uuid

from app.models.waitlist import WaitlistEntry
from app.models.schedule import Schedule
from app.models.rest_day import RestDay
from app.modules.rule_engine import RuleEngineService
from app.utils.audit import set_create_audit, set_update_audit


class WaitlistMutationMixin:
    """候补队列 - 变更方法"""

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
                except Exception:
                    pass

            return False
        except Exception:
            return False
