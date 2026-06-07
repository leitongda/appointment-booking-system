from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from typing import Optional, List, Tuple
from datetime import datetime
import uuid

from app.models.doctor_review import DoctorReview
from app.models.doctor import Doctor
from app.models.user import User
from app.models.patient import Patient
from app.modules.doctor_reviews.schemas import DoctorReviewCreate, DoctorReviewReply
from app.middleware.tenant_context import get_current_tenant_id
from app.utils.audit import set_create_audit, set_update_audit


class DoctorReviewService:
    """医生评价服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

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

    async def get_list(
        self,
        doctor_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[int] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[dict], int]:
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
    ) -> Tuple[List[dict], int]:
        """获取医生评价列表"""
        return await self.get_list(doctor_id=doctor_id, status=1, page=page, page_size=page_size)

    async def reply(
        self,
        review_id: str,
        operator_id: str,
        data: DoctorReviewReply,
    ) -> Optional[DoctorReview]:
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

    async def _get_user_name(self, user_id: str) -> Optional[str]:
        result = await self.db.execute(
            select(User.name).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def _get_patient_name(self, patient_id: str) -> Optional[str]:
        result = await self.db.execute(
            select(Patient.name).where(Patient.id == patient_id)
        )
        return result.scalar_one_or_none()
