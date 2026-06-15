"""统一账号头像上传端点

为所有角色（admin/doctor/user）提供统一的头像上传 API。
根据 Token 类型自动确定角色，同时更新旧表和 Account 表。
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.account_sync import AccountSyncService
from app.common.auth_types import AccountInfo, RoleType
from app.common.auth_unified import get_current_account
from app.core.config import settings
from app.core.logging import logger
from app.core.redis import RedisCache
from app.core.security import get_password_hash, verify_password
from app.db.session import get_db
from app.infrastructure.email.service import EmailService
from app.infrastructure.storage import get_storage
from app.infrastructure.storage.base import build_tenant_storage_folder
from app.models.account import Account, AccountAdmin
from app.models.admin import Admin
from app.models.doctor import Doctor
from app.models.user import User

router = APIRouter()

ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2MB


class UnifiedAvatarResponse(BaseModel):
    url: str
    key: str


class AccountChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class AccountEmailSendCodeRequest(BaseModel):
    email: str | None = None
    code_type: str = "bind"


class AccountEmailBindRequest(BaseModel):
    email: str
    code: str


class AccountEmailUnbindRequest(BaseModel):
    code: str


class AccountEmailChangeRequest(BaseModel):
    new_email: str
    new_email_code: str
    old_email_code: str


def _camelize_keys(value):
    """递归将 dict key 从 snake_case 转为 camelCase。"""
    from app.schemas.auth import to_camel

    if isinstance(value, dict):
        return {to_camel(key): _camelize_keys(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_camelize_keys(item) for item in value]
    return value


def _validate_email_format(email: str) -> bool:
    import re

    if not email or not email.strip():
        return False
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email))


def _normalize_email(email: str) -> str:
    return email.strip().lower()


async def _get_account_row(db: AsyncSession, account: AccountInfo) -> Account:
    account_row = await db.get(Account, account.id)
    if not account_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在，请检查后重试")
    return account_row


async def _is_email_taken_in_tenant(
    db: AsyncSession,
    tenant_id: str | None,
    email: str,
    exclude_account_id: str,
) -> bool:
    query = select(Account).where(Account.email == email)
    if tenant_id is None:
        query = query.where(Account.tenant_id.is_(None))
    else:
        query = query.where(Account.tenant_id == tenant_id)
    result = await db.execute(query)
    existing_account = result.scalar_one_or_none()
    return bool(existing_account and existing_account.id != exclude_account_id)


async def _sync_legacy_email(
    db: AsyncSession,
    account: AccountInfo,
    email: str | None,
) -> None:
    if account.role_type == RoleType.ADMIN:
        admin = await db.get(Admin, account.id)
        if admin:
            admin.email = email
        admin_ext = await db.get(AccountAdmin, account.id)
        if admin_ext:
            admin_ext.email = email
    elif account.role_type == RoleType.USER:
        user = await db.get(User, account.id)
        if user:
            user.email = email


@router.get("/me", summary="获取统一账号信息")
async def get_account_me(
    account: AccountInfo = Depends(get_current_account),
):
    """获取当前登录账号的统一视图（accounts 入口）。"""
    return _camelize_keys(account.to_dict())


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
        await AccountSyncService._update_account_field(db, account.id, "avatar", result.url)
        await db.commit()
    except Exception as exc:
        logger.warning(f"Sync avatar to Account table failed: {exc}")

    logger.info(f"Avatar uploaded: {result.key} by {account.role_type.value} {account.id}")
    return UnifiedAvatarResponse(url=result.url, key=result.key)


@router.post("/me/change-password", summary="统一账号修改密码")
async def change_account_password(
    data: AccountChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    account: AccountInfo = Depends(get_current_account),
):
    """统一账号改密入口（admin/doctor/user 通用）。"""
    account_row = await db.get(Account, account.id)
    if not account_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在，请检查后重试")
    if not account_row.password_hash:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前账号未设置密码，请先设置初始密码")

    if not verify_password(data.old_password, account_row.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="原密码错误，请重新输入")

    if data.old_password == data.new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码不能与原密码相同")
    if not (6 <= len(data.new_password) <= 20):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="密码长度必须为6-20位")

    # 租户密码策略校验
    from app.modules.tenants.password_policy import PasswordPolicyValidator, get_tenant_password_policy

    policy = await get_tenant_password_policy(db, account.tenant_id)
    validator = PasswordPolicyValidator(policy)
    is_valid, errors = validator.validate(
        data.new_password,
        username=getattr(account, "username", None),
        phone=account.phone,
    )
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="; ".join(errors))

    new_hash = get_password_hash(data.new_password)
    account_row.password_hash = new_hash

    # 兼容旧表登录链路：同步更新 legacy 主表密码
    if account.role_type == RoleType.ADMIN:
        admin = await db.get(Admin, account.id)
        if admin:
            admin.password_hash = new_hash
    elif account.role_type == RoleType.DOCTOR:
        doctor = await db.get(Doctor, account.id)
        if doctor:
            doctor.password_hash = new_hash
    else:
        user = await db.get(User, account.id)
        if user:
            user.password_hash = new_hash

    await db.commit()
    return {"message": "密码修改成功"}


@router.post("/me/email/send-code", summary="发送统一账号邮箱验证码")
async def send_account_email_code(
    data: AccountEmailSendCodeRequest,
    db: AsyncSession = Depends(get_db),
    account: AccountInfo = Depends(get_current_account),
):
    account_row = await _get_account_row(db, account)
    target_email = data.email or account_row.email
    if not target_email or not _validate_email_format(target_email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱格式不正确")

    target_email = _normalize_email(target_email)
    scenario = "account_bind"
    can_send, wait_seconds = await RedisCache.check_email_rate_limit(target_email, scenario)
    if not can_send:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"发送过于频繁，请{wait_seconds}秒后重试",
        )

    from app.infrastructure.sms.service import SmsService

    code = SmsService.generate_code()
    await RedisCache.set_email_code(target_email, code, scenario)
    try:
        email_service = EmailService(db)
        await email_service.send_verification_code_email(target_email, code, scenario)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="验证码发送失败，请稍后重试",
        ) from exc

    if settings.DEBUG:
        return {"message": "验证码发送成功", "code": code}
    return {"message": "验证码发送成功"}


@router.post("/me/email/bind", summary="统一账号绑定邮箱")
async def bind_account_email(
    data: AccountEmailBindRequest,
    db: AsyncSession = Depends(get_db),
    account: AccountInfo = Depends(get_current_account),
):
    if not _validate_email_format(data.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱格式不正确")

    email = _normalize_email(data.email)
    is_valid = await RedisCache.verify_email_code(email, data.code, "account_bind")
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")
    if await _is_email_taken_in_tenant(db, account.tenant_id, email, account.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该邮箱已被其他账号绑定")

    account_row = await _get_account_row(db, account)
    account_row.email = email
    await _sync_legacy_email(db, account, email)
    await db.commit()
    return {"message": "邮箱绑定成功"}


@router.post("/me/email/unbind", summary="统一账号解绑邮箱")
async def unbind_account_email(
    data: AccountEmailUnbindRequest,
    db: AsyncSession = Depends(get_db),
    account: AccountInfo = Depends(get_current_account),
):
    account_row = await _get_account_row(db, account)
    if not account_row.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前账号未绑定邮箱")

    is_valid = await RedisCache.verify_email_code(account_row.email, data.code, "account_bind")
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")

    account_row.email = None
    await _sync_legacy_email(db, account, None)
    await db.commit()
    return {"message": "邮箱解绑成功"}


@router.post("/me/email/change", summary="统一账号更换邮箱")
async def change_account_email(
    data: AccountEmailChangeRequest,
    db: AsyncSession = Depends(get_db),
    account: AccountInfo = Depends(get_current_account),
):
    if not _validate_email_format(data.new_email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新邮箱格式不正确")

    new_email = _normalize_email(data.new_email)
    account_row = await _get_account_row(db, account)
    if not account_row.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前账号未绑定邮箱，请先绑定")

    old_valid = await RedisCache.verify_email_code(account_row.email, data.old_email_code, "account_bind")
    if not old_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前邮箱验证码错误或已过期")

    new_valid = await RedisCache.verify_email_code(new_email, data.new_email_code, "account_bind")
    if not new_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新邮箱验证码错误或已过期")

    if await _is_email_taken_in_tenant(db, account.tenant_id, new_email, account.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新邮箱已被其他账号绑定")

    account_row.email = new_email
    await _sync_legacy_email(db, account, new_email)
    await db.commit()
    return {"message": "邮箱换绑成功"}
