from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class LoginRequest(BaseModel):
    """用户登录请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "phone": "13800138000",
                "password": "123456"
            }
        }
    )
    
    phone: str = Field(..., min_length=11, max_length=11, description="手机号", examples=["13800138000"])
    password: str = Field(..., min_length=6, description="密码", examples=["123456"])


class RegisterRequest(BaseModel):
    """用户注册请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "phone": "13800138000",
                "password": "123456",
                "code": "888888"
            }
        }
    )
    
    phone: str = Field(..., min_length=11, max_length=11, description="手机号", examples=["13800138000"])
    password: str = Field(..., min_length=6, max_length=20, description="密码", examples=["123456"])
    code: Optional[str] = Field(None, description="短信验证码", examples=["888888"])


class TokenResponse(BaseModel):
    """Token响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    access_token: Optional[str] = Field(None, description="访问令牌")
    refresh_token: Optional[str] = Field(None, description="刷新令牌")
    token_type: str = Field("Bearer", description="令牌类型")
    expires_in: Optional[int] = Field(None, description="访问令牌有效期(秒)")


class UserInfo(BaseModel):
    """用户信息（用于登录响应）"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str = Field(..., description="用户ID")
    phone: Optional[str] = Field(None, description="手机号")
    nickname: Optional[str] = Field(None, description="昵称")
    avatar: Optional[str] = Field(None, description="头像URL")
    gender: int = Field(0, description="性别: 0未知 1男 2女")
    status: int = Field(1, description="状态: 0禁用 1正常")


class LoginResponse(BaseModel):
    """登录响应（包含用户信息和令牌）"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    expires_in: int = Field(..., description="访问令牌有效期(秒)")
    user: UserInfo = Field(..., description="用户信息")


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    refresh_token: str = Field(..., description="刷新令牌")


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    old_password: str = Field(..., min_length=6, description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=20, description="新密码")


class ForgotPasswordRequest(BaseModel):
    """忘记密码请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    phone: str = Field(..., min_length=11, max_length=11, description="手机号")
    verification_code: str = Field(..., min_length=4, max_length=6, description="验证码")
    new_password: str = Field(..., min_length=6, max_length=20, description="新密码")


class SendCodeRequest(BaseModel):
    """发送验证码请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    phone: str = Field(..., min_length=11, max_length=11, description="手机号")
    code_type: str = Field(default="reset", description="验证码类型：login/register/reset")


class WechatLoginRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    code: str = Field(..., description="微信登录code")


# ==================== 邮箱认证相关 Schema ====================

class EmailSendCodeRequest(BaseModel):
    """发送邮箱验证码请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    email: str = Field(..., description="邮箱地址", examples=["user@example.com"])
    code_type: str = Field(default="login", description="验证码类型：login/register/reset/bind")


class EmailLoginRequest(BaseModel):
    """邮箱验证码登录请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    email: str = Field(..., description="邮箱地址", examples=["user@example.com"])
    code: str = Field(..., min_length=4, max_length=6, description="验证码", examples=["123456"])


class EmailBindRequest(BaseModel):
    """邮箱绑定请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    email: str = Field(..., description="要绑定的邮箱地址")
    code: str = Field(..., min_length=4, max_length=6, description="验证码")


class EmailUnbindRequest(BaseModel):
    """邮箱解绑请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    code: str = Field(..., min_length=4, max_length=6, description="验证码（发送到当前绑定的邮箱）")


class EmailChangeRequest(BaseModel):
    """邮箱换绑请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    new_email: str = Field(..., description="新邮箱地址")
    new_email_code: str = Field(..., min_length=4, max_length=6, description="新邮箱验证码")
    old_email_code: str = Field(..., min_length=4, max_length=6, description="当前邮箱验证码")
