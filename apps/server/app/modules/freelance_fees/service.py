"""兼职费用服务 — 组合 Query + Mutation"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.freelance_fees.service_mutation import FreelanceMutationMixin
from app.modules.freelance_fees.service_query import FreelanceQueryMixin


class FreelanceService(FreelanceQueryMixin, FreelanceMutationMixin):
    """兼职费用服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
