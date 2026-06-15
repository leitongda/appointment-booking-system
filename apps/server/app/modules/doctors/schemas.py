
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


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
