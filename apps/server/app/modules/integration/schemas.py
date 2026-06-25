"""第三方集成 API 数据模型。"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# 支持的第三方平台
SUPPORTED_PROVIDERS = ["dingtalk", "wecom", "feishu"]


class IntegrationBase(BaseModel):
    """集成配置基础字段。"""
    provider: str = Field(..., description="平台: dingtalk/wecom/feishu")
    name: str = Field(..., max_length=100, description="集成名称")
    app_id: str | None = Field(None, max_length=100, description="应用ID")
    app_secret_ref: str | None = Field(None, max_length=255, description="应用Secret引用(env:VAR)")
    webhook_url: str | None = Field(None, max_length=500, description="群机器人Webhook地址")
    webhook_secret_ref: str | None = Field(None, max_length=255, description="群机器人密钥引用")
    extra_config: dict[str, Any] | None = Field(None, description="扩展配置(agent_id等)")
    status: int = Field(1, description="状态: 0-禁用 1-启用")


class IntegrationCreate(IntegrationBase):
    pass


class IntegrationUpdate(BaseModel):
    """更新集成配置（部分字段）。

    注：app_secret / webhook secret 在更新时单独提交，不随列表返回。
    """
    name: str | None = Field(None, max_length=100)
    app_id: str | None = Field(None, max_length=100)
    app_secret_ref: str | None = Field(None, max_length=255)
    webhook_url: str | None = Field(None, max_length=500)
    webhook_secret_ref: str | None = Field(None, max_length=255)
    extra_config: dict[str, Any] | None = None
    status: int | None = None


class IntegrationResponse(IntegrationBase):
    """集成配置响应。

    注：secret_ref 字段会做脱敏（仅返回 env: 前缀，不暴露明文引用全貌）。
    """
    id: str
    tenant_id: str

    class Config:
        from_attributes = True


class IntegrationBindingResponse(BaseModel):
    """账号绑定关系响应。"""
    id: str
    user_id: str
    user_type: str
    provider: str
    external_id: str
    union_id: str | None = None
    name: str | None = None

    class Config:
        from_attributes = True


class TestConnectionRequest(BaseModel):
    """测试集成连接请求。"""
    provider: str = Field(..., description="平台: dingtalk/wecom/feishu")


class TestConnectionResponse(BaseModel):
    """测试连接结果。"""
    success: bool
    message: str
    detail: dict[str, Any] | None = None


class ProviderInfo(BaseModel):
    """平台信息（前端展示用）。"""
    provider: str
    name: str
    description: str
    configured: bool = False
    status: int = 0
