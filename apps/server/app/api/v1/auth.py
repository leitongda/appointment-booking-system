from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_user
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, RefreshTokenRequest, ChangePasswordRequest
from app.schemas.user import UserResponse
from app.schemas.wechat import WechatLoginRequest, WechatLoginResponse, WechatPhoneRequest, WechatBindPhoneRequest
from app.services.user_service import UserService
from app.services.wechat_service import WechatService
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password, get_password_hash
from app.core.config import settings

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    user_service = UserService(db)
    user = await user_service.authenticate(data.phone, data.password)
    
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="手机号或密码错误")
    
    if user.status != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
    
    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@router.post("/register", response_model=UserResponse)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """用户注册"""
    user_service = UserService(db)
    
    # 检查手机号是否已注册
    existing = await user_service.get_by_phone(data.phone)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="手机号已注册")
    
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

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """刷新Token"""
    payload = decode_token(data.refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的刷新Token")
    
    user_id = payload.get("sub")
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)
    
    if not user or user.status != 1:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")
    
    access_token = create_access_token(data={"sub": user.id})
    new_refresh_token = create_refresh_token(data={"sub": user.id})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """修改密码"""
    user_service = UserService(db)
    user = await user_service.get_by_id(current_user["id"])
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    
    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="原密码错误")
    
    user.password_hash = get_password_hash(data.new_password)
    await db.commit()
    
    return {"message": "密码修改成功"}


# ========== 微信登录 ==========
@router.post("/wechat/login", response_model=WechatLoginResponse)
async def wechat_login(data: WechatLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    微信小程序登录
    - 通过 code 获取 openid
    - 如果用户已存在，返回 token
    - 如果是新用户，返回 openid，需要绑定手机号
    """
    wechat_service = WechatService(db)
    user_service = UserService(db)
    
    try:
        # 获取 openid
        session_info = await wechat_service.code2session(data.code)
        openid = session_info.get("openid")
        
        if not openid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="获取 openid 失败")
        
        # 查找用户
        user = await user_service.get_by_openid(openid)
        
        if user:
            # 已有用户，直接返回 token
            access_token = create_access_token(data={"sub": user.id})
            refresh_token = create_refresh_token(data={"sub": user.id})
            
            return WechatLoginResponse(
                is_new_user=False,
                need_bindPhone=False,
                openid=openid,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )
        else:
            # 新用户，需要绑定手机号
            return WechatLoginResponse(
                is_new_user=True,
                need_bindPhone=True,
                openid=openid,
                access_token=None,
                refresh_token=None,
                expires_in=None
            )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/wechat/phone", response_model=TokenResponse)
async def wechat_get_phone(data: WechatPhoneRequest, db: AsyncSession = Depends(get_db)):
    """
    微信获取手机号并自动登录/注册
    """
    wechat_service = WechatService(db)
    user_service = UserService(db)
    
    try:
        # 获取手机号
        phone = await wechat_service.get_phone_number(data.code)
        
        if not phone:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="获取手机号失败")
        
        # 查找或创建用户
        user = await user_service.get_by_phone(phone)
        
        if user:
            # 更新 openid
            if not user.openid:
                user.openid = data.openid
                await db.commit()
        else:
            # 创建新用户
            from app.schemas.user import UserCreate
            user = await user_service.create(UserCreate(
                phone=phone,
                password="",  # 微信用户无密码
                openid=data.openid
            ))
        
        # 生成 token
        access_token = create_access_token(data={"sub": user.id})
        refresh_token = create_refresh_token(data={"sub": user.id})
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/wechat/bind-phone", response_model=TokenResponse)
async def wechat_bind_phone(data: WechatBindPhoneRequest, db: AsyncSession = Depends(get_db)):
    """
    微信绑定手机号（手动输入方式）
    """
    user_service = UserService(db)
    
    # 验证手机号格式
    import re
    if not re.match(r'^1\d{10}$', data.phone):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="手机号格式不正确")
    
    # 查找或创建用户
    user = await user_service.get_by_phone(data.phone)
    
    if user:
        # 更新 openid
        if user.openid and user.openid != data.openid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该手机号已绑定其他微信")
        user.openid = data.openid
        await db.commit()
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
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
