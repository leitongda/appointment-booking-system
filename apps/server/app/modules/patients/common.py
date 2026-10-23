import random
import string
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant_context import get_current_tenant_id


class PatientsServiceBase:
    def __init__(self, db: AsyncSession, tenant_id: str | None = None):
        self.db = db
        # 管理端锚点：显式传入时硬过滤；未传时回退请求上下文（灰度兼容）
        self.tenant_id = tenant_id

    def _current_tenant_id(self) -> str | None:
        return self.tenant_id if self.tenant_id is not None else get_current_tenant_id()

    def _calculate_age(self, birthday: datetime):
        if not birthday:
            return None
        today = date.today()
        age = today.year - birthday.year
        if (today.month, today.day) < (birthday.month, birthday.day):
            age -= 1
        return age

    def _generate_card_no(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = "".join(random.choices(string.digits, k=4))
        return f"JZK{timestamp}{random_str}"
