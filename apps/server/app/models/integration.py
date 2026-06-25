"""第三方集成数据模型

存储钉钉 / 企业微信 / 飞书 的租户级应用凭证与用户账号绑定关系。

凭证安全策略（沿用 MiniappInstance 模式）：
- app_id / webhook_url 等非敏感信息直接入库
- app_secret / webhook 加签密钥等敏感信息以 `env:VAR_NAME` 引用形式入库，
  实际值通过 app.common.secret_refs.resolve_secret_ref() 解析为环境变量
"""
import uuid

from sqlalchemy import JSON, Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base, TimestampMixin


def _uuid() -> str:
    return str(uuid.uuid4())


class Integration(Base, AuditMixin):
    """租户级第三方集成配置。

    每个租户对每个平台（dingtalk/wecom/feishu）最多一条启用记录。
    同时承载「企业自建应用」（用于点对点工作通知 / SSO / 通讯录同步）
    与「群机器人」（用于群消息推送）两套凭证。
    """

    __tablename__ = "integrations"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    # 平台标识：dingtalk / wecom / feishu
    provider = Column(String(20), nullable=False, comment="集成平台: dingtalk/wecom/feishu")
    name = Column(String(100), nullable=False, comment="集成名称（便于识别）")

    # ---- 企业自建应用凭证（点对点消息 / SSO / 通讯录）----
    # 钉钉: AppKey + AppSecret ; 企业微信: CorpID + Secret(+AgentID) ; 飞书: AppID + AppSecret
    app_id = Column(String(100), nullable=True, comment="应用ID: 钉钉AppKey / 企业微信CorpID / 飞书AppID")
    app_secret_ref = Column(String(255), nullable=True, comment="应用Secret引用，例如 env:DINGTALK_APP_SECRET")

    # ---- 群机器人凭证（群消息推送）----
    webhook_url = Column(String(500), nullable=True, comment="群机器人 Webhook 地址")
    webhook_secret_ref = Column(String(255), nullable=True, comment="群机器人加签密钥引用")

    # ---- 扩展配置（平台差异化字段）----
    # 钉钉: {"agent_id": "...", "robot_code": "..."}
    # 企业微信: {"agent_id": "..."}
    # 飞书: {"app_type": "internal", "robot_code": "..."}
    extra_config = Column(JSON, nullable=True, comment="平台扩展配置(JSON)")

    status = Column(Integer, default=1, comment="状态: 0-禁用 1-启用")

    tenant = relationship("Tenant", backref="integrations")

    __table_args__ = (
        UniqueConstraint("tenant_id", "provider", name="uq_integrations_tenant_provider"),
        {"comment": "第三方集成配置表"},
    )


class IntegrationBinding(Base, TimestampMixin):
    """用户账号与第三方平台的绑定关系。

    用于：
    - 扫码登录（SSO）：通过 external_id / union_id 反查本地用户
    - 点对点消息推送：查收件人的第三方 userId 以精准投递
    """

    __tablename__ = "integration_bindings"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    user_id = Column(String(36), nullable=False, index=True, comment="本地用户ID")
    user_type = Column(String(20), nullable=False, comment="用户类型: admin/doctor/user")
    provider = Column(String(20), nullable=False, comment="集成平台: dingtalk/wecom/feishu")
    external_id = Column(String(100), nullable=False, comment="平台用户ID: 钉钉userId / 企业微信userid / 飞书open_id")
    union_id = Column(String(100), nullable=True, comment="跨应用unionId（钉钉/企业微信支持）")
    name = Column(String(100), nullable=True, comment="平台侧昵称（同步用）")

    __table_args__ = (
        UniqueConstraint("tenant_id", "provider", "external_id", name="uq_ib_tenant_provider_ext"),
        UniqueConstraint("tenant_id", "provider", "user_id", name="uq_ib_tenant_provider_user"),
        {"comment": "第三方账号绑定关系表"},
    )
