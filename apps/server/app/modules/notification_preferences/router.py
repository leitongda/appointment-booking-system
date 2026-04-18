from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_user
from app.schemas.notification_preference import (
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
)
from app.modules.notification_preferences.service import NotificationPreferenceService
from app.middleware.tenant_context import get_current_tenant_id

router = APIRouter()


@router.get("", response_model=NotificationPreferenceResponse, summary="获取通知偏好")
async def get_notification_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_type = "doctor" if current_user.get("is_doctor") else "patient"
    service = NotificationPreferenceService(db)
    pref = await service.get_or_create(
        user_id=current_user["id"],
        user_type=user_type,
        tenant_id=get_current_tenant_id(),
    )
    return NotificationPreferenceResponse.model_validate(pref)


@router.put("", response_model=NotificationPreferenceResponse, summary="更新通知偏好")
async def update_notification_preferences(
    data: NotificationPreferenceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_type = "doctor" if current_user.get("is_doctor") else "patient"
    service = NotificationPreferenceService(db)
    pref = await service.update(
        user_id=current_user["id"],
        user_type=user_type,
        data=data,
        tenant_id=get_current_tenant_id(),
    )
    return NotificationPreferenceResponse.model_validate(pref)
