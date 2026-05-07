"""扩展表补齐 role_id，关联 roles 表

Revision ID: 079_add_role_id_to_extensions
Revises: 078_create_unified_accounts
Create Date: 2026-05-07

变更内容：
  - account_doctors 增加 role_id 列 (FK → roles.id)
  - account_users 增加 role_id 列 (FK → roles.id)
  - 回填：所有医生指向默认 DOCTOR 角色
  - 回填：所有用户指向默认 PATIENT 角色
"""
from alembic import op
import sqlalchemy as sa

revision = '079_add_role_id_to_extensions'
down_revision = '078_create_unified_accounts'
branch_labels = None
depends_on = None

# 迁移 077 插入的默认角色 ID
DEFAULT_DOCTOR_ROLE_ID = 'role_doctor_default'
DEFAULT_PATIENT_ROLE_ID = 'role_patient_default'


def upgrade() -> None:
    # 1. account_doctors 加 role_id
    op.add_column(
        'account_doctors',
        sa.Column('role_id', sa.String(36), nullable=True, comment='角色ID（关联 roles 表）'),
    )
    op.create_foreign_key(
        'fk_account_doctors_role_id',
        'account_doctors', 'roles',
        ['role_id'], ['id'],
    )

    # 2. account_users 加 role_id
    op.add_column(
        'account_users',
        sa.Column('role_id', sa.String(36), nullable=True, comment='角色ID（关联 roles 表）'),
    )
    op.create_foreign_key(
        'fk_account_users_role_id',
        'account_users', 'roles',
        ['role_id'], ['id'],
    )

    # 3. 回填默认角色
    op.execute(
        f"UPDATE account_doctors SET role_id = '{DEFAULT_DOCTOR_ROLE_ID}' "
        f"WHERE role_id IS NULL"
    )
    op.execute(
        f"UPDATE account_users SET role_id = '{DEFAULT_PATIENT_ROLE_ID}' "
        f"WHERE role_id IS NULL"
    )


def downgrade() -> None:
    op.drop_constraint('fk_account_users_role_id', 'account_users', type_='foreignkey')
    op.drop_column('account_users', 'role_id')
    op.drop_constraint('fk_account_doctors_role_id', 'account_doctors', type_='foreignkey')
    op.drop_column('account_doctors', 'role_id')
