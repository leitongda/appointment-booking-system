"""第三方集成扫码登录（钉钉/企业微信/飞书）。

实现方式：标准 OAuth2 code 兑换。
1. 前端调用 /qrcode 获取平台扫码授权 URL + state
2. 用户扫码授权后，平台回调前端页面（带 code）
3. 前端用 code 调用 /login 换取登录态
4. 若用户未绑定本地账号，返回 needBindPhone，前端引导绑定手机号

返回结构对齐现有微信登录（WechatCheckResponse / AdminLoginResponse），
复用登录页的 handleLoginSuccess 流程。
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth_deps import get_current_admin
from app.modules.settings.security_helpers import get_token_expire_config
from app.core.security import create_access_token, create_refresh_token
from app.db.session import get_db
from app.infrastructure.integrations import get_provider
from app.middleware.tenant_context import get_current_tenant_id
from app.models.admin import Admin
from app.models.integration import Integration, IntegrationBinding
from app.modules.admin.helpers import build_admin_response, store_admin_session
from app.modules.admin.schemas_integration import (
    IntegrationBindPhoneRequest,
    IntegrationBindRequest,
    IntegrationLoginRequest,
    IntegrationLoginResponse,
    IntegrationQrcodeResponse,
)
from app.modules.admin.service_admins import AdminService
from app.modules.integration.service import IntegrationService
from app.utils.ip import get_client_ip
from sqlalchemy import select

router = APIRouter()
logger = logging.getLogger(__name__)

SUPPORTED_PROVIDERS = ["dingtalk", "wecom", "feishu"]


def _build_admin_access_token_payload(admin: Admin) -> dict:
    payload = {"sub": admin.id, "type": "admin"}
    if admin.tenant_id:
        payload["tenant_id"] = admin.tenant_id
    return payload


def _build_admin_refresh_token_payload(admin: Admin) -> dict:
    payload = {"sub": admin.id, "type": "refresh", "role_type": "admin"}
    if admin.tenant_id:
        payload["tenant_id"] = admin.tenant_id
    return payload


async def _load_integration(db: AsyncSession, provider: str) -> Integration:
    """加载当前租户在该平台的集成配置。"""
    tid = get_current_tenant_id()
    if not tid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="缺少租户上下文")
    stmt = select(Integration).where(
        Integration.tenant_id == tid,
        Integration.provider == provider,
        Integration.status == 1,
    )
    result = await db.execute(stmt)
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"未配置 {provider} 集成或已禁用，请联系管理员",
        )
    return integration


async def _find_admin_by_binding(db: AsyncSession, provider: str, external_id: str, union_id: str | None) -> Admin | None:
    """根据第三方账号绑定关系反查本地 Admin。

    优先按 external_id 查；钉钉/企业微信支持 union_id 时也尝试。
    """
    tid = get_current_tenant_id()
    # 按 external_id 查绑定
    stmt = select(IntegrationBinding).where(
        IntegrationBinding.tenant_id == tid,
        IntegrationBinding.provider == provider,
        IntegrationBinding.external_id == external_id,
        IntegrationBinding.user_type == "admin",
    )
    result = await db.execute(stmt)
    binding = result.scalar_one_or_none()

    # union_id 兜底
    if not binding and union_id:
        stmt = select(IntegrationBinding).where(
            IntegrationBinding.tenant_id == tid,
            IntegrationBinding.provider == provider,
            IntegrationBinding.union_id == union_id,
            IntegrationBinding.user_type == "admin",
        )
        result = await db.execute(stmt)
        binding = result.scalar_one_or_none()

    if not binding:
        return None

    service = AdminService(db)
    return await service.get_by_id(binding.user_id)


# ============================================================
# 获取扫码授权 URL
# ============================================================
@router.get("/qrcode", response_model=IntegrationQrcodeResponse, summary="获取第三方平台扫码授权URL")
async def get_integration_qrcode(
    provider: str = Query(..., description="平台: dingtalk/wecom/feishu"),
    redirect_uri: str = Query(..., description="扫码成功后的前端回调地址"),
    db: AsyncSession = Depends(get_db),
):
    """生成平台扫码登录的授权 URL（前端渲染二维码或跳转平台扫码页）。"""
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"不支持的平台: {provider}")

    integration = await _load_integration(db, provider)
    impl = get_provider(provider)
    if not impl:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Provider 未注册")

    import secrets

    state = secrets.token_urlsafe(16)
    # state 存入 Redis，/login 时校验（CSRF 防护，10分钟过期）
    from app.core.redis import RedisCache

    await RedisCache.set(f"integration:oauth:state:{state}", "1", expire=600)
    url = await impl.get_qrcode_login_url(integration, redirect_uri=redirect_uri, state=state)
    return IntegrationQrcodeResponse(provider=provider, qrcode_url=url, state=state)


# ============================================================
# code 换登录态
# ============================================================
@router.post("/login", response_model=IntegrationLoginResponse, summary="第三方平台扫码登录")
async def integration_login(
    request: Request,
    provider: str = Query(..., description="平台: dingtalk/wecom/feishu"),
    data: IntegrationLoginRequest = None,
    db: AsyncSession = Depends(get_db),
):
    """用平台 OAuth code 兑换登录态。

    - 已绑定本地 Admin：直接签发 token（并记录登录会话）
    - 未绑定：返回 needBindPhone，前端引导绑定手机号
    """
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"不支持的平台: {provider}")
    if data is None or not data.code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="缺少授权 code")

    integration = await _load_integration(db, provider)
    impl = get_provider(provider)
    if not impl:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Provider 未注册")

    # state CSRF 校验（与 /qrcode 生成的 state 比对）
    if data.state:
        from app.core.redis import RedisCache

        expected = await RedisCache.get(f"integration:oauth:state:{data.state}")
        if expected is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="state 已过期或无效")
        await RedisCache.delete(f"integration:oauth:state:{data.state}")

    try:
        user_info = await impl.get_user_info_by_code(integration, data.code)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    external_id = user_info.get("external_id")
    if not external_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未获取到平台用户信息")

    # 查绑定
    admin = await _find_admin_by_binding(db, provider, external_id, user_info.get("union_id"))
    if admin:
        if admin.status != 1:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
        # 传入 request 以记录登录会话与登录历史
        return await _issue_admin_tokens(admin, provider, external_id, user_info, db, request)

    # 未绑定，返回需绑定手机号
    return IntegrationLoginResponse(
        is_new_user=True,
        need_bind_phone=True,
        provider=provider,
        external_id=external_id,
        union_id=user_info.get("union_id"),
        name=user_info.get("name"),
    )


async def _issue_admin_tokens(
    admin: Admin,
    provider: str,
    external_id: str,
    user_info: dict,
    db: AsyncSession,
    request: Request | None = None,
) -> IntegrationLoginResponse:
    """为已绑定 Admin 签发登录态。"""
    access_delta, refresh_delta, expires_seconds = await get_token_expire_config(db)
    access_token = create_access_token(data=_build_admin_access_token_payload(admin), expires_delta=access_delta)
    refresh_token = create_refresh_token(data=_build_admin_refresh_token_payload(admin), expires_delta=refresh_delta)

    # 更新绑定昵称
    if user_info.get("name"):
        tid = get_current_tenant_id()
        stmt = select(IntegrationBinding).where(
            IntegrationBinding.tenant_id == tid,
            IntegrationBinding.provider == provider,
            IntegrationBinding.external_id == external_id,
        )
        result = await db.execute(stmt)
        binding = result.scalar_one_or_none()
        if binding and not binding.name:
            binding.name = user_info["name"]

    if request is not None:
        await store_admin_session(
            admin, access_token, get_client_ip(request), request.headers.get("user-agent", ""), db
        )
    await db.commit()

    return IntegrationLoginResponse(
        is_new_user=False,
        need_bind_phone=False,
        provider=provider,
        external_id=external_id,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_seconds,
        admin=build_admin_response(admin).model_dump(by_alias=True),
    )


# ============================================================
# 绑定手机号（新用户）
# ============================================================
@router.post("/bind-phone", response_model=IntegrationLoginResponse, summary="第三方登录绑定手机号")
async def integration_bind_phone(
    data: IntegrationBindPhoneRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """新用户用手机号匹配本地 Admin 并建立第三方绑定。

    匹配规则：手机号 + 当前租户下的启用 Admin。
    """
    if data.provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"不支持的平台: {data.provider}")

    tid = get_current_tenant_id()
    if not tid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="缺少租户上下文")

    # 按手机号查 Admin
    service = AdminService(db)
    stmt = select(Admin).where(
        Admin.tenant_id == tid,
        Admin.phone == data.phone,
        Admin.status == 1,
    )
    result = await db.execute(stmt)
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该手机号未找到对应管理员账号")

    # 检查是否已被其他平台账号绑定
    exist = select(IntegrationBinding).where(
        IntegrationBinding.tenant_id == tid,
        IntegrationBinding.provider == data.provider,
        IntegrationBinding.external_id == data.external_id,
    )
    existing = (await db.execute(exist)).scalar_one_or_none()
    if existing and existing.user_id != admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该第三方账号已绑定其他管理员")

    # 建立绑定
    integ_service = IntegrationService(db)
    await integ_service.upsert_binding(
        user_id=admin.id,
        user_type="admin",
        provider=data.provider,
        external_id=data.external_id,
        union_id=data.union_id,
        name=data.name,
    )

    user_info = {"name": data.name, "union_id": data.union_id}
    return await _issue_admin_tokens(admin, data.provider, data.external_id, user_info, db, request)


# ============================================================
# 已登录用户主动绑定/解绑
# ============================================================
@router.post("/bind", summary="已登录管理员绑定第三方账号")
async def bind_integration_account(
    provider: str = Query(...),
    data: IntegrationBindRequest = None,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """已登录用户主动绑定第三方账号（扫码授权后调用）。"""
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"不支持的平台: {provider}")
    if data is None or not data.code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="缺少授权 code")

    integration = await _load_integration(db, provider)
    impl = get_provider(provider)
    if not impl:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Provider 未注册")
    try:
        user_info = await impl.get_user_info_by_code(integration, data.code)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    integ_service = IntegrationService(db)
    await integ_service.upsert_binding(
        user_id=current_admin["id"],
        user_type="admin",
        provider=provider,
        external_id=user_info.get("external_id"),
        union_id=user_info.get("union_id"),
        name=user_info.get("name"),
    )
    await db.commit()
    return {"message": "绑定成功", "external_id": user_info.get("external_id")}


@router.get("/bindings", summary="获取当前管理员的第三方账号绑定")
async def list_my_bindings(
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """获取当前登录管理员已绑定的第三方平台账号。"""
    tid = get_current_tenant_id()
    stmt = select(IntegrationBinding).where(
        IntegrationBinding.tenant_id == tid,
        IntegrationBinding.user_id == current_admin["id"],
        IntegrationBinding.user_type == "admin",
    )
    result = await db.execute(stmt)
    items = result.scalars().all()
    return {
        "data": [
            {
                "id": b.id,
                "provider": b.provider,
                "external_id": b.external_id,
                "name": b.name,
            }
            for b in items
        ]
    }
