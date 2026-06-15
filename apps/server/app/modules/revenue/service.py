from datetime import date
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.constants.appointment import REVENUE_STATUSES
from app.models.appointment import Appointment
from app.models.consultation_fee import ConsultationFeeType, DoctorConsultationFee
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.modules.visit_types.service import VisitTypeService


class RevenueService:
    """收入计算服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.visit_type_service = VisitTypeService(db)

    async def get_appointment_fee(self, appointment: Appointment) -> Decimal:
        """
        计算单个预约的诊费

        逻辑：
        1. 获取排班的 appointment_type
        2. 通过 appointment_type 匹配诊费类型的 code
        3. 获取医生的诊费配置
        4. 判断初诊/复诊，返回对应金额
        """
        # 获取排班信息
        schedule_result = await self.db.execute(
            select(Schedule)
            .options(joinedload(Schedule.doctor))
            .where(Schedule.id == appointment.schedule_id)
        )
        schedule = schedule_result.unique().scalar_one_or_none()

        if not schedule or not schedule.doctor:
            return Decimal("0")

        doctor = schedule.doctor
        appointment_type = schedule.appointment_type or "normal"

        # 查找匹配的诊费类型
        fee_type_result = await self.db.execute(
            select(ConsultationFeeType)
            .where(
                and_(
                    ConsultationFeeType.code == appointment_type,
                    ConsultationFeeType.status == 1
                )
            )
        )
        fee_type = fee_type_result.scalar_one_or_none()

        if not fee_type:
            return Decimal("0")

        # 获取医生的诊费配置
        doctor_fee_result = await self.db.execute(
            select(DoctorConsultationFee)
            .where(
                and_(
                    DoctorConsultationFee.doctor_id == doctor.id,
                    DoctorConsultationFee.fee_type_id == fee_type.id,
                    DoctorConsultationFee.status == 1
                )
            )
        )
        doctor_fee = doctor_fee_result.scalar_one_or_none()

        if not doctor_fee:
            return Decimal("0")

        # 判断初诊/复诊
        is_follow_up = await self.visit_type_service.is_follow_up_visit(
            patient_id=appointment.patient_id,
            store_id=schedule.store_id or doctor.store_id,
            doctor_id=doctor.id,
            department_id=doctor.department_id,
            check_time=appointment.created_at
        )

        if is_follow_up:
            return doctor_fee.follow_up_fee or Decimal("0")
        else:
            return doctor_fee.initial_fee or Decimal("0")

    async def calculate_total_revenue(
        self,
        start_date: date,
        end_date: date | None = None,
        store_id: str | None = None,
        status_list: list[int] = None
    ) -> Decimal:
        """
        计算时间段内的总收入

        由于需要逐条判断初诊/复诊，这里采用批量查询然后遍历计算的方式
        对于大数据量可以考虑使用缓存或定期聚合
        """
        if status_list is None:
            status_list = list(REVENUE_STATUSES)  # 已签到/历史候诊/就诊中/已完成

        if end_date is None:
            end_date = date.today()

        # 查询预约
        query = (
            select(Appointment)
            .join(Schedule, Appointment.schedule_id == Schedule.id)
            .join(Doctor, Schedule.doctor_id == Doctor.id)
            .where(
                and_(
                    func.date(Appointment.created_at) >= start_date,
                    func.date(Appointment.created_at) <= end_date,
                    Appointment.status.in_(status_list)
                )
            )
        )

        if store_id:
            query = query.where(Doctor.store_id == store_id)

        # 排除软删除的医生
        query = query.where(Doctor.deleted_at.is_(None))

        result = await self.db.execute(query)
        appointments = result.scalars().all()

        total = Decimal("0")
        for appt in appointments:
            fee = await self.get_appointment_fee(appt)
            total += fee

        return total

    async def calculate_revenue_trend(
        self,
        start_date: date,
        end_date: date,
        store_id: str | None = None
    ) -> dict[str, float]:
        """
        计算收入趋势

        返回 {日期: 收入} 的字典
        """
        # 查询预约
        query = (
            select(Appointment)
            .join(Schedule, Appointment.schedule_id == Schedule.id)
            .join(Doctor, Schedule.doctor_id == Doctor.id)
            .where(
                and_(
                    func.date(Appointment.created_at) >= start_date,
                    func.date(Appointment.created_at) <= end_date,
                    Appointment.status.in_([2, 3, 5])
                )
            )
        )

        if store_id:
            query = query.where(Doctor.store_id == store_id)

        # 排除软删除的医生
        query = query.where(Doctor.deleted_at.is_(None))

        result = await self.db.execute(query)
        appointments = result.scalars().all()

        # 按日期分组计算
        daily_revenue: dict[str, Decimal] = {}

        for appt in appointments:
            appt_date = str(appt.created_at.date())
            fee = await self.get_appointment_fee(appt)

            if appt_date not in daily_revenue:
                daily_revenue[appt_date] = Decimal("0")
            daily_revenue[appt_date] += fee

        return {k: float(v) for k, v in daily_revenue.items()}
