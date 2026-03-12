"""候补队列服务 - Mixin 组合"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.waitlist.service_query import WaitlistQueryMixin
from app.modules.waitlist.service_mutation import WaitlistMutationMixin
from app.modules.waitlist.service_promotion import WaitlistPromotionMixin


class WaitlistService(WaitlistQueryMixin, WaitlistMutationMixin, WaitlistPromotionMixin):
    """候补队列服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
