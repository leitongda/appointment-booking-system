"""add composite indexes for multi-tenant queries

Revision ID: 042_composite_indexes
Revises: 041_template_driven_miniapp
Create Date: 2026-03-27

为高频多租户查询添加复合索引，避免全表扫描。
保留已有单列 tenant_id 索引。
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '042_composite_indexes'
down_revision = '041_template_driven_miniapp_platform'
branch_labels = None
depends_on = None

# 索引定义: (table, index_name, columns)
COMPOSITE_INDEXES = [
    # appointments
    ("appointments", "idx_appointments_tenant_status", ["tenant_id", "status"]),
    ("appointments", "idx_appointments_tenant_user", ["tenant_id", "user_id"]),
    ("appointments", "idx_appointments_tenant_doctor_date", ["tenant_id", "doctor_id", "schedule_date"]),
    ("appointments", "idx_appointments_tenant_schedule", ["tenant_id", "schedule_id"]),
    # schedules
    ("schedules", "idx_schedules_tenant_doctor_date", ["tenant_id", "doctor_id", "schedule_date"]),
    ("schedules", "idx_schedules_tenant_store_date", ["tenant_id", "store_id", "schedule_date"]),
    ("schedules", "idx_schedules_tenant_status", ["tenant_id", "status"]),
    # doctors
    ("doctors", "idx_doctors_tenant_department", ["tenant_id", "department_id"]),
    ("doctors", "idx_doctors_tenant_store", ["tenant_id", "store_id"]),
    ("doctors", "idx_doctors_tenant_status", ["tenant_id", "status"]),
    # departments
    ("departments", "idx_departments_tenant_store", ["tenant_id", "store_id"]),
    # stores
    ("stores", "idx_stores_tenant_status", ["tenant_id", "status"]),
    # admins
    ("admins", "idx_admins_tenant_role", ["tenant_id", "role_id"]),
    ("admins", "idx_admins_tenant_status", ["tenant_id", "status"]),
    # users
    ("users", "idx_users_tenant_phone", ["tenant_id", "phone"]),
    ("users", "idx_users_tenant_status", ["tenant_id", "status"]),
    # patients
    ("patients", "idx_patients_tenant_user", ["tenant_id", "user_id"]),
    # schedule_templates
    ("schedule_templates", "idx_schedule_templates_tenant_store", ["tenant_id", "store_id"]),
]


def upgrade() -> None:
    for table, index_name, columns in COMPOSITE_INDEXES:
        op.create_index(index_name, table, columns)


def downgrade() -> None:
    for table, index_name, columns in reversed(COMPOSITE_INDEXES):
        op.drop_index(index_name, table_name=table)
