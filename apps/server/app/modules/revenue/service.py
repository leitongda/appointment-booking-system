from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import and_, case, func, select
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
        # 注意：DoctorConsultationFee 的自然键为 (doctor_id, store_id, department_id, fee_type_id)，
        # 表上没有唯一约束，同一 (doctor_id, store_id, fee_type_id) 可能存在多条（不同科室）记录。
        # 因此必须按 schedule.store_id 收窄，并优先匹配 schedule/医生所属科室，使用 first() 容错。
        store_id = schedule.store_id or doctor.store_id
        department_id = doctor.department_id

        doctor_fee_stmt = (
            select(DoctorConsultationFee)
            .where(
                DoctorConsultationFee.doctor_id == doctor.id,
                DoctorConsultationFee.fee_type_id == fee_type.id,
                DoctorConsultationFee.store_id == store_id,
                DoctorConsultationFee.status == 1,
            )
            # 优先返回所属科室的记录，避免在多科室场景下取错行
            .order_by(
                case(
                    (DoctorConsultationFee.department_id == department_id, 0),
                    else_=1,
                ),
                DoctorConsultationFee.created_at.desc(),
            )
            .limit(1)
        )
        doctor_fee = (await self.db.execute(doctor_fee_stmt)).scalar_one_or_none()

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
        status_list: list[int] = None,
        tenant_id: str | None = None,
    ) -> Decimal:
        """
        计算时间段内的总收入

        由于需要逐条判断初诊/复诊，这里采用批量查询然后遍历计算的方式
        对于大数据量可以考虑使用缓存或定期聚合

        Args:
            tenant_id: 租户锚点（None 表示平台管理员，不按租户过滤）
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
                    Appointment.created_at >= datetime.combine(start_date, datetime.min.time()),
                    Appointment.created_at < datetime.combine(end_date + timedelta(days=1), datetime.min.time()),
                    Appointment.status.in_(status_list)
                )
            )
        )

        if store_id:
            query = query.where(Doctor.store_id == store_id)

        # 租户过滤（R1-3）
        if tenant_id:
            query = query.where(Doctor.tenant_id == tenant_id)

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
        store_id: str | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, float]:
        """
        计算收入趋势

        返回 {日期: 收入} 的字典

        Args:
            tenant_id: 租户锚点（None 表示平台管理员，不按租户过滤）
        """
        # 查询预约
        query = (
            select(Appointment)
            .join(Schedule, Appointment.schedule_id == Schedule.id)
            .join(Doctor, Schedule.doctor_id == Doctor.id)
            .where(
                and_(
                    Appointment.created_at >= datetime.combine(start_date, datetime.min.time()),
                    Appointment.created_at < datetime.combine(end_date + timedelta(days=1), datetime.min.time()),
                    Appointment.status.in_([2, 3, 5])
                )
            )
        )

        if store_id:
            query = query.where(Doctor.store_id == store_id)

        # 租户过滤（R1-3）
        if tenant_id:
            query = query.where(Doctor.tenant_id == tenant_id)

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
