from pydantic import BaseModel, Field
from typing import Optional


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
