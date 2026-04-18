from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base, AuditMixin
import uuid


class Company(Base, AuditMixin):
    """租户下的公司/结算主体。"""

    __tablename__ = "companies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    name = Column(String(100), nullable=False, comment="公司主体名称")
    code = Column(String(50), nullable=True, comment="主体编码，租户内唯一")
    unified_social_credit_code = Column(String(50), nullable=True, comment="统一社会信用代码")
    contact_name = Column(String(100), nullable=True, comment="联系人")
    contact_phone = Column(String(20), nullable=True, comment="联系电话")
    status = Column(Integer, default=1, comment="状态: 0禁用 1启用")

    tenant = relationship("Tenant", backref="companies")

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_companies_tenant_code"),
        {"comment": "公司/结算主体表"},
    )


class AppTemplate(Base, AuditMixin):
    """小程序模板定义。"""

    __tablename__ = "app_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), nullable=False, unique=True, comment="模板编码")
    name = Column(String(100), nullable=False, comment="模板名称")
    description = Column(Text, nullable=True, comment="模板描述")
    default_config = Column(Text, nullable=True, comment="默认配置(JSON)")
    status = Column(Integer, default=1, comment="状态: 0禁用 1启用")


class TemplateVersion(Base, AuditMixin):
    """模板版本。"""

    __tablename__ = "template_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    template_id = Column(String(36), ForeignKey("app_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(String(50), nullable=False, comment="模板版本号")
    source_ref = Column(String(255), nullable=True, comment="模板源码引用")
    schema_version = Column(String(50), nullable=True, comment="模板配置结构版本")
    changelog = Column(Text, nullable=True, comment="版本变更说明")
    status = Column(Integer, default=1, comment="状态: 0禁用 1启用")

    template = relationship("AppTemplate", backref="versions")

    __table_args__ = (
        UniqueConstraint("template_id", "version", name="uq_template_versions_template_version"),
        {"comment": "模板版本表"},
    )


class MiniappInstance(Base, AuditMixin):
    """租户的小程序实例。"""

    __tablename__ = "miniapp_instances"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    template_id = Column(String(36), ForeignKey("app_templates.id"), nullable=False, index=True, comment="模板ID")
    template_version_id = Column(
        String(36),
        ForeignKey("template_versions.id"),
        nullable=True,
        index=True,
        comment="当前模板版本ID",
    )
    default_store_id = Column(String(36), ForeignKey("stores.id"), nullable=True, index=True, comment="默认门店ID")
    default_payment_profile_id = Column(
        String(36),
        ForeignKey("payment_profiles.id"),
        nullable=True,
        index=True,
        comment="默认支付配置ID",
    )
    code = Column(String(50), nullable=True, comment="实例编码，租户内唯一")
    name = Column(String(100), nullable=False, comment="实例名称")
    app_id = Column(String(100), nullable=False, comment="微信小程序AppID")
    app_secret_ref = Column(String(255), nullable=True, comment="小程序Secret引用，例如 env:WX_APP_SECRET")
    upload_private_key_ref = Column(String(255), nullable=True, comment="上传私钥引用")
    app_config = Column(Text, nullable=True, comment="实例扩展配置(JSON)")
    status = Column(Integer, default=1, comment="状态: 0禁用 1启用 2归档")

    tenant = relationship("Tenant", backref="miniapp_instances")
    template = relationship("AppTemplate", backref="instances")
    template_version = relationship("TemplateVersion", foreign_keys=[template_version_id], backref="instances")
    default_store = relationship("Store", foreign_keys=[default_store_id], backref="miniapp_instances")

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_miniapp_instances_tenant_code"),
        UniqueConstraint("tenant_id", "app_id", name="uq_miniapp_instances_tenant_appid"),
        {"comment": "小程序实例表"},
    )


class PaymentProfile(Base, AuditMixin):
    """支付配置。"""

    __tablename__ = "payment_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=True, index=True, comment="公司主体ID")
    name = Column(String(100), nullable=False, comment="支付配置名称")
    code = Column(String(50), nullable=True, comment="支付配置编码，租户内唯一")
    mode = Column(String(30), nullable=False, default="direct", comment="支付模式: direct/service_provider")
    app_id = Column(String(100), nullable=True, comment="支付关联AppID")
    mch_id = Column(String(100), nullable=True, comment="直连商户号")
    sub_mchid = Column(String(100), nullable=True, comment="服务商模式子商户号")
    notify_url = Column(String(255), nullable=True, comment="支付回调地址")
    refund_notify_url = Column(String(255), nullable=True, comment="退款回调地址")
    api_v3_key_ref = Column(String(255), nullable=True, comment="APIv3 Key引用")
    cert_serial_no = Column(String(100), nullable=True, comment="商户证书序列号")
    private_key_ref = Column(String(255), nullable=True, comment="商户私钥引用")
    is_default = Column(Boolean, default=False, comment="是否租户默认支付配置")
    status = Column(Integer, default=1, comment="状态: 0禁用 1启用")

    tenant = relationship("Tenant", backref="payment_profiles")
    company = relationship("Company", backref="payment_profiles")

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_payment_profiles_tenant_code"),
        {"comment": "支付配置表"},
    )


class PaymentRoute(Base, AuditMixin):
    """支付路由规则。"""

    __tablename__ = "payment_routes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=True, index=True, comment="门店ID")
    miniapp_instance_id = Column(
        String(36),
        ForeignKey("miniapp_instances.id"),
        nullable=True,
        index=True,
        comment="小程序实例ID",
    )
    payment_profile_id = Column(
        String(36),
        ForeignKey("payment_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="支付配置ID",
    )
    priority = Column(Integer, default=100, comment="优先级，值越大优先级越高")
    status = Column(Integer, default=1, comment="状态: 0禁用 1启用")

    tenant = relationship("Tenant", backref="payment_routes")
    store = relationship("Store", backref="payment_routes")
    miniapp_instance = relationship("MiniappInstance", backref="payment_routes")
    payment_profile = relationship("PaymentProfile", backref="routes")

    __table_args__ = (
        {"comment": "支付路由规则表"},
    )


class BuildJob(Base, AuditMixin):
    """小程序构建任务。"""

    __tablename__ = "build_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    miniapp_instance_id = Column(
        String(36),
        ForeignKey("miniapp_instances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="小程序实例ID",
    )
    template_version_id = Column(
        String(36),
        ForeignKey("template_versions.id"),
        nullable=True,
        index=True,
        comment="模板版本ID",
    )
    trigger_source = Column(String(50), nullable=True, comment="触发来源")
    build_params = Column(Text, nullable=True, comment="构建参数(JSON)")
    status = Column(String(30), nullable=False, default="pending", comment="任务状态")
    started_at = Column(DateTime, nullable=True, comment="开始时间")
    finished_at = Column(DateTime, nullable=True, comment="结束时间")

    tenant = relationship("Tenant", backref="build_jobs")
    miniapp_instance = relationship("MiniappInstance", backref="build_jobs")
    template_version = relationship("TemplateVersion", backref="build_jobs")


class ReleaseArtifact(Base, AuditMixin):
    """发布构建产物。"""

    __tablename__ = "release_artifacts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    build_job_id = Column(String(36), ForeignKey("build_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(500), nullable=False, comment="制品路径")
    checksum = Column(String(128), nullable=True, comment="制品校验值")
    artifact_metadata = Column("metadata", Text, nullable=True, comment="制品元数据(JSON)")

    build_job = relationship("BuildJob", backref="artifacts")


class ReleaseJob(Base, AuditMixin):
    """小程序发布任务。"""

    __tablename__ = "release_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    miniapp_instance_id = Column(
        String(36),
        ForeignKey("miniapp_instances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="小程序实例ID",
    )
    artifact_id = Column(
        String(36),
        ForeignKey("release_artifacts.id"),
        nullable=True,
        index=True,
        comment="制品ID",
    )
    action = Column(String(30), nullable=False, comment="动作: upload/submit_audit/publish/rollback")
    target_version = Column(String(50), nullable=True, comment="目标版本")
    result = Column(Text, nullable=True, comment="执行结果(JSON)")
    status = Column(String(30), nullable=False, default="pending", comment="任务状态")

    miniapp_instance = relationship("MiniappInstance", backref="release_jobs")
    artifact = relationship("ReleaseArtifact", backref="release_jobs")
