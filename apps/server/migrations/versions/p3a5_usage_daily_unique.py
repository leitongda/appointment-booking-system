"""P3-5: TenantUsageLog daily unique + duplicate cleanup

Revision ID: p3a5_usage_daily_unique
Revises: p3a4_config_codes
Create Date: 2026-10-23

清理同租户同日的重复用量行（计数列按 SUM 合并到保留行，保留行取最新 created_at），
然后建立 (tenant_id, usage_date) 唯一约束。
downgrade 仅删除约束，不恢复被合并的重复行。
"""
import sqlalchemy as sa
from alembic import op

revision = "p3a5_usage_daily_unique"
down_revision = "p3a4_config_codes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text(
        "WITH ranked AS ("
        " SELECT id, row_number() OVER (PARTITION BY tenant_id, usage_date"
        "   ORDER BY created_at DESC, id DESC) AS rn,"
        " sum(appointment_count) OVER (PARTITION BY tenant_id, usage_date) AS s1,"
        " sum(appointment_completed_count) OVER (PARTITION BY tenant_id, usage_date) AS s2,"
        " sum(appointment_cancelled_count) OVER (PARTITION BY tenant_id, usage_date) AS s3,"
        " sum(new_user_count) OVER (PARTITION BY tenant_id, usage_date) AS s4,"
        " sum(active_user_count) OVER (PARTITION BY tenant_id, usage_date) AS s5,"
        " sum(active_doctor_count) OVER (PARTITION BY tenant_id, usage_date) AS s6,"
        " sum(storage_used_mb) OVER (PARTITION BY tenant_id, usage_date) AS s7,"
        " sum(sms_sent_count) OVER (PARTITION BY tenant_id, usage_date) AS s8,"
        " sum(push_sent_count) OVER (PARTITION BY tenant_id, usage_date) AS s9"
        " FROM tenant_usage_logs"
        ") UPDATE tenant_usage_logs t SET"
        " appointment_count = r.s1, appointment_completed_count = r.s2,"
        " appointment_cancelled_count = r.s3, new_user_count = r.s4,"
        " active_user_count = r.s5, active_doctor_count = r.s6,"
        " storage_used_mb = r.s7, sms_sent_count = r.s8, push_sent_count = r.s9"
        " FROM ranked r WHERE t.id = r.id AND r.rn = 1 AND EXISTS ("
        "  SELECT 1 FROM tenant_usage_logs x WHERE x.tenant_id = t.tenant_id"
        "  AND x.usage_date = t.usage_date AND x.id <> t.id)"
    ))
    op.execute(sa.text(
        "WITH ranked AS ("
        " SELECT id, row_number() OVER (PARTITION BY tenant_id, usage_date"
        "   ORDER BY created_at DESC, id DESC) AS rn FROM tenant_usage_logs"
        ") DELETE FROM tenant_usage_logs WHERE id IN"
        " (SELECT id FROM ranked WHERE rn > 1)"
    ))
    op.create_unique_constraint(
        "uq_tenant_usage_date", "tenant_usage_logs", ["tenant_id", "usage_date"]
    )
    op.create_index("ix_tenant_usage_logs_tenant_id", "tenant_usage_logs", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_tenant_usage_logs_tenant_id", table_name="tenant_usage_logs")
    op.drop_constraint("uq_tenant_usage_date", "tenant_usage_logs", type_="unique")
