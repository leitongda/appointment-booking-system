from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_user
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, RefreshTokenRequest, ChangePasswordRequest, LoginResponse, UserInfo
from app.schemas.user import UserResponse
from app.schemas.wechat import WechatLoginRequest, WechatLoginResponse, WechatPhoneRequest, WechatBindPhoneRequest, WechatBindUserInfoRequest
from app.schemas.response import ErrorResponse
from app.modules.users.service import UserService
from app.infrastructure.wechat.service import WechatService
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password, get_password_hash
from app.core.config import settings

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
    
    user.password_hash = get_password_hash(data.new_password)
    await db.commit()
    
    return {"message": "密码修改成功"}


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
