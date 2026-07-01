
from pydantic import BaseModel

from app.schemas.doctor import DoctorResponse


class DoctorLoginRequest(BaseModel):
    phone: str
    password: str


class DoctorLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    doctor: DoctorResponse


class SortOrderItem(BaseModel):
    id: str
    sort_order: int


class BatchSortRequest(BaseModel):
    items: list[SortOrderItem]


class CheckUsernameRequest(BaseModel):
    username: str
    exclude_id: str | None = None


class CheckUsernameResponse(BaseModel):
    exists: bool
    suggestions: list[str] = []


class GenerateUsernameRequest(BaseModel):
    name: str


class GenerateUsernameResponse(BaseModel):
    username: str


# NOTE: ChangePasswordRequest 已收敛到 app.schemas.common（统一密码策略 6-20 位）。
# 原定义 old/new 为裸 str，长度靠 router 手动 HTTPException(400) 校验；
# 现迁移到 Pydantic schema 层 422（行为变更，详见 app/schemas/common.py docstring）。
# 请改为: from app.schemas.common import ChangePasswordRequest
