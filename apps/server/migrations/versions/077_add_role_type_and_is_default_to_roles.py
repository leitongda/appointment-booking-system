"""add role_type and is_default to roles, insert default doctor/patient roles

Revision ID: 077_add_role_type_is_default
Revises: 076_add_actor_role
Create Date: 2026-05-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

revision = '077_add_role_type_is_default'
down_revision = '076_add_actor_role'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 为 roles 表增加 role_type 和 is_default 字段
    op.add_column('roles', sa.Column(
        'role_type',
        sa.String(20),
        nullable=False,
        server_default='admin',
        comment='角色类型: admin/doctor/user',
    ))
    op.add_column('roles', sa.Column(
        'is_default',
        sa.Boolean(),
        nullable=False,
        server_default='0',
        comment='是否为默认角色',
    ))

    # 2. 为现有角色设置 role_type（根据 code 或 name 判断）
    roles = table(
        'roles',
        column('id', sa.String),
        column('code', sa.String),
        column('name', sa.String),
        column('role_type', sa.String),
        column('is_default', sa.Boolean),
    )

    # 平台管理员相关角色 -> admin
    op.execute(
        roles.update()
        .where(roles.c.code.in_(['SUPER_ADMIN', 'PLATFORM_ADMIN', 'TENANT_ADMIN', 'STORE_ADMIN']))
        .values(role_type='admin', is_default=False)
    )
    # 兼容：按名称匹配中文角色名
    op.execute(
        roles.update()
        .where(roles.c.name.in_(['超级管理员', '平台管理员', '租户管理员', '门店管理员']))
        .where(roles.c.role_type == 'admin')
        .values(is_default=False)
    )
    # 其他已有角色默认设为 admin
    op.execute(
        roles.update()
        .where(roles.c.role_type == 'admin')
        .values(is_default=False)
    )

    # 3. 插入默认医生角色和患者角色
    # 使用 sa.text 直接执行 SQL 以避免冲突
    op.execute(sa.text("""
        INSERT INTO roles (id, name, code, description, status, role_type, is_default, tenant_id, permissions, created_at, updated_at)
        VALUES (
            'role_doctor_default',
            '医生',
            'DOCTOR',
            '默认医生角色',
            1,
            'doctor',
            TRUE,
            NULL,
            '["doctor:schedule:view", "doctor:schedule:edit", "doctor:appointment:view", "doctor:appointment:edit", "doctor:patient:view", "doctor:consultation:*", "doctor:profile:edit", "doctor:message:view", "doctor:statistics:view"]',
            NOW(),
            NOW()
        )
        ON CONFLICT (id) DO NOTHING
    """))

    op.execute(sa.text("""
        INSERT INTO roles (id, name, code, description, status, role_type, is_default, tenant_id, permissions, created_at, updated_at)
        VALUES (
            'role_patient_default',
            '患者',
            'PATIENT',
            '默认患者角色',
            1,
            'user',
            TRUE,
            NULL,
            '["patient:appointment:create", "patient:appointment:cancel", "patient:appointment:view", "patient:profile:edit", "patient:patient:manage", "patient:message:view", "patient:review:create", "patient:review:view"]',
            NOW(),
            NOW()
        )
        ON CONFLICT (id) DO NOTHING
    """))


def downgrade() -> None:
    # 删除默认角色
    op.execute(sa.text("DELETE FROM roles WHERE id IN ('role_doctor_default', 'role_patient_default')"))

    # 删除新增字段
    op.drop_column('roles', 'is_default')
    op.drop_column('roles', 'role_type')
