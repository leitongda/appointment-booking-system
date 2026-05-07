"""统一账号头像上传端点

为所有角色（admin/doctor/user）提供统一的头像上传 API。
根据 Token 类型自动确定角色，同时更新旧表和 Account 表。
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth_unified import get_current_account
from app.common.auth_types import AccountInfo, RoleType
from app.common.account_sync import AccountSyncService
from app.core.logging import logger
from app.db.session import get_db
from app.infrastructure.storage import get_storage
from app.infrastructure.storage.base import build_tenant_storage_folder
from app.models.admin import Admin
from app.models.doctor import Doctor
from app.models.user import User

router = APIRouter()

ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2MB


class UnifiedAvatarResponse(BaseModel):
    url: str
    key: str


@router.post("/avatar", response_model=UnifiedAvatarResponse, summary="统一头像上传")
async def upload_unified_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    account: AccountInfo = Depends(get_current_account),
):
    """统一头像上传（支持所有角色）

    根据 Token 自动判断角色，更新对应表的 avatar 字段，
    同时双写到 Account 表。
    """
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的图片格式，请使用 jpg、png、gif 或 webp",
        )

    content = await file.read()
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制，最大支持 {MAX_AVATAR_SIZE // 1024 // 1024}MB",
        )

    await file.seek(0)

    try:
        storage = get_storage()
        content_type = file.content_type or "image/jpeg"
        filename = file.filename or "avatar.jpg"
        tenant_folder = build_tenant_storage_folder("avatars", account.tenant_id)
        result = await storage.upload(
            file=file.file,
            filename=filename,
            content_type=content_type,
            folder=tenant_folder,
        )
    except Exception as exc:
        logger.error(f"Avatar upload failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="头像上传失败，请稍后重试",
        ) from exc

    # 更新旧表
    try:
        if account.role_type == RoleType.ADMIN:
            row = await db.execute(select(Admin).where(Admin.id == account.id))
            admin = row.scalar_one_or_none()
            if admin:
                admin.avatar = result.url
        elif account.role_type == RoleType.DOCTOR:
            row = await db.execute(select(Doctor).where(Doctor.id == account.id))
            doctor = row.scalar_one_or_none()
            if doctor:
                doctor.avatar = result.url
        elif account.role_type == RoleType.USER:
            row = await db.execute(select(User).where(User.id == account.id))
            user = row.scalar_one_or_none()
            if user:
                user.avatar = result.url

        await db.commit()
    except Exception as exc:
        logger.error(f"Update avatar in old table failed: {exc}")
        await db.rollback()

    # 双写到 Account 表
    try:
        AccountSyncService._update_account_field(db, account.id, "avatar", result.url)
        await db.commit()
    except Exception as exc:
        logger.warning(f"Sync avatar to Account table failed: {exc}")

    logger.info(f"Avatar uploaded: {result.key} by {account.role_type.value} {account.id}")
    return UnifiedAvatarResponse(url=result.url, key=result.key)
