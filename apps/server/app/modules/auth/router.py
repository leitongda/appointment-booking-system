from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.api.deps import get_current_user
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    RefreshTokenRequest,
    ChangePasswordRequest,
    LoginResponse,
    UserInfo,
    ForgotPasswordRequest,
    SendCodeRequest,
    EmailSendCodeRequest,
    EmailLoginRequest,
    EmailBindRequest,
    EmailUnbindRequest,
    EmailChangeRequest,
)
from app.schemas.user import UserResponse
from app.schemas.wechat import WechatLoginRequest, WechatLoginResponse, WechatPhoneRequest, WechatBindPhoneRequest, WechatBindUserInfoRequest
from app.schemas.response import ErrorResponse
from app.modules.users.service import UserService
from app.infrastructure.wechat.service import WechatService
from app.infrastructure.email.service import EmailService
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password, get_password_hash
from app.core.redis import RedisCache
from app.core.config import settings
from app.common.account_sync import AccountSyncService

router = APIRouter()

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="用户登录",
    description="""用户通过手机号和密码登录系统。

**功能说明：**
- 验证用户手机号和密码
- 检查账号状态是否正常
- 生成访问令牌和刷新令牌
- 返回用户基本信息

**请求示例：**
```json
{
  "phone": "13800138000",
  "password": "password123"
}
```

**响应示例：**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600,
  "user": {
    "id": "user_123",
    "phone": "13800138000",
    "nickname": "张医生",
    "avatar": "https://example.com/avatar.jpg",
    "gender": 1,
    "status": 1
  }
}
```

**错误响应：**
- 401: 手机号或密码错误
- 403: 账号已被禁用
""",
    responses={
        401: {"model": ErrorResponse, "description": "手机号或密码错误"},
        403: {"model": ErrorResponse, "description": "账号已被禁用"},
    }
)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    user_service = UserService(db)
    user = await user_service.authenticate(data.phone, data.password)
    
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="手机号或密码错误，请检查后重试")
    
    if user.status != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用，请联系管理员")
    
    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserInfo(
            id=user.id,
            phone=user.phone,
            nickname=user.nickname,
            avatar=user.avatar,
            gender=user.gender if user.gender is not None else 0,
            status=user.status
        )
    )

@router.post(
    "/register",
    response_model=UserResponse,
    summary="用户注册",
    description="""新用户注册账号。

**功能说明：**
- 验证手机号格式和唯一性
- 创建用户账号
- 默认状态为正常
- 注册成功后可直接登录

**请求示例：**
```json
{
  "phone": "13800138000",
  "password": "password123",
  "nickname": "张医生",
  "gender": 1
}
```

**响应示例：**
```json
{
  "id": "user_123",
  "phone": "13800138000",
  "nickname": "张医生",
  "avatar": null,
  "gender": 1,
  "status": 1,
  "created_at": "2024-01-15T10:30:00Z"
}
```

**错误响应：**
- 400: 手机号已注册或格式不正确

**字段说明：**
- phone: 手机号，11位数字，必须唯一
- password: 密码，最少6位
- nickname: 昵称，可选
- gender: 性别，0-未知, 1-男, 2-女
""",
    responses={
        400: {"model": ErrorResponse, "description": "手机号已注册"},
    }
)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """用户注册"""
    user_service = UserService(db)

    # 检查手机号是否已注册
    existing = await user_service.get_by_phone(data.phone)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="手机号已注册，请直接登录")

    # 密码策略校验（用户注册使用当前租户上下文）
    from app.modules.tenants.password_policy import get_tenant_password_policy, PasswordPolicyValidator
    from app.middleware.tenant_context import get_current_tenant_id
    tenant_id = get_current_tenant_id()
    policy = await get_tenant_password_policy(db, tenant_id)
    validator = PasswordPolicyValidator(policy)
    is_valid, errors = validator.validate(data.password, phone=data.phone)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="; ".join(errors))

    from app.schemas.user import UserCreate
    user = await user_service.create(UserCreate(phone=data.phone, password=data.password))

    return UserResponse(
        id=user.id,
        phone=user.phone,
        nickname=user.nickname,
        avatar=user.avatar,
        gender=user.gender,
        status=user.status
    )

@router.post("/refresh", response_model=TokenResponse, summary="刷新Token")
async def refresh_token(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """刷新Token"""
    payload = decode_token(data.refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="身份验证失败，请重新登录")
    
    user_id = payload.get("sub")
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)
    
    if not user or user.status != 1:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不存在或已被禁用，请检查后重试")
    
    access_token = create_access_token(data={"sub": user.id})
    new_refresh_token = create_refresh_token(data={"sub": user.id})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@router.post("/change-password", summary="修改密码")
async def change_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """修改密码"""
    user_service = UserService(db)
    user = await user_service.get_by_id(current_user["id"])

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在，请检查后重试")

    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="原密码错误，请重新输入")

    # 验证新旧密码不能相同
    if data.old_password == data.new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码不能与原密码相同")

    # 密码长度验证
    if not (6 <= len(data.new_password) <= 20):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="密码长度必须为6-20位")

    # 密码策略校验
    from app.modules.tenants.password_policy import get_tenant_password_policy, PasswordPolicyValidator
    from app.middleware.tenant_context import get_current_tenant_id
    tenant_id = get_current_tenant_id()
    policy = await get_tenant_password_policy(db, tenant_id)
    validator = PasswordPolicyValidator(policy)
    is_valid, errors = validator.validate(data.new_password, phone=user.phone)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="; ".join(errors))

    user.password_hash = get_password_hash(data.new_password)
    await db.flush()

    # 双写同步: 密码变更同步到 accounts
    await AccountSyncService.sync_user_to_account(
        db, user.id, operator_id=current_user["id"]
    )

    await db.commit()

    return {"message": "密码修改成功"}


@router.post("/send-code", summary="发送验证码")
async def send_code(
    data: SendCodeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    发送短信验证码

    **功能说明**：
    - 发送验证码到指定手机号
    - 支持登录、注册、重置密码等场景
    - 60秒内不能重复发送

    **请求示例**：
    ```json
    {
      "phone": "13800138000",
      "codeType": "reset"
    }
    ```

    **验证码类型**：
    - login: 登录验证码
    - register: 注册验证码
    - reset: 重置密码验证码
    """
    from app.infrastructure.sms.service import SmsService
    import re

    # 验证手机号格式
    if not re.match(r'^1\d{10}$', data.phone):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="手机号格式不正确")

    # 检查用户是否存在（重置密码场景需要验证）
    user_service = UserService(db)
    if data.code_type == "reset":
        user = await user_service.get_by_phone(data.phone)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该手机号未注册")

    try:
        code = await SmsService.send_code(data.phone, data.code_type)
        # 开发环境返回验证码，生产环境不返回
        from app.core.config import settings
        if settings.DEBUG:
            return {"message": "验证码发送成功", "code": code}
        return {"message": "验证码发送成功"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/forgot-password", summary="忘记密码")
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    通过手机号和验证码重置密码

    **功能说明**：
    - 验证手机号和验证码
    - 重置用户密码
    - 无需旧密码即可重置

    **请求示例**：
    ```json
    {
      "phone": "13800138000",
      "verificationCode": "123456",
      "newPassword": "newpass123"
    }
    ```

    **业务规则**：
    - 验证码必须正确且未过期
    - 新密码需符合密码策略
    - 密码长度 6-20 位
    """
    from app.infrastructure.sms.service import SmsService
    from app.middleware.tenant_context import get_current_tenant_id
    import re

    # 验证手机号格式
    if not re.match(r'^1\d{10}$', data.phone):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="手机号格式不正确")

    # 验证密码长度
    if not (6 <= len(data.new_password) <= 20):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="密码长度必须为6-20位")

    # 查找用户
    user_service = UserService(db)
    user = await user_service.get_by_phone(data.phone)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该手机号未注册")

    # 验证验证码
    tenant_id = get_current_tenant_id()
    is_valid = await SmsService.verify_code(data.phone, data.verification_code, "reset", tenant_id)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")

    # 密码策略校验
    from app.modules.tenants.password_policy import get_tenant_password_policy, PasswordPolicyValidator
    policy = await get_tenant_password_policy(db, tenant_id)
    validator = PasswordPolicyValidator(policy)
    is_valid, errors = validator.validate(data.new_password, phone=user.phone)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="; ".join(errors))

    # 更新密码
    user.password_hash = get_password_hash(data.new_password)
    await db.flush()

    # 双写同步: 密码重置同步到 accounts
    await AccountSyncService.sync_user_to_account(
        db, user.id, operator_id=None
    )

    await db.commit()

    return {"message": "密码重置成功，请使用新密码登录"}


# ========== 微信登录 ==========
@router.post("/wechat/login", response_model=WechatLoginResponse, summary="微信登录")
async def wechat_login(data: WechatLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    微信小程序登录
    - 通过 code 获取 openid 和 unionid
    - 如果用户已存在，返回 token
    - 如果是新用户，返回 openid，需要绑定手机号
    """
    wechat_service = WechatService(
        db,
        store_id=data.store_id,
        miniapp_instance_id=data.miniapp_instance_id,
    )
    user_service = UserService(db)
    
    try:
        # 获取 openid 和 unionid
        session_info = await wechat_service.code2session(data.code)
        openid = session_info.get("openid")
        unionid = session_info.get("unionid")
        
        if not openid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="微信授权失败，请重试")
        
        # 优先通过 unionid 查找用户（跨应用关联）
        user = None
        if unionid:
            user = await user_service.get_by_unionid(unionid)
        if not user:
            user = await user_service.get_by_openid(openid)
        
        if user:
            # 已有用户，更新 unionid（如果之前没有）
            if unionid and not user.unionid:
                await user_service.update_wechat_info(user.id, {"unionid": unionid})
            
            # 直接返回 token
            access_token = create_access_token(data={"sub": user.id})
            refresh_token = create_refresh_token(data={"sub": user.id})
            
            return WechatLoginResponse(
                is_new_user=False,
                need_bind_phone=False,
                openid=openid,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )
        else:
            # 新用户，需要绑定手机号
            return WechatLoginResponse(
                is_new_user=True,
                need_bind_phone=True,
                openid=openid,
                access_token=None,
                refresh_token=None,
                expires_in=None
            )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/wechat/phone", response_model=LoginResponse, summary="微信获取手机号")
async def wechat_get_phone(data: WechatPhoneRequest, db: AsyncSession = Depends(get_db)):
    """
    微信获取手机号并自动登录/注册
    """
    wechat_service = WechatService(
        db,
        store_id=data.store_id,
        miniapp_instance_id=data.miniapp_instance_id,
    )
    user_service = UserService(db)
    
    try:
        # 获取手机号
        phone = await wechat_service.get_phone_number(data.code)
        
        if not phone:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="获取手机号失败，请重试")
        
        # 查找或创建用户
        user = await user_service.get_by_phone(phone)
        
        if user:
            # 更新 openid 和 unionid
            update_data = {}
            if not user.openid:
                user.openid = data.openid
                await db.flush()
                # 双写同步: openid 更新
                await AccountSyncService.sync_user_to_account(db, user.id)
                await db.commit()
            if hasattr(data, 'unionid') and data.unionid:
                update_data["unionid"] = data.unionid
            if update_data:
                await user_service.update_wechat_info(user.id, update_data)
            await db.refresh(user)
        else:
            # 创建新用户
            from app.schemas.user import UserCreate
            user = await user_service.create(UserCreate(
                phone=phone,
                password="",  # 微信用户无密码
                openid=data.openid,
                unionid=getattr(data, 'unionid', None)
            ))
        
        # 生成 token
        access_token = create_access_token(data={"sub": user.id})
        refresh_token = create_refresh_token(data={"sub": user.id})
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserInfo(
                id=user.id,
                phone=user.phone,
                nickname=user.nickname,
                avatar=user.avatar,
                gender=user.gender if user.gender is not None else 0,
                status=user.status
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/wechat/bind-phone", response_model=LoginResponse, summary="微信绑定手机号")
async def wechat_bind_phone(data: WechatBindPhoneRequest, db: AsyncSession = Depends(get_db)):
    """
    微信绑定手机号（手动输入方式）
    """
    user_service = UserService(db)
    
    # 验证手机号格式
    import re
    if not re.match(r'^1\d{10}$', data.phone):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="手机号格式不正确，请检查后重试")
    
    # 查找或创建用户
    user = await user_service.get_by_phone(data.phone)
    
    if user:
        # 更新 openid
        if user.openid and user.openid != data.openid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该手机号已绑定其他微信账号")
        user.openid = data.openid
        await db.flush()
        # 双写同步: openid 绑定同步
        await AccountSyncService.sync_user_to_account(db, user.id)
        await db.commit()
        await db.refresh(user)
    else:
        # 创建新用户
        from app.schemas.user import UserCreate
        user = await user_service.create(UserCreate(
            phone=data.phone,
            password="",
            openid=data.openid
        ))
    
    # 生成 token
    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserInfo(
            id=user.id,
            phone=user.phone,
            nickname=user.nickname,
            avatar=user.avatar,
            gender=user.gender if user.gender is not None else 0,
            status=user.status
        )
    )


@router.post("/wechat/bind-userinfo", response_model=LoginResponse, summary="微信绑定用户信息")
async def wechat_bind_userinfo(data: WechatBindUserInfoRequest, db: AsyncSession = Depends(get_db)):
    """
    微信绑定用户信息（头像昵称）并完成登录
    - 不需要手机号，直接使用 openid 创建/更新用户
    - 同时存储微信原始信息到专用字段
    """
    user_service = UserService(db)
    
    # 查找或创建用户
    user = await user_service.get_by_openid(data.openid)
    
    if user:
        # 更新用户信息和微信信息
        wechat_info = {}
        if data.nickname:
            user.nickname = data.nickname
            wechat_info["nickname"] = data.nickname
        if data.avatar:
            user.avatar = data.avatar
            wechat_info["avatar"] = data.avatar
        if hasattr(data, 'unionid') and data.unionid:
            wechat_info["unionid"] = data.unionid
        
        if wechat_info:
            await user_service.update_wechat_info(user.id, wechat_info)
        else:
            await db.commit()
        await db.refresh(user)
    else:
        # 创建新用户（不需要手机号，phone 传空会被 service 层转为 None）
        from app.schemas.user import UserCreate
        user = await user_service.create(UserCreate(
            phone="",  # 微信用户无手机号，service 层会转为 None
            password="",
            openid=data.openid,
            unionid=getattr(data, 'unionid', None),
            nickname=data.nickname or "微信用户",
            avatar=data.avatar or ""
        ))
    
    # 生成 token
    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserInfo(
            id=user.id,
            phone=user.phone or "",
            nickname=user.nickname,
            avatar=user.avatar,
            gender=user.gender if user.gender is not None else 0,
            status=user.status
        )
    )


# ==================== 邮箱认证相关 ====================

def _validate_email_format(email: str) -> bool:
    """简单邮箱格式校验"""
    import re
    if not email or not email.strip():
        return False
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))


def _normalize_email(email: str) -> str:
    """规范化邮箱：去空格、转小写"""
    return email.strip().lower()


@router.post("/email/send-code", summary="发送邮箱验证码")
async def email_send_code(
    data: EmailSendCodeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    发送邮箱验证码

    **功能说明**：
    - 发送验证码到指定邮箱
    - 支持登录、注册、重置密码、绑定等场景
    - 60秒内不能重复发送

    **验证码类型**：
    - login: 登录验证码
    - register: 注册验证码
    - reset: 重置密码验证码
    - bind: 绑定邮箱验证码
    """
    import re

    if not _validate_email_format(data.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱格式不正确")

    data.email = _normalize_email(data.email)

    # 重置密码场景需要验证邮箱是否已绑定
    user_service = UserService(db)
    if data.code_type == "reset":
        user = await user_service.get_by_email(data.email)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该邮箱未注册")

    # 检查发送频率
    can_send, wait_seconds = await RedisCache.check_email_rate_limit(data.email, data.code_type)
    if not can_send:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"发送过于频繁，请{wait_seconds}秒后重试",
        )

    # 生成并存储验证码
    from app.infrastructure.sms.service import SmsService
    code = SmsService.generate_code()
    await RedisCache.set_email_code(data.email, code, data.code_type)

    # 发送邮件
    try:
        email_service = EmailService(db)
        await email_service.send_verification_code_email(data.email, code, data.code_type)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="验证码发送失败，请稍后重试",
        )

    # 开发环境返回验证码
    if settings.DEBUG:
        return {"message": "验证码发送成功", "code": code}
    return {"message": "验证码发送成功"}


@router.post("/email/login", response_model=LoginResponse, summary="邮箱验证码登录")
async def email_login(
    data: EmailLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    邮箱验证码登录（支持自动注册）

    **功能说明**：
    - 通过邮箱 + 验证码登录
    - 若邮箱未注册且当前租户允许，自动注册新用户（仅患者类型）
    - 若邮箱已绑定已有账号，直接登录

    **业务规则**：
    - 管理员/医生邮箱必须已绑定才能登录，不支持自动注册
    - 患者邮箱未注册时自动创建新账号
    """
    if not _validate_email_format(data.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱格式不正确")

    data.email = _normalize_email(data.email)

    # 校验验证码
    is_valid = await RedisCache.verify_email_code(data.email, data.code, "login")
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")

    user_service = UserService(db)
    user = await user_service.get_by_email(data.email)

    if not user:
        # 邮箱未注册 → 自动注册新用户（患者）
        from app.schemas.user import UserCreate
        user = await user_service.create(UserCreate(
            email=data.email,
            password="",  # 邮箱注册用户无密码
            nickname=f"用户{data.email.split('@')[0]}",
        ))

    if user.status != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用，请联系管理员")

    # 登录信息更新（Account 表，通过双写同步处理）
    # 注意: User 模型无 last_login_at/ip 字段，由 AccountSyncService 同步到 Account 表

    # 生成 token
    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserInfo(
            id=user.id,
            phone=user.phone or "",
            nickname=user.nickname,
            avatar=user.avatar,
            gender=user.gender if user.gender is not None else 0,
            status=user.status,
        ),
    )


@router.post("/email/bind", summary="绑定邮箱")
async def email_bind(
    data: EmailBindRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    绑定邮箱到当前账号

    **功能说明**：
    - 需要已登录状态
    - 验证邮箱验证码后绑定
    - 一个邮箱在同一租户下只能绑定一个账号
    """
    if not _validate_email_format(data.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱格式不正确")

    data.email = _normalize_email(data.email)

    # 校验验证码
    is_valid = await RedisCache.verify_email_code(data.email, data.code, "bind")
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")

    # 检查邮箱是否已被其他账号绑定
    user_service = UserService(db)
    existing = await user_service.get_by_email(data.email)
    if existing and existing.id != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该邮箱已被其他账号绑定")

    # 更新 User 表
    user = await user_service.get_by_id(current_user["id"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    user.email = data.email
    await db.flush()

    # 双写同步到 Account 表
    await AccountSyncService.sync_user_to_account(db, user.id, operator_id=user.id)

    await db.commit()
    return {"message": "邮箱绑定成功"}


@router.post("/email/unbind", summary="解绑邮箱")
async def email_unbind(
    data: EmailUnbindRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    解绑当前账号的邮箱

    **功能说明**：
    - 需要已登录状态
    - 需要验证码确认（发送到当前绑定的邮箱）
    """
    user_service = UserService(db)
    user = await user_service.get_by_id(current_user["id"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if not user.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前账号未绑定邮箱")

    # 校验验证码（发送到当前绑定的邮箱）
    is_valid = await RedisCache.verify_email_code(user.email, data.code, "bind")
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")

    # 清除邮箱
    user.email = None
    await db.flush()

    # 双写同步
    await AccountSyncService.sync_user_to_account(db, user.id, operator_id=user.id)

    await db.commit()
    return {"message": "邮箱解绑成功"}


@router.post("/email/change", summary="换绑邮箱")
async def email_change(
    data: EmailChangeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    换绑邮箱

    **功能说明**：
    - 需要已登录状态
    - 需要新旧邮箱的验证码同时确认
    - 新邮箱不能已被其他账号绑定
    """
    if not _validate_email_format(data.new_email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新邮箱格式不正确")

    data.new_email = _normalize_email(data.new_email)

    user_service = UserService(db)
    user = await user_service.get_by_id(current_user["id"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if not user.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前账号未绑定邮箱，请先绑定")

    # 校验旧邮箱验证码
    is_old_valid = await RedisCache.verify_email_code(user.email, data.old_email_code, "bind")
    if not is_old_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前邮箱验证码错误或已过期")

    # 校验新邮箱验证码
    is_new_valid = await RedisCache.verify_email_code(data.new_email, data.new_email_code, "bind")
    if not is_new_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新邮箱验证码错误或已过期")

    # 检查新邮箱是否已被其他账号绑定
    existing = await user_service.get_by_email(data.new_email)
    if existing and existing.id != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新邮箱已被其他账号绑定")

    # 更新邮箱
    user.email = data.new_email
    await db.flush()

    # 双写同步
    await AccountSyncService.sync_user_to_account(db, user.id, operator_id=user.id)

    await db.commit()
    return {"message": "邮箱换绑成功"}