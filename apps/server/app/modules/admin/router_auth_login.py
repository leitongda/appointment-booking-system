"""登录相关端点"""
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, get_rsa_public_key, rsa_decrypt
from app.core.redis import RedisCache
from app.db.session import get_db
from app.infrastructure.email.service import EmailService
from app.common.security_settings import get_token_expire_config
from app.models.admin import Admin, Permission
from app.modules.admin.helpers import build_admin_response, build_stores_list, store_admin_session
from app.modules.admin.schemas import (
    AdminLoginRequest,
    AdminLoginResponse,
    PhoneLoginRequest,
    PublicKeyResponse,
    SmsCodeRequest,
    SmsLoginRequest,
    StoreInfo,
)
from app.schemas.auth import EmailLoginRequest, EmailSendCodeRequest
from app.schemas.response import Response
from app.modules.admin.service_admins import AdminService
from app.utils.ip import get_client_ip

router = APIRouter()
logger = logging.getLogger(__name__)


# ==================== 公钥 ====================

@router.get("/public-key", summary="获取RSA公钥")
async def get_public_key():
    public_key = get_rsa_public_key()
    response_data = PublicKeyResponse(public_key=public_key)
    return Response(code=200, message="success", data=response_data.model_dump(by_alias=True))


# ==================== 辅助函数 ====================

def _decrypt_password(raw_password: str, encrypted: bool, identifier: str) -> str:
    """解密密码"""
    try:
        if encrypted:
            password = rsa_decrypt(raw_password)
            logger.debug(f"密码解密成功: {identifier}")
            return password
        logger.warning(f"使用未加密密码登录（仅开发环境）: {identifier}")
        return raw_password
    except ValueError as exc:
        logger.error(f"密码解密失败: {str(exc)}, {identifier}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"密码处理失败: {str(exc)}, {identifier}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="密码格式错误，请重新输入") from exc


def _check_tenant_status_for_login(admin) -> None:
    """登录入口：检查租户订阅状态，命中则抛结构化错误码（403）。"""
    role_code = admin.role.code if admin.role else None
    is_super_admin = role_code == "SUPER_ADMIN"
    if not admin.tenant_id or is_super_admin or not admin.tenant:
        return

    from app.middleware.exception import raise_business_http_error
    from app.core.error_codes import ErrorCode as TenantErrorCode

    if admin.tenant.status == 0:
        raise_business_http_error(
            status.HTTP_403_FORBIDDEN,
            TenantErrorCode.TENANT_DISABLED,
            "租户已被禁用",
        )
    if admin.tenant.status == 2:
        raise_business_http_error(
            status.HTTP_403_FORBIDDEN,
            TenantErrorCode.TENANT_OVERDUE,
            "租户已欠费，请续费后继续使用",
        )
    if (
        admin.tenant.subscription_end_at is not None
        and admin.tenant.subscription_end_at < datetime.utcnow()
    ):
        code = (
            TenantErrorCode.TENANT_TRIAL_EXPIRED
            if admin.tenant.status == 3
            else TenantErrorCode.TENANT_OVERDUE
        )
        raise_business_http_error(
            status.HTTP_403_FORBIDDEN,
            code,
            "订阅已到期，请续费后继续使用",
        )


def _tenant_status_error_for_wechat(admin) -> Optional[str]:
    """微信扫码登录：返回错误文案；可正常登录返回 None。"""
    role_code = admin.role.code if admin.role else None
    is_super_admin = role_code == "SUPER_ADMIN"
    if not admin.tenant_id or is_super_admin or not admin.tenant:
        return None
    if admin.tenant.status == 0:
        return "租户已被禁用"
    if admin.tenant.status == 2:
        return "租户已欠费，请续费后继续使用"
    if (
        admin.tenant.subscription_end_at is not None
        and admin.tenant.subscription_end_at < datetime.utcnow()
    ):
        return "订阅已到期，请续费后继续使用"
    return None


def _build_login_response(admin, access_token: str, refresh_token: str, expires_in: int = None) -> dict:
    """构建登录响应"""
    stores_list = build_stores_list(admin.stores)
    first_store = stores_list[0] if stores_list else None
    response = AdminLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in or settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        admin=build_admin_response(admin),
        store=first_store,
        stores=stores_list,
    )
    return response.model_dump(mode="json", by_alias=True)


def _build_admin_access_token_payload(admin) -> dict:
    payload = {"sub": admin.id, "type": "admin"}
    if admin.tenant_id:
        payload["tenant_id"] = admin.tenant_id
    return payload


def _build_admin_refresh_token_payload(admin) -> dict:
    payload = {"sub": admin.id, "type": "refresh", "role_type": "admin"}
    if admin.tenant_id:
        payload["tenant_id"] = admin.tenant_id
    return payload


def _validate_email_format(email: str) -> bool:
    import re

    if not email or not email.strip():
        return False
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email))


def _normalize_email(email: str) -> str:
    return email.strip().lower()


async def _get_unique_admin_by_email(service: AdminService, email: str) -> Admin:
    admins = await service.list_by_email_global(email)
    if not admins:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该邮箱未绑定管理员账号，请使用其他方式登录")
    if len(admins) > 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该邮箱绑定了多个管理员账号，请使用手机号或账号密码登录")

    admin = admins[0]
    if admin.status != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用，请联系管理员")
    return admin


# ==================== 账号密码登录 ====================

@router.post("/login", summary="管理员登录")
async def admin_login(
    data: AdminLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    password = _decrypt_password(data.password, data.encrypted, f"用户名: {data.username}")
    admin = await service.authenticate(data.username, password)
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误，请检查后重试")
    if admin.status != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用，请联系管理员")

    role_code = admin.role.code if admin.role else None
    is_super_admin = role_code == "SUPER_ADMIN"
    available_stores = [s for s in admin.stores if s.status != 2] if admin.stores else []
    if not is_super_admin and admin.stores and not available_stores:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您所属的门店已被禁用，请联系管理员")

    # 检查租户状态（非平台管理员）
    if admin.tenant_id and not is_super_admin:
        if admin.tenant:
            if admin.tenant.status == 0:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="租户已被禁用")
            if admin.tenant.status == 2:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="租户已欠费，请续费后继续使用")

    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    await service.update_login_info(admin.id, client_ip)

    access_delta, refresh_delta, expires_seconds = await get_token_expire_config(db)
    access_token = create_access_token(data=_build_admin_access_token_payload(admin), expires_delta=access_delta)
    refresh_token = create_refresh_token(data=_build_admin_refresh_token_payload(admin), expires_delta=refresh_delta)
    await store_admin_session(admin, access_token, client_ip, user_agent, db)

    response = AdminLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_seconds,
        admin=build_admin_response(admin),
        store=available_stores and StoreInfo.model_validate(available_stores[0]) or None,
        stores=build_stores_list(available_stores),
    )
    resp = JSONResponse(content=response.model_dump(mode="json", by_alias=True))
    if admin.must_change_password:
        resp.headers["X-Password-Change-Required"] = "true"
    return resp


@router.post("/phone-login", summary="手机号登录")
async def phone_login(
    data: PhoneLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    password = _decrypt_password(data.password, data.encrypted, f"手机号: {data.phone}")
    admin = await service.authenticate_by_phone(data.phone, password)
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="手机号或密码错误，请检查后重试")
    if admin.status != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用，请联系管理员")

    # 检查租户状态
    role_code = admin.role.code if admin.role else None
    is_super_admin = role_code == "SUPER_ADMIN"
    if admin.tenant_id and not is_super_admin:
        if admin.tenant:
            if admin.tenant.status == 0:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="租户已被禁用")
            if admin.tenant.status == 2:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="租户已欠费，请续费后继续使用")

    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    await service.update_login_info(admin.id, client_ip)

    access_delta, refresh_delta, expires_seconds = await get_token_expire_config(db)
    access_token = create_access_token(data=_build_admin_access_token_payload(admin), expires_delta=access_delta)
    refresh_token = create_refresh_token(data=_build_admin_refresh_token_payload(admin), expires_delta=refresh_delta)
    await store_admin_session(admin, access_token, client_ip, user_agent, db)
    resp = JSONResponse(content=_build_login_response(admin, access_token, refresh_token, expires_in=expires_seconds))
    if admin.must_change_password:
        resp.headers["X-Password-Change-Required"] = "true"
    return resp


# ==================== 短信验证码登录 ====================

@router.post("/sms/send", summary="发送验证码")
async def send_sms_code(
    data: SmsCodeRequest,
    db: AsyncSession = Depends(get_db),
):
    from app.infrastructure.sms.service import SmsService

    service = AdminService(db)
    admin = await service.get_by_phone(data.phone)
    if not admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该手机号未注册，请先注册账号")
    if admin.status != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用，请联系管理员")
    try:
        await SmsService.send_code(data.phone, "login")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"message": "验证码已发送"}


@router.post("/sms/login", summary="验证码登录")
async def sms_login(
    data: SmsLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from app.infrastructure.sms.service import SmsService

    service = AdminService(db)
    is_valid = await SmsService.verify_code(data.phone, data.code, "login")
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期，请重新获取")

    admin = await service.get_by_phone(data.phone)
    if not admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该手机号未注册，请先注册账号")
    if admin.status != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用，请联系管理员")

    # 检查租户状态
    role_code = admin.role.code if admin.role else None
    is_super_admin = role_code == "SUPER_ADMIN"
    if admin.tenant_id and not is_super_admin:
        if admin.tenant:
            if admin.tenant.status == 0:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="租户已被禁用")
            if admin.tenant.status == 2:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="租户已欠费，请续费后继续使用")

    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    await service.update_login_info(admin.id, client_ip)

    access_delta, refresh_delta, expires_seconds = await get_token_expire_config(db)
    access_token = create_access_token(data=_build_admin_access_token_payload(admin), expires_delta=access_delta)
    refresh_token = create_refresh_token(data=_build_admin_refresh_token_payload(admin), expires_delta=refresh_delta)
    await store_admin_session(admin, access_token, client_ip, user_agent, db)
    resp = JSONResponse(content=_build_login_response(admin, access_token, refresh_token, expires_in=expires_seconds))
    if admin.must_change_password:
        resp.headers["X-Password-Change-Required"] = "true"
    return resp


@router.post("/email/send-code", summary="发送管理员邮箱验证码")
async def send_admin_email_code(
    data: EmailSendCodeRequest,
    db: AsyncSession = Depends(get_db),
):
    if not _validate_email_format(data.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱格式不正确")

    data.email = _normalize_email(data.email)
    service = AdminService(db)
    await _get_unique_admin_by_email(service, data.email)

    can_send, wait_seconds = await RedisCache.check_email_rate_limit(data.email, "admin_login")
    if not can_send:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"发送过于频繁，请{wait_seconds}秒后重试",
        )

    from app.infrastructure.sms.service import SmsService

    code = SmsService.generate_code()
    await RedisCache.set_email_code(data.email, code, "admin_login")

    try:
        email_service = EmailService(db)
        await email_service.send_verification_code_email(data.email, code, "admin_login")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="验证码发送失败，请稍后重试",
        ) from exc

    if settings.DEBUG:
        return {"message": "验证码发送成功", "code": code}
    return {"message": "验证码发送成功"}


@router.post("/email/login", summary="管理员邮箱验证码登录")
async def admin_email_login(
    data: EmailLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if not _validate_email_format(data.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱格式不正确")

    data.email = _normalize_email(data.email)

    is_valid = await RedisCache.verify_email_code(data.email, data.code, "admin_login")
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期，请重新获取")

    service = AdminService(db)
    admin = await _get_unique_admin_by_email(service, data.email)
    _check_tenant_status_for_login(admin)

    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    await service.update_login_info(admin.id, client_ip)

    access_delta, refresh_delta, expires_seconds = await get_token_expire_config(db)
    access_token = create_access_token(data=_build_admin_access_token_payload(admin), expires_delta=access_delta)
    refresh_token = create_refresh_token(data=_build_admin_refresh_token_payload(admin), expires_delta=refresh_delta)
    await store_admin_session(admin, access_token, client_ip, user_agent, db)
    resp = JSONResponse(content=_build_login_response(admin, access_token, refresh_token, expires_in=expires_seconds))
    if admin.must_change_password:
        resp.headers["X-Password-Change-Required"] = "true"
    return resp


# ==================== 微信扫码登录 ====================

_wechat_scan_tickets: dict = {}


@router.get("/wechat/qrcode", summary="获取微信登录二维码")
async def get_wechat_qrcode():
    import time
    import uuid

    ticket = str(uuid.uuid4())
    expire_seconds = 300
    _wechat_scan_tickets[ticket] = {
        "status": "waiting",
        "created_at": time.time(),
        "expire_at": time.time() + expire_seconds,
        "admin_id": None,
    }
    qrcode_url = f"https://example.com/wechat/scan?ticket={ticket}"
    return WechatQrcodeResponse(
        qrcode_url=qrcode_url,
        ticket=ticket,
        expire_seconds=expire_seconds,
    ).model_dump(by_alias=True)


@router.get("/wechat/check", summary="检查扫码状态")
async def check_wechat_scan(
    ticket: str = Query(...),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    import time

    if ticket not in _wechat_scan_tickets:
        return WechatCheckResponse(status="expired").model_dump(by_alias=True)
    ticket_data = _wechat_scan_tickets[ticket]
    if time.time() > ticket_data["expire_at"]:
        del _wechat_scan_tickets[ticket]
        return WechatCheckResponse(status="expired").model_dump(by_alias=True)
    if ticket_data["status"] == "confirmed" and ticket_data["admin_id"]:
        service = AdminService(db)
        admin = await service.get_by_id(ticket_data["admin_id"])
        if admin and admin.status == 1:
            # 检查租户状态
            role_code = admin.role.code if admin.role else None
            is_super_admin = role_code == "SUPER_ADMIN"
            if admin.tenant_id and not is_super_admin:
                if admin.tenant:
                    if admin.tenant.status == 0:
                        return WechatCheckResponse(status="error", error="租户已被禁用").model_dump(by_alias=True)
                    if admin.tenant.status == 2:
                        return WechatCheckResponse(status="error", error="租户已欠费，请续费后继续使用").model_dump(by_alias=True)

            client_ip = get_client_ip(request)
            await service.update_login_info(admin.id, client_ip)

            access_delta, refresh_delta, expires_seconds = await get_token_expire_config(db)
            access_token = create_access_token(data=_build_admin_access_token_payload(admin), expires_delta=access_delta)
            refresh_token = create_refresh_token(data=_build_admin_refresh_token_payload(admin), expires_delta=refresh_delta)
            del _wechat_scan_tickets[ticket]
            return WechatCheckResponse(
                status="confirmed",
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=expires_seconds,
                admin=build_admin_response(admin),
            ).model_dump(by_alias=True)
    return WechatCheckResponse(status=ticket_data["status"]).model_dump(by_alias=True)


@router.post("/wechat/confirm", summary="确认微信扫码")
async def confirm_wechat_scan(
    ticket: str = Query(...),
    admin_id: str = Query(..., description="管理员ID（模拟扫码确认用）"),
):
    import time

    if ticket not in _wechat_scan_tickets:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="票据不存在或已过期，请重新操作")
    ticket_data = _wechat_scan_tickets[ticket]
    if time.time() > ticket_data["expire_at"]:
        del _wechat_scan_tickets[ticket]
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="票据已过期，请重新操作")
    ticket_data["status"] = "confirmed"
    ticket_data["admin_id"] = admin_id
    return {"message": "扫码确认成功"}
