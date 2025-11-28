"""微信相关 Schema"""
from pydantic import BaseModel, Field
from typing import Optional


class WechatLoginRequest(BaseModel):
    """微信登录请求"""
    code: str = Field(..., description="微信登录凭证 code")


class WechatPhoneRequest(BaseModel):
    """微信获取手机号请求"""
    code: str = Field(..., description="手机号获取凭证 code")
    openid: str = Field(..., description="用户 openid")


class WechatBindPhoneRequest(BaseModel):
    """微信绑定手机号请求"""
    openid: str = Field(..., description="用户 openid")
    phone: str = Field(..., description="手机号")
    code: Optional[str] = Field(None, description="验证码")


class WechatLoginResponse(BaseModel):
    """微信登录响应"""
    is_new_user: bool = Field(..., description="是否新用户")
    need_bindPhone: bool = Field(..., description="是否需要绑定手机号")
    openid: str = Field(..., description="用户 openid")
    access_token: Optional[str] = Field(None, description="访问令牌")
    refresh_token: Optional[str] = Field(None, description="刷新令牌")
    expires_in: Optional[int] = Field(None, description="过期时间(秒)")

