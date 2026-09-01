from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_account_dict
from app.db.session import get_db
from app.middleware.tenant_context import get_current_tenant_id
from app.modules.notification_preferences.service import NotificationPreferenceService
from app.schemas.notification_preference import (
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
)

router = APIRouter()


def _resolve_user_type(current_user: dict) -> str:
    """根据统一账号字典解析通知偏好维度下的 user_type。

    通知偏好的 user_type 取值为 patient / doctor / admin（与
    NotificationRecipient.user_type 一致）。get_current_account_dict 返回的
    dict 用 role_type 标识角色（admin / operator / doctor / user），其中
    operator 归入 admin 维度（运营人员使用同一套管理端通知偏好）。
    旧的 ``is_doctor`` 判定在 admin/operator 进入时会误落入 patient，故改为
    以 role_type 为准。
    """
    role_type = current_user.get("role_type", "user")
    if role_type == "doctor":
        return "doctor"
    if role_type in ("admin", "operator"):
        return "admin"
    return "patient"


@router.get("", response_model=NotificationPreferenceResponse, summary="获取通知偏好")
async def get_notification_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_account_dict),
):
    user_type = _resolve_user_type(current_user)
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
    current_user: dict = Depends(get_current_account_dict),
):
    user_type = _resolve_user_type(current_user)
    service = NotificationPreferenceService(db)
    pref = await service.update(
        user_id=current_user["id"],
        user_type=user_type,
        data=data,
        tenant_id=get_current_tenant_id(),
    )
    return NotificationPreferenceResponse.model_validate(pref)
