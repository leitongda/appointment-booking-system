"""常见服务模块业务逻辑"""
import json
from datetime import date, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.middleware.tenant_context import get_current_tenant_id
from app.models.appointment import Appointment
from app.models.common_service import CommonService, HealthReminder
from app.models.user import Patient


def safe_json_loads(value):
    if isinstance(value, (list, dict)):
        return value
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


class CommonServiceService:
    """常见服务服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        store_id: str | None = None,
        status: int | None = None,
    ) -> list[CommonService]:
        """获取常见服务列表"""
        tenant_id = get_current_tenant_id()

        conditions = [CommonService.tenant_id == tenant_id]

        if store_id:
            # 查询门店专属和全局的服务
            conditions.append(
                or_(CommonService.store_id == store_id, CommonService.store_id.is_(None))
            )
        else:
            # 只查全局服务
            conditions.append(CommonService.store_id.is_(None))

        if status is not None:
            conditions.append(CommonService.status == status)

        query = select(CommonService).options(
            selectinload(CommonService.department),
        ).where(and_(*conditions))
        query = query.order_by(CommonService.sort_order.asc())

        result = await self.db.execute(query)
        return list(result.scalars().all())


class HealthReminderService:
    """健康提醒服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_config(
        self,
        store_id: str | None = None,
        reminder_type: str | None = None,
    ) -> list[HealthReminder]:
        """获取健康提醒配置"""
        tenant_id = get_current_tenant_id()

        conditions = [HealthReminder.tenant_id == tenant_id]

        if store_id:
            conditions.append(
                or_(HealthReminder.store_id == store_id, HealthReminder.store_id.is_(None))
            )
        else:
            conditions.append(HealthReminder.store_id.is_(None))

        if reminder_type:
            conditions.append(HealthReminder.reminder_type == reminder_type)

        conditions.append(HealthReminder.status == 1)

        query = select(HealthReminder).where(and_(*conditions))
        query = query.order_by(HealthReminder.sort_order.asc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_user_reminder(
        self,
        user_id: str,
        store_id: str | None = None,
    ) -> dict:
        """获取用户的健康提醒信息

        基于用户的预约历史推断下次检查时间
        """
        tenant_id = get_current_tenant_id()

        # 获取默认就诊人
        patient_result = await self.db.execute(
            select(Patient).where(
                and_(
                    Patient.user_id == user_id,
                    Patient.tenant_id == tenant_id,
                )
            ).order_by(Patient.is_default.desc()).limit(1)
        )
        patient = patient_result.scalar_one_or_none()

        if not patient:
            return {
                "has_data": False,
                "reminder_content": "暂无提醒，请先添加就诊人",
            }

        # 获取最近的预约记录（用于推断检查历史）
        appointment_result = await self.db.execute(
            select(Appointment).where(
                and_(
                    Appointment.patient_id == patient.id,
                    Appointment.tenant_id == tenant_id,
                    Appointment.status.in_([4, 5]),  # 已完成或已取消
                )
            ).order_by(Appointment.created_at.desc()).limit(5)
        )
        appointments = list(appointment_result.scalars().all())

        # 获取提醒配置
        reminders = await self.get_config(store_id=store_id)

        if not reminders:
            return {
                "has_data": False,
                "reminder_content": "暂无提醒，祝您健康",
            }

        # 使用第一个提醒配置作为默认
        default_reminder = reminders[0]

        # 计算下次检查日期
        next_check_date = None
        last_check_date = None

        if appointments:
            last_appointment = appointments[0]
            if last_appointment.created_at:
                last_check_date = last_appointment.created_at.date()
                # 基于推荐周期计算下次检查
                interval_days = default_reminder.recommended_interval or 365
                next_check_date = last_check_date + timedelta(days=interval_days)
        else:
            # 无历史记录，设置默认提醒
            next_check_date = date.today() + timedelta(days=default_reminder.recommended_interval or 365)

        # 解析贴士
        tips = None
        if default_reminder.tips:
            tips = safe_json_loads(default_reminder.tips)

        return {
            "next_check_date": next_check_date.isoformat() if next_check_date else None,
            "last_check_date": last_check_date.isoformat() if last_check_date else None,
            "check_type": default_reminder.reminder_type,
            "reminder_content": default_reminder.content,
            "tips": tips,
            "has_data": True,
        }
