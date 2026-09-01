"""微信相关 Schema"""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.base import BaseRequestSchema
from app.schemas.response import to_camel


class WechatLoginRequest(BaseRequestSchema):
    """微信登录请求"""

    code: str = Field(..., description="微信登录凭证 code")
    store_id: str | None = Field(None, description="门店ID，用于获取对应门店的微信配置")
    miniapp_instance_id: str | None = Field(None, description="小程序实例ID，优先于门店配置")

class WechatPhoneRequest(BaseRequestSchema):
    """微信获取手机号请求"""

    code: str = Field(..., description="手机号获取凭证 code")
    openid: str = Field(..., description="用户 openid")
    store_id: str | None = Field(None, description="门店ID，用于获取对应门店的微信配置")
    miniapp_instance_id: str | None = Field(None, description="小程序实例ID，优先于门店配置")

class WechatBindPhoneRequest(BaseRequestSchema):
    """微信绑定手机号请求"""

    openid: str = Field(..., description="用户 openid")
    phone: str = Field(..., description="手机号")
    code: str | None = Field(None, description="验证码")

class WechatBindUserInfoRequest(BaseRequestSchema):
    """微信绑定用户信息请求（头像昵称）"""

    openid: str = Field(..., description="用户 openid")
    nickname: str = Field(..., description="用户昵称")
    avatar: str | None = Field(None, description="用户头像URL")

class WechatLoginResponse(BaseModel):
    """微信登录响应
    NOTE: 原 ConfigDict 为 {alias_generator, populate_by_name, by_alias=True}（3 字段，无 from_attributes），
    与 BaseSchema（4 字段）不一致，保留手写配置避免行为变化。
    """
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )

    is_new_user: bool = Field(..., description="是否新用户")
    need_bind_phone: bool = Field(..., description="是否需要绑定手机号")
    openid: str | None = Field(None, description="用户 openid")
    access_token: str | None = Field(None, description="访问令牌")
    refresh_token: str | None = Field(None, description="刷新令牌")
    expires_in: int | None = Field(None, description="过期时间(秒)")
