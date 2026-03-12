"""Composed consultation-fee service."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.consultation_fees.service_doctors import ConsultationFeeDoctorMixin
from app.modules.consultation_fees.service_store import ConsultationFeeStoreMixin
from app.modules.consultation_fees.service_types import ConsultationFeeTypeMixin


class ConsultationFeeService(
    ConsultationFeeTypeMixin,
    ConsultationFeeStoreMixin,
    ConsultationFeeDoctorMixin,
):
    def __init__(self, db: AsyncSession):
        self.db = db
