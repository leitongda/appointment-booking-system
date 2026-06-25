"""第三方集成 OAuth 登录数据模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class IntegrationLoginRequest(BaseModel):
    """第三方平台 OAuth 登录请求（前端用 code 换登录态）。"""
    code: str = Field(..., description="平台 OAuth 回调返回的授权 code")
    state: str | None = Field(None, description="OAuth state（防 CSRF）")


class IntegrationLoginResponse(BaseModel):
    """第三方平台登录响应（结构对齐 WechatCheckResponse / AdminLoginResponse）。"""
    is_new_user: bool = Field(False, serialization_alias="isNewUser", description="是否为新用户（需绑定手机号）")
    need_bind_phone: bool = Field(False, serialization_alias="needBindPhone", description="是否需要绑定手机号")
    provider: str = Field(..., description="平台: dingtalk/wecom/feishu")
    external_id: str | None = Field(None, serialization_alias="externalId", description="平台用户ID（绑定时回传）")
    union_id: str | None = Field(None, serialization_alias="unionId")
    name: str | None = Field(None, description="平台昵称")
    # 已绑定用户直接返回登录态
    access_token: str | None = Field(None, serialization_alias="accessToken")
    refresh_token: str | None = Field(None, serialization_alias="refreshToken")
    expires_in: int | None = Field(None, serialization_alias="expiresIn")
    admin: dict | None = None

    class Config:
        populate_by_name = True


class IntegrationBindPhoneRequest(BaseModel):
    """新用户绑定手机号完成登录。"""
    provider: str = Field(..., description="平台: dingtalk/wecom/feishu")
    external_id: str = Field(..., serialization_alias="externalId", description="平台用户ID")
    union_id: str | None = Field(None, serialization_alias="unionId")
    name: str | None = None
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")

    class Config:
        populate_by_name = True


class IntegrationQrcodeResponse(BaseModel):
    """获取扫码登录二维码/授权URL。"""
    provider: str
    qrcode_url: str = Field(..., serialization_alias="qrcodeUrl", description="扫码授权URL")
    state: str = Field(..., description="OAuth state（回调时回传校验）")
    expire_seconds: int = Field(300, serialization_alias="expireSeconds")

    class Config:
        populate_by_name = True


class IntegrationBindRequest(BaseModel):
    """已登录用户主动绑定第三方账号（传入 code）。"""
    code: str = Field(..., description="平台 OAuth 授权 code")
    state: str | None = None
