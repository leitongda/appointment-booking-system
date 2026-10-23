"""P3-3: business numbers become tenant-scoped unique

Revision ID: p3a3_business_numbers
Revises: p3a2_admin_role_unique
Create Date: 2026-10-23

appointment_no / record_no / task_no / settlement_no 改为 (tenant_id, no) 唯一，
tenant_id IS NULL 的平台行用 partial unique index 保持唯一。
四列原均为全局唯一，不存在跨租户重复；约束创建失败即说明存量数据异常。
downgrade 恢复全局唯一；跨租户同号数据存在时会失败。
"""
import sqlalchemy as sa
from alembic import op

revision = "p3a3_business_numbers"
down_revision = "p3a2_admin_role_unique"
branch_labels = None
depends_on = None

TARGETS = (
    ("appointments", "appointment_no", "appointments_appointment_no_key",
     "uq_appointments_tenant_no", "uq_appointments_no_platform"),
    ("medical_records", "record_no", "medical_records_record_no_key",
     "uq_medical_records_tenant_no", "uq_medical_records_no_platform"),
    ("follow_up_tasks", "task_no", "follow_up_tasks_task_no_key",
     "uq_follow_up_tasks_tenant_no", "uq_follow_up_tasks_no_platform"),
    ("freelance_settlements", "settlement_no", "freelance_settlements_settlement_no_key",
     "uq_freelance_settlements_tenant_no", "uq_freelance_settlements_no_platform"),
)


def upgrade() -> None:
    for table, column, old_constraint, uq_name, idx_name in TARGETS:
        op.drop_constraint(old_constraint, table, type_="unique")
        op.create_unique_constraint(uq_name, table, ["tenant_id", column])
        op.create_index(
            idx_name,
            table,
            [column],
            unique=True,
            postgresql_where=sa.text("tenant_id IS NULL"),
        )


def downgrade() -> None:
    for table, column, old_constraint, uq_name, idx_name in TARGETS:
        op.drop_index(idx_name, table_name=table)
        op.drop_constraint(uq_name, table, type_="unique")
        op.create_unique_constraint(old_constraint, table, [column])
