"""add template-driven miniapp platform

Revision ID: 041_template_driven_miniapp_platform
Revises: 040_tenant_core_tables
Create Date: 2026-03-24

新增模板、小程序实例、支付配置和发布任务相关表，
并为 appointments 表添加支付快照字段。
"""
from alembic import op
import sqlalchemy as sa


revision = "041_template_driven_miniapp_platform"
down_revision = "040_tenant_core_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False, comment="租户ID"),
        sa.Column("name", sa.String(100), nullable=False, comment="公司主体名称"),
        sa.Column("code", sa.String(50), nullable=True, comment="主体编码，租户内唯一"),
        sa.Column("unified_social_credit_code", sa.String(50), nullable=True, comment="统一社会信用代码"),
        sa.Column("contact_name", sa.String(100), nullable=True, comment="联系人"),
        sa.Column("contact_phone", sa.String(20), nullable=True, comment="联系电话"),
        sa.Column("status", sa.Integer(), nullable=True, comment="状态"),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.UniqueConstraint("tenant_id", "code", name="uq_companies_tenant_code"),
    )
    op.create_index("idx_companies_tenant_id", "companies", ["tenant_id"])

    op.create_table(
        "app_templates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True, comment="模板编码"),
        sa.Column("name", sa.String(100), nullable=False, comment="模板名称"),
        sa.Column("description", sa.Text(), nullable=True, comment="模板描述"),
        sa.Column("default_config", sa.Text(), nullable=True, comment="默认配置(JSON)"),
        sa.Column("status", sa.Integer(), nullable=True, comment="状态"),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
    )

    op.create_table(
        "template_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("template_id", sa.String(36), sa.ForeignKey("app_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.String(50), nullable=False, comment="模板版本"),
        sa.Column("source_ref", sa.String(255), nullable=True, comment="模板源码引用"),
        sa.Column("schema_version", sa.String(50), nullable=True, comment="配置结构版本"),
        sa.Column("changelog", sa.Text(), nullable=True, comment="变更说明"),
        sa.Column("status", sa.Integer(), nullable=True, comment="状态"),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.UniqueConstraint("template_id", "version", name="uq_template_versions_template_version"),
    )
    op.create_index("idx_template_versions_template_id", "template_versions", ["template_id"])

    op.create_table(
        "payment_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False, comment="租户ID"),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=True, comment="公司主体ID"),
        sa.Column("name", sa.String(100), nullable=False, comment="支付配置名称"),
        sa.Column("code", sa.String(50), nullable=True, comment="支付配置编码，租户内唯一"),
        sa.Column("mode", sa.String(30), nullable=False, server_default="direct", comment="支付模式"),
        sa.Column("app_id", sa.String(100), nullable=True, comment="支付关联AppID"),
        sa.Column("mch_id", sa.String(100), nullable=True, comment="直连商户号"),
        sa.Column("sub_mchid", sa.String(100), nullable=True, comment="服务商模式子商户号"),
        sa.Column("notify_url", sa.String(255), nullable=True, comment="支付回调地址"),
        sa.Column("api_v3_key_ref", sa.String(255), nullable=True, comment="APIv3 Key引用"),
        sa.Column("cert_serial_no", sa.String(100), nullable=True, comment="商户证书序列号"),
        sa.Column("private_key_ref", sa.String(255), nullable=True, comment="商户私钥引用"),
        sa.Column("is_default", sa.Boolean(), nullable=True, server_default=sa.text("false"), comment="是否默认"),
        sa.Column("status", sa.Integer(), nullable=True, comment="状态"),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.UniqueConstraint("tenant_id", "code", name="uq_payment_profiles_tenant_code"),
    )
    op.create_index("idx_payment_profiles_tenant_id", "payment_profiles", ["tenant_id"])
    op.create_index("idx_payment_profiles_company_id", "payment_profiles", ["company_id"])

    op.create_table(
        "miniapp_instances",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False, comment="租户ID"),
        sa.Column("template_id", sa.String(36), sa.ForeignKey("app_templates.id"), nullable=False, comment="模板ID"),
        sa.Column("template_version_id", sa.String(36), sa.ForeignKey("template_versions.id"), nullable=True, comment="模板版本ID"),
        sa.Column("default_store_id", sa.String(36), sa.ForeignKey("stores.id"), nullable=True, comment="默认门店ID"),
        sa.Column(
            "default_payment_profile_id",
            sa.String(36),
            sa.ForeignKey("payment_profiles.id"),
            nullable=True,
            comment="默认支付配置ID",
        ),
        sa.Column("code", sa.String(50), nullable=True, comment="实例编码，租户内唯一"),
        sa.Column("name", sa.String(100), nullable=False, comment="实例名称"),
        sa.Column("app_id", sa.String(100), nullable=False, comment="微信小程序AppID"),
        sa.Column("app_secret_ref", sa.String(255), nullable=True, comment="小程序Secret引用"),
        sa.Column("upload_private_key_ref", sa.String(255), nullable=True, comment="上传私钥引用"),
        sa.Column("app_config", sa.Text(), nullable=True, comment="实例扩展配置(JSON)"),
        sa.Column("status", sa.Integer(), nullable=True, comment="状态"),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.UniqueConstraint("tenant_id", "code", name="uq_miniapp_instances_tenant_code"),
        sa.UniqueConstraint("tenant_id", "app_id", name="uq_miniapp_instances_tenant_appid"),
    )
    op.create_index("idx_miniapp_instances_tenant_id", "miniapp_instances", ["tenant_id"])
    op.create_index("idx_miniapp_instances_template_id", "miniapp_instances", ["template_id"])
    op.create_index("idx_miniapp_instances_template_version_id", "miniapp_instances", ["template_version_id"])
    op.create_index("idx_miniapp_instances_default_store_id", "miniapp_instances", ["default_store_id"])
    op.create_index("idx_miniapp_instances_default_payment_profile_id", "miniapp_instances", ["default_payment_profile_id"])

    op.create_table(
        "payment_routes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False, comment="租户ID"),
        sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id"), nullable=True, comment="门店ID"),
        sa.Column("miniapp_instance_id", sa.String(36), sa.ForeignKey("miniapp_instances.id"), nullable=True, comment="小程序实例ID"),
        sa.Column(
            "payment_profile_id",
            sa.String(36),
            sa.ForeignKey("payment_profiles.id", ondelete="CASCADE"),
            nullable=False,
            comment="支付配置ID",
        ),
        sa.Column("priority", sa.Integer(), nullable=True, server_default="100", comment="优先级"),
        sa.Column("status", sa.Integer(), nullable=True, comment="状态"),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
    )
    op.create_index("idx_payment_routes_tenant_id", "payment_routes", ["tenant_id"])
    op.create_index("idx_payment_routes_store_id", "payment_routes", ["store_id"])
    op.create_index("idx_payment_routes_miniapp_instance_id", "payment_routes", ["miniapp_instance_id"])
    op.create_index("idx_payment_routes_payment_profile_id", "payment_routes", ["payment_profile_id"])

    op.create_table(
        "build_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False, comment="租户ID"),
        sa.Column("miniapp_instance_id", sa.String(36), sa.ForeignKey("miniapp_instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_version_id", sa.String(36), sa.ForeignKey("template_versions.id"), nullable=True),
        sa.Column("trigger_source", sa.String(50), nullable=True, comment="触发来源"),
        sa.Column("build_params", sa.Text(), nullable=True, comment="构建参数(JSON)"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending", comment="任务状态"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
    )
    op.create_index("idx_build_jobs_tenant_id", "build_jobs", ["tenant_id"])
    op.create_index("idx_build_jobs_instance_id", "build_jobs", ["miniapp_instance_id"])
    op.create_index("idx_build_jobs_template_version_id", "build_jobs", ["template_version_id"])

    op.create_table(
        "release_artifacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("build_job_id", sa.String(36), sa.ForeignKey("build_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False, comment="制品路径"),
        sa.Column("checksum", sa.String(128), nullable=True, comment="制品校验值"),
        sa.Column("metadata", sa.Text(), nullable=True, comment="制品元数据(JSON)"),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
    )
    op.create_index("idx_release_artifacts_build_job_id", "release_artifacts", ["build_job_id"])

    op.create_table(
        "release_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("miniapp_instance_id", sa.String(36), sa.ForeignKey("miniapp_instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("artifact_id", sa.String(36), sa.ForeignKey("release_artifacts.id"), nullable=True),
        sa.Column("action", sa.String(30), nullable=False, comment="动作"),
        sa.Column("target_version", sa.String(50), nullable=True, comment="目标版本"),
        sa.Column("result", sa.Text(), nullable=True, comment="执行结果(JSON)"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending", comment="任务状态"),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
    )
    op.create_index("idx_release_jobs_instance_id", "release_jobs", ["miniapp_instance_id"])
    op.create_index("idx_release_jobs_artifact_id", "release_jobs", ["artifact_id"])

    op.add_column(
        "appointments",
        sa.Column("payment_profile_id", sa.String(36), sa.ForeignKey("payment_profiles.id"), nullable=True, comment="支付配置ID快照"),
    )
    op.add_column(
        "appointments",
        sa.Column("payment_miniapp_instance_id", sa.String(36), sa.ForeignKey("miniapp_instances.id"), nullable=True, comment="小程序实例ID快照"),
    )
    op.add_column("appointments", sa.Column("payment_mode", sa.String(30), nullable=True, comment="支付模式快照"))
    op.add_column("appointments", sa.Column("payment_app_id", sa.String(100), nullable=True, comment="支付AppID快照"))
    op.add_column("appointments", sa.Column("payment_mch_id", sa.String(100), nullable=True, comment="支付商户号快照"))
    op.add_column("appointments", sa.Column("payment_sub_mchid", sa.String(100), nullable=True, comment="支付子商户号快照"))
    op.add_column("appointments", sa.Column("payment_notify_url", sa.String(255), nullable=True, comment="支付回调地址快照"))
    op.create_index("idx_appointments_payment_profile_id", "appointments", ["payment_profile_id"])
    op.create_index("idx_appointments_payment_instance_id", "appointments", ["payment_miniapp_instance_id"])


def downgrade() -> None:
    op.drop_index("idx_appointments_payment_instance_id", "appointments")
    op.drop_index("idx_appointments_payment_profile_id", "appointments")
    op.drop_column("appointments", "payment_notify_url")
    op.drop_column("appointments", "payment_sub_mchid")
    op.drop_column("appointments", "payment_mch_id")
    op.drop_column("appointments", "payment_app_id")
    op.drop_column("appointments", "payment_mode")
    op.drop_column("appointments", "payment_miniapp_instance_id")
    op.drop_column("appointments", "payment_profile_id")

    op.drop_index("idx_release_jobs_artifact_id", "release_jobs")
    op.drop_index("idx_release_jobs_instance_id", "release_jobs")
    op.drop_table("release_jobs")

    op.drop_index("idx_release_artifacts_build_job_id", "release_artifacts")
    op.drop_table("release_artifacts")

    op.drop_index("idx_build_jobs_template_version_id", "build_jobs")
    op.drop_index("idx_build_jobs_instance_id", "build_jobs")
    op.drop_index("idx_build_jobs_tenant_id", "build_jobs")
    op.drop_table("build_jobs")

    op.drop_index("idx_payment_routes_payment_profile_id", "payment_routes")
    op.drop_index("idx_payment_routes_miniapp_instance_id", "payment_routes")
    op.drop_index("idx_payment_routes_store_id", "payment_routes")
    op.drop_index("idx_payment_routes_tenant_id", "payment_routes")
    op.drop_table("payment_routes")

    op.drop_index("idx_miniapp_instances_default_payment_profile_id", "miniapp_instances")
    op.drop_index("idx_miniapp_instances_default_store_id", "miniapp_instances")
    op.drop_index("idx_miniapp_instances_template_version_id", "miniapp_instances")
    op.drop_index("idx_miniapp_instances_template_id", "miniapp_instances")
    op.drop_index("idx_miniapp_instances_tenant_id", "miniapp_instances")
    op.drop_table("miniapp_instances")

    op.drop_index("idx_payment_profiles_company_id", "payment_profiles")
    op.drop_index("idx_payment_profiles_tenant_id", "payment_profiles")
    op.drop_table("payment_profiles")

    op.drop_index("idx_template_versions_template_id", "template_versions")
    op.drop_table("template_versions")

    op.drop_table("app_templates")

    op.drop_index("idx_companies_tenant_id", "companies")
    op.drop_table("companies")
