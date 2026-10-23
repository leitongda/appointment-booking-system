"""候补队列递补服务"""
import logging
from datetime import datetime

from sqlalchemy import and_, select

from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.waitlist import WaitlistEntry
from app.modules.appointments.service import AppointmentService
from app.modules.rule_engine import RuleEngineService
from app.utils.audit import set_update_audit

logger = logging.getLogger(__name__)


class WaitlistPromotionMixin:
    """候补队列 - 递补方法"""

    async def promote_next(
        self,
        schedule_id: str,
        operator_id: str | None = None,
        tenant_id: str | None = None,
    ) -> Appointment | None:
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

        # 租户隔离：显式锚点存在时，他租户候补按不存在处理
        from app.middleware.tenant_context import get_current_tenant_id

        scope = tenant_id if tenant_id is not None else get_current_tenant_id()
        if scope and entry.tenant_id != scope:
            return None

        # 创建预约
        return await self._promote_to_appointment(entry, operator_id=operator_id or 'SYSTEM')

    async def auto_promote(
        self,
        schedule_id: str,
        reason: str = 'APPOINTMENT_CANCELLED'
    ) -> list[Appointment]:
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
                logger.error(f'递补候补用户失败: {entry.id}, 错误: {e}')

        return promoted

    async def _promote_to_appointment(
        self,
        entry: WaitlistEntry,
        operator_id: str | None = None,
        auto_promote: bool = False
    ) -> Appointment | None:
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
        import pytz

        from app.schemas.appointment import AppointmentCreate

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
