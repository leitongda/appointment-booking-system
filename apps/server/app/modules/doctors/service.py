"""Composed doctor service."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.doctors.service_mutation import DoctorMutationMixin
from app.modules.doctors.service_query import DoctorQueryMixin


class DoctorService(DoctorQueryMixin, DoctorMutationMixin):
    def __init__(self, db: AsyncSession):
        self.db = db
