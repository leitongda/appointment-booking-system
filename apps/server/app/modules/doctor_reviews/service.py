import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.exception import BusinessError
from app.middleware.tenant_context import get_current_tenant_id
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.doctor_review import DoctorReview
from app.models.user import Patient, User
from app.modules.doctor_reviews.schemas import DoctorReviewCreate, DoctorReviewPatientCreate, DoctorReviewReply
from app.utils.audit import set_create_audit, set_update_audit


class DoctorReviewService:
    """医生评价服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def mask_patient_name(name: str | None) -> str | None:
        """就诊人姓名脱敏：保留姓氏，其余以 * 代替（如 雷先生 → 雷**）"""
        if not name:
            return name
        return name[0] + "*" * max(len(name) - 1, 1)

    def _tenant_filter(self, stmt):
        tenant_id = get_current_tenant_id()
        if tenant_id:
            return stmt.where(DoctorReview.tenant_id == tenant_id)
        return stmt

    async def create(self, user_id: str, data: DoctorReviewCreate) -> DoctorReview:
        """创建评价"""
        review = DoctorReview(
            id=str(uuid.uuid4()),
            tenant_id=get_current_tenant_id(),
            appointment_id=data.appointment_id,
            doctor_id=data.doctor_id,
            user_id=user_id,
            patient_id=data.patient_id,
            rating=data.rating,
            content=data.content,
            tags=data.tags,
            is_anonymous=data.is_anonymous,
            status=1,
        )
        set_create_audit(review, user_id)
        self.db.add(review)

        # 更新医生评价统计
        await self._update_doctor_rating(data.doctor_id)

        await self.db.commit()
        await self.db.refresh(review)
        return review

    async def create_from_patient(
        self, user_id: str, data: DoctorReviewPatientCreate
    ) -> DoctorReview:
        """患者端创建评价

        评价必须挂到一条预约上（appointment_id 非空，见模型约束）：
        - 显式传入 appointment_id 时校验归属（本人 + 该医生）；
        - 未传入时自动取该患者在目标医生下的最近一次预约。
        重复提交依赖 appointment_id 唯一约束（uq_doctor_reviews_appointment）
        在提交时拦截，返回 409。
        """
        doctor_id = data.doctor_id

        # 医生必须存在，避免写入时触发外键错误
        if await self.db.get(Doctor, doctor_id) is None:
            raise BusinessError("医生不存在", code=404)

        appointment = await self._resolve_patient_appointment(user_id, doctor_id, data.appointment_id)

        review = DoctorReview(
            id=str(uuid.uuid4()),
            tenant_id=get_current_tenant_id() or appointment.tenant_id,
            appointment_id=appointment.id,
            doctor_id=doctor_id,
            user_id=user_id,
            patient_id=appointment.patient_id,
            rating=data.rating,
            content=data.content,
            tags=None,
            is_anonymous=data.is_anonymous,
            status=1,
        )
        set_create_audit(review, user_id)
        self.db.add(review)

        # 更新医生评价统计
        await self._update_doctor_rating(doctor_id)

        try:
            await self.db.commit()
        except IntegrityError as exc:
            # appointment_id 唯一约束冲突：同一预约只能评价一次
            await self.db.rollback()
            raise BusinessError("该预约已评价过，请勿重复评价", code=409) from exc
        await self.db.refresh(review)
        return review

    async def _resolve_patient_appointment(
        self,
        user_id: str,
        doctor_id: str,
        appointment_id: str | None,
    ) -> Appointment:
        """定位评价关联的预约：显式指定时校验归属，否则取最近一次预约"""
        if appointment_id:
            appointment = await self.db.get(Appointment, appointment_id)
            if (
                appointment is None
                or appointment.user_id != user_id
                or appointment.doctor_id != doctor_id
            ):
                raise BusinessError("预约不存在或不属于当前医生", code=400)
            return appointment

        # 复用预约服务的既有查询：按创建时间倒序取该患者在目标医生下的最近一条
        from app.modules.appointments.service import AppointmentService

        appointments, _ = await AppointmentService(self.db).get_list(
            user_id=user_id,
            doctor_id=doctor_id,
            page=1,
            page_size=1,
        )
        if not appointments:
            raise BusinessError("未找到可评价的预约记录", code=400)
        return appointments[0]

    async def get_list(
        self,
        doctor_id: str | None = None,
        user_id: str | None = None,
        status: int | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[dict], int]:
        """获取评价列表"""
        stmt = self._tenant_filter(select(DoctorReview))
        count_stmt = self._tenant_filter(select(func.count(DoctorReview.id)))

        if doctor_id:
            stmt = stmt.where(DoctorReview.doctor_id == doctor_id)
            count_stmt = count_stmt.where(DoctorReview.doctor_id == doctor_id)
        if user_id:
            stmt = stmt.where(DoctorReview.user_id == user_id)
            count_stmt = count_stmt.where(DoctorReview.user_id == user_id)
        if status is not None:
            stmt = stmt.where(DoctorReview.status == status)
            count_stmt = count_stmt.where(DoctorReview.status == status)

        stmt = stmt.order_by(DoctorReview.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        count_result = await self.db.execute(count_stmt)

        reviews = list(result.scalars().all())
        total = count_result.scalar() or 0

        # 填充关联信息
        enriched = []
        for review in reviews:
            item = {
                "id": review.id,
                "appointment_id": review.appointment_id,
                "doctor_id": review.doctor_id,
                "user_id": review.user_id,
                "patient_id": review.patient_id,
                "rating": review.rating,
                "content": review.content,
                "tags": review.tags,
                "is_anonymous": review.is_anonymous,
                "status": review.status,
                "reply": review.reply,
                "reply_at": review.reply_at,
                "created_at": review.created_at,
                "user_name": None,
                "patient_name": None,
            }
            if not review.is_anonymous:
                user = await self._get_user_name(review.user_id)
                item["user_name"] = user
            if review.patient_id:
                patient = await self._get_patient_name(review.patient_id)
                item["patient_name"] = patient
            enriched.append(item)

        return enriched, total

    async def get_by_doctor(
        self,
        doctor_id: str,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[dict], int]:
        """获取医生评价列表"""
        return await self.get_list(doctor_id=doctor_id, status=1, page=page, page_size=page_size)

    async def reply(
        self,
        review_id: str,
        operator_id: str,
        data: DoctorReviewReply,
    ) -> DoctorReview | None:
        """回复评价"""
        stmt = self._tenant_filter(
            select(DoctorReview).where(DoctorReview.id == review_id)
        )
        result = await self.db.execute(stmt)
        review = result.scalar_one_or_none()
        if not review:
            return None

        review.reply = data.reply
        review.reply_at = datetime.utcnow()
        set_update_audit(review, operator_id)

        await self.db.commit()
        await self.db.refresh(review)
        return review

    async def _update_doctor_rating(self, doctor_id: str):
        """更新医生平均评分和评价数"""
        stmt = select(
            func.avg(DoctorReview.rating),
            func.count(DoctorReview.id),
        ).where(
            DoctorReview.doctor_id == doctor_id,
            DoctorReview.status == 1,
        )
        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(DoctorReview.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        row = result.one()
        avg_rating = float(row[0] or 0)
        review_count = row[1] or 0

        await self.db.execute(
            update(Doctor)
            .where(Doctor.id == doctor_id)
            .values(avg_rating=round(avg_rating, 2), review_count=review_count)
        )

    async def _get_user_name(self, user_id: str) -> str | None:
        result = await self.db.execute(
            select(User.nickname).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def _get_patient_name(self, patient_id: str) -> str | None:
        result = await self.db.execute(
            select(Patient.name).where(Patient.id == patient_id)
        )
        return result.scalar_one_or_none()
