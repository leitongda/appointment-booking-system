import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant_context import get_current_tenant_id
from app.models.appointment import Appointment
from app.models.appointment_satisfaction import AppointmentSatisfaction
from app.modules.appointment_satisfactions.schemas import AppointmentSatisfactionCreate
from app.utils.audit import set_create_audit


class AppointmentSatisfactionService:
    """预约满意度服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _tenant_filter(self, stmt):
        tenant_id = get_current_tenant_id()
        if tenant_id:
            return stmt.where(AppointmentSatisfaction.tenant_id == tenant_id)
        return stmt

    async def create(
        self,
        appointment_id: str,
        user_id: str,
        data: AppointmentSatisfactionCreate,
    ) -> AppointmentSatisfaction:
        """创建满意度评价"""
        # 获取预约信息
        appt_result = await self.db.execute(
            select(Appointment).where(Appointment.id == appointment_id)
        )
        appointment = appt_result.scalar_one_or_none()
        if not appointment:
            raise ValueError("预约不存在")

        satisfaction = AppointmentSatisfaction(
            id=str(uuid.uuid4()),
            tenant_id=get_current_tenant_id(),
            appointment_id=appointment_id,
            user_id=user_id,
            patient_id=appointment.patient_id,
            doctor_id=appointment.doctor_id,
            overall_score=data.overall_score,
            service_score=data.service_score,
            environment_score=data.environment_score,
            comment=data.comment,
            tags=data.tags,
            submitted_at=datetime.utcnow(),
        )
        set_create_audit(satisfaction, user_id)
        self.db.add(satisfaction)
        await self.db.commit()
        await self.db.refresh(satisfaction)
        return satisfaction

    async def get_by_appointment(self, appointment_id: str) -> AppointmentSatisfaction | None:
        """获取预约的满意度评价"""
        stmt = self._tenant_filter(
            select(AppointmentSatisfaction).where(
                AppointmentSatisfaction.appointment_id == appointment_id
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
