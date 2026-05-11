"""密码管理相关端点"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.config import settings
from app.core.redis import RedisCache
from app.db.session import get_db
from app.modules.admin.schemas import ChangePasswordRequest, UpdateProfileRequest
from app.modules.admin.service_admins import AdminService
from app.common.account_sync import AccountSyncService
from app.infrastructure.email.service import EmailService
from app.schemas.auth import EmailBindRequest, EmailChangeRequest, EmailSendCodeRequest, EmailUnbindRequest

router = APIRouter()


def _validate_email_format(email: str) -> bool:
    import re

    if not email or not email.strip():
        return False
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email))


def _normalize_email(email: str) -> str:
    return email.strip().lower()


@router.put("/me", response_model=None, summary="更新个人信息")
async def update_current_admin_profile(
    data: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    from app.modules.admin.helpers import build_admin_response

    service = AdminService(db)
    admin = await service.update(current_admin["id"], data.model_dump(exclude_unset=True))
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在，请检查后重试")
    admin = await service.get_by_id(current_admin["id"])
    return build_admin_response(admin)


@router.put("/me/change-password", summary="修改密码")
async def change_current_admin_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    from app.core.security import get_password_hash, verify_password

    service = AdminService(db)
    admin = await service.get_by_id(current_admin["id"])
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在，请检查后重试")
    if not verify_password(data.old_password, admin.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="原密码错误，请重新输入")

    # 密码策略校验
    from app.modules.tenants.password_policy import get_tenant_password_policy, PasswordPolicyValidator
    policy = await get_tenant_password_policy(db, admin.tenant_id)
    validator = PasswordPolicyValidator(policy)
    is_valid, errors = validator.validate(
        data.new_password,
        username=admin.username,
        phone=admin.phone,
    )
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="; ".join(errors))

    admin.password_hash = get_password_hash(data.new_password)
    await db.flush()

    # 双写同步: 密码变更同步到 accounts
    await AccountSyncService.sync_admin_to_account(
        db, current_admin["id"], operator_id=current_admin["id"]
    )

    await db.commit()
    return {"message": "密码修改成功"}


@router.post("/me/email/send-code", summary="发送管理员邮箱验证码")
async def send_current_admin_email_code(
    data: EmailSendCodeRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    service = AdminService(db)
    admin = await service.get_by_id(current_admin["id"])
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在，请检查后重试")

    target_email = data.email
    if not target_email and admin.email:
        target_email = admin.email

    if not target_email or not _validate_email_format(target_email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱格式不正确")

    target_email = _normalize_email(target_email)

    can_send, wait_seconds = await RedisCache.check_email_rate_limit(target_email, "admin_bind")
    if not can_send:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"发送过于频繁，请{wait_seconds}秒后重试",
        )

    from app.infrastructure.sms.service import SmsService

    code = SmsService.generate_code()
    await RedisCache.set_email_code(target_email, code, "admin_bind")

    try:
        email_service = EmailService(db)
        await email_service.send_verification_code_email(target_email, code, "admin_bind")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="验证码发送失败，请稍后重试",
        ) from exc

    if settings.DEBUG:
        return {"message": "验证码发送成功", "code": code}
    return {"message": "验证码发送成功"}


@router.post("/me/email/bind", summary="绑定管理员邮箱")
async def bind_current_admin_email(
    data: EmailBindRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    if not _validate_email_format(data.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱格式不正确")

    email = _normalize_email(data.email)
    is_valid = await RedisCache.verify_email_code(email, data.code, "admin_bind")
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")

    service = AdminService(db)
    admin = await service.get_by_id(current_admin["id"])
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在，请检查后重试")

    existing_admins = await service.list_by_email_global(email)
    if any(item.id != admin.id for item in existing_admins):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该邮箱已被其他管理员绑定")

    admin.email = email
    await db.flush()
    await AccountSyncService.sync_admin_to_account(db, admin.id, operator_id=admin.id)
    await db.commit()
    return {"message": "邮箱绑定成功"}


@router.post("/me/email/unbind", summary="解绑管理员邮箱")
async def unbind_current_admin_email(
    data: EmailUnbindRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    service = AdminService(db)
    admin = await service.get_by_id(current_admin["id"])
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在，请检查后重试")
    if not admin.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前账号未绑定邮箱")

    is_valid = await RedisCache.verify_email_code(admin.email, data.code, "admin_bind")
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")

    admin.email = None
    await db.flush()
    await AccountSyncService.sync_admin_to_account(db, admin.id, operator_id=admin.id)
    await db.commit()
    return {"message": "邮箱解绑成功"}


@router.post("/me/email/change", summary="更换管理员邮箱")
async def change_current_admin_email(
    data: EmailChangeRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    if not _validate_email_format(data.new_email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新邮箱格式不正确")

    new_email = _normalize_email(data.new_email)
    service = AdminService(db)
    admin = await service.get_by_id(current_admin["id"])
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在，请检查后重试")
    if not admin.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前账号未绑定邮箱，请先绑定")

    old_valid = await RedisCache.verify_email_code(admin.email, data.old_email_code, "admin_bind")
    if not old_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前邮箱验证码错误或已过期")

    new_valid = await RedisCache.verify_email_code(new_email, data.new_email_code, "admin_bind")
    if not new_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新邮箱验证码错误或已过期")

    existing_admins = await service.list_by_email_global(new_email)
    if any(item.id != admin.id for item in existing_admins):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新邮箱已被其他管理员绑定")

    admin.email = new_email
    await db.flush()
    await AccountSyncService.sync_admin_to_account(db, admin.id, operator_id=admin.id)
    await db.commit()
    return {"message": "邮箱换绑成功"}
