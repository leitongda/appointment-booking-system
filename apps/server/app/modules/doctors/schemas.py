from typing import List, Optional

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
    items: List[SortOrderItem]


class CheckUsernameRequest(BaseModel):
    username: str
    exclude_id: Optional[str] = None


class CheckUsernameResponse(BaseModel):
    exists: bool
    suggestions: List[str] = []


class GenerateUsernameRequest(BaseModel):
    name: str


class GenerateUsernameResponse(BaseModel):
    username: str
