"""add tenant_audit_logs table

Revision ID: 070_add_tenant_audit_log
Revises: 069_add_tenant_id_to_feedbacks
Create Date: 2026-04-27 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "070_add_tenant_audit_log"
down_revision = "069_add_tenant_id_to_feedbacks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False, comment="事件类型"),
        sa.Column("actor_id", sa.String(36), nullable=True, comment="操作人ID"),
        sa.Column("actor_type", sa.String(20), nullable=True, comment="操作人类型: admin/platform_admin/system"),
        sa.Column("actor_name", sa.String(50), nullable=True, comment="操作人名称"),
        sa.Column("resource_type", sa.String(50), nullable=False, comment="资源类型"),
        sa.Column("resource_id", sa.String(36), nullable=False, comment="资源ID"),
        sa.Column("action", sa.String(50), nullable=False, comment="具体操作"),
        sa.Column("before_data", sa.Text, nullable=True, comment="变更前数据快照(JSON)"),
        sa.Column("after_data", sa.Text, nullable=True, comment="变更后数据快照(JSON)"),
        sa.Column("ip_address", sa.String(50), nullable=True, comment="IP地址"),
        sa.Column("user_agent", sa.String(255), nullable=True, comment="User-Agent"),
        sa.Column("created_at", sa.DateTime, nullable=True, comment="创建时间"),
        comment="租户操作审计日志表",
    )
    op.create_index(
        "ix_tenant_audit_logs_tenant_id",
        "tenant_audit_logs",
        ["tenant_id"],
    )
    op.create_index(
        "ix_tenant_audit_logs_tenant_created",
        "tenant_audit_logs",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_tenant_audit_logs_tenant_event",
        "tenant_audit_logs",
        ["tenant_id", "event_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_tenant_audit_logs_tenant_event", table_name="tenant_audit_logs")
    op.drop_index("ix_tenant_audit_logs_tenant_created", table_name="tenant_audit_logs")
    op.drop_index("ix_tenant_audit_logs_tenant_id", table_name="tenant_audit_logs")
    op.drop_table("tenant_audit_logs")
