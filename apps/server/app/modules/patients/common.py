from datetime import date, datetime
import random
import string

from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant_context import get_current_tenant_id


class PatientsServiceBase:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _current_tenant_id(self) -> str | None:
        return get_current_tenant_id()

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
