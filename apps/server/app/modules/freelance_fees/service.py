"""兼职费用服务 — 组合 Query + Mutation"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.freelance_fees.service_mutation import FreelanceMutationMixin
from app.modules.freelance_fees.service_query import FreelanceQueryMixin


class FreelanceService(FreelanceQueryMixin, FreelanceMutationMixin):
    """兼职费用服务

    Args:
        db: 数据库会话
        tenant_id: 管理员账号租户锚点（R1-4）。查询以锚点强过滤，
            写路径要求非空（否则拒绝）。
    """

    def __init__(self, db: AsyncSession, tenant_id: str | None = None):
        self.db = db
        self.tenant_id = tenant_id
