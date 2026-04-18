"""Add tenant_id to email_templates and message_templates

Revision ID: 059_add_tenant_id_to_template_tables
Revises: 058_add_notification_logs, 058_add_rule_set_audit_logs
Create Date: 2026-04-18 19:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "059_add_tenant_id_to_template_tables"
down_revision = ("058_add_notification_logs", "058_add_rule_set_audit_logs")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "email_templates",
        sa.Column("tenant_id", sa.String(36), nullable=True, comment="租户ID"),
    )
    op.create_index("ix_email_templates_tenant_id", "email_templates", ["tenant_id"])

    op.add_column(
        "message_templates",
        sa.Column("tenant_id", sa.String(36), nullable=True, comment="租户ID"),
    )
    op.create_index("ix_message_templates_tenant_id", "message_templates", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_message_templates_tenant_id", table_name="message_templates")
    op.drop_column("message_templates", "tenant_id")

    op.drop_index("ix_email_templates_tenant_id", table_name="email_templates")
    op.drop_column("email_templates", "tenant_id")
