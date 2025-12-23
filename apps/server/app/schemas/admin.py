from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


# ========== 短信登录 ==========
class SmsCodeRequest(BaseModel):
    """发送短信验证码请求"""
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")


class SmsLoginRequest(BaseModel):
    """短信验证码登录请求"""
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")
    code: str = Field(..., min_length=4, max_length=6, description="验证码")


# ========== 手机号密码登录 ==========
class PhoneLoginRequest(BaseModel):
    """手机号+密码登录请求"""
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")
    password: str = Field(..., min_length=6, description="密码")
    encrypted: bool = Field(default=False, description="密码是否已加密")


# ========== 账号密码登录 ==========
class AdminLoginRequest(BaseModel):
    """管理员账号密码登录请求"""
    username: str = Field(..., min_length=2, description="用户名")
    password: str = Field(..., min_length=6, description="密码")
    encrypted: bool = Field(default=False, description="密码是否已加密")


# ========== 微信扫码登录 ==========
class WechatQrcodeResponse(BaseModel):
    """微信扫码登录二维码响应"""
    qrcode_url: str = Field(..., description="二维码图片URL")
    ticket: str = Field(..., description="轮询票据")
    expire_seconds: int = Field(default=300, description="二维码有效期(秒)")


class WechatCheckRequest(BaseModel):
    """检查微信扫码状态请求"""
    ticket: str = Field(..., description="轮询票据")


class WechatCheckResponse(BaseModel):
    """检查微信扫码状态响应"""
    status: str = Field(..., description="状态: waiting/scanned/confirmed/expired")
    access_token: Optional[str] = Field(None, description="登录成功时返回的token")
    refresh_token: Optional[str] = Field(None, description="刷新token")
    expires_in: Optional[int] = Field(None, description="token有效期(秒)")


# ========== 通用登录响应 ==========
class AdminLoginResponse(BaseModel):
    """管理员登录响应"""
    access_token: str = Field(..., alias="accessToken")
    refresh_token: str = Field(..., alias="refreshToken")
    expires_in: int = Field(..., alias="expiresIn")
    admin: dict = Field(..., description="管理员信息")

    class Config:
        populate_by_name = True


# ========== 管理员列表响应 ==========
def to_camel(string: str) -> str:
    """转换 snake_case 为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class AdminListResponse(BaseModel):
    """管理员列表响应（用于门店用户列表等场景）"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )
    
    id: str
    username: str
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None
    role_id: Optional[str] = None
    status: int = 1
    created_at: Optional[datetime] = None
