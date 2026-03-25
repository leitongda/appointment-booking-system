"""add tenant_id to core tables

Revision ID: 040_tenant_core_tables
Revises: 039_tenant_support
Create Date: 2026-03-23

为核心业务表添加 tenant_id 字段，实现多租户强隔离：
- users: 用户表（微信用户可在不同租户分别绑定账号）
- doctors: 医生表
- patients: 患者表
- schedules: 排班表
- schedule_templates: 排班模板表
- appointments: 预约表
- roles: 角色表（平台角色 tenant_id 为 NULL）
- departments: 科室表

修改唯一约束为租户内唯一：
- admins: (tenant_id, username)
- doctors: (tenant_id, username), (tenant_id, phone)
- users: (tenant_id, phone), (tenant_id, openid), (tenant_id, unionid)
- stores: (tenant_id, code)
- roles: (tenant_id, code)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '040_tenant_core_tables'
down_revision = '039_tenant_support'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ============================================================
    # 1. 为各表添加 tenant_id 字段（允许 NULL，兼容历史数据）
    # ============================================================

    # 1.1 users 表
    op.add_column('users', sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, comment='租户ID'))
    op.create_index('idx_users_tenant_id', 'users', ['tenant_id'])

    # 1.2 doctors 表
    op.add_column('doctors', sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, comment='租户ID'))
    op.create_index('idx_doctors_tenant_id', 'doctors', ['tenant_id'])

    # 1.3 patients 表
    op.add_column('patients', sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, comment='租户ID'))
    op.create_index('idx_patients_tenant_id', 'patients', ['tenant_id'])

    # 1.4 schedules 表
    op.add_column('schedules', sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, comment='租户ID'))
    op.create_index('idx_schedules_tenant_id', 'schedules', ['tenant_id'])

    # 1.5 schedule_templates 表
    op.add_column('schedule_templates', sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, comment='租户ID'))
    op.create_index('idx_schedule_templates_tenant_id', 'schedule_templates', ['tenant_id'])

    # 1.6 appointments 表
    op.add_column('appointments', sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, comment='租户ID'))
    op.create_index('idx_appointments_tenant_id', 'appointments', ['tenant_id'])

    # 1.7 roles 表
    op.add_column('roles', sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, comment='租户ID（NULL表示平台角色）'))
    op.create_index('idx_roles_tenant_id', 'roles', ['tenant_id'])

    # 1.8 departments 表
    op.add_column('departments', sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, comment='租户ID'))
    op.create_index('idx_departments_tenant_id', 'departments', ['tenant_id'])

    # ============================================================
    # 2. 删除原有全局唯一约束，创建租户内唯一约束
    # ============================================================

    # 2.1 admins 表: username -> (tenant_id, username)
    # 实际约束名是 admins_username_key
    op.drop_constraint('admins_username_key', 'admins', type_='unique')
    op.create_unique_constraint('uq_admins_tenant_username', 'admins', ['tenant_id', 'username'])

    # 2.2 doctors 表: username, phone -> (tenant_id, username), (tenant_id, phone)
    # doctors 表当前没有唯一约束，直接创建新的
    op.create_unique_constraint('uq_doctors_tenant_username', 'doctors', ['tenant_id', 'username'])
    op.create_unique_constraint('uq_doctors_tenant_phone', 'doctors', ['tenant_id', 'phone'])

    # 2.3 users 表: phone, openid, unionid -> 租户内唯一
    # users 表当前没有唯一约束，直接创建新的
    op.create_unique_constraint('uq_users_tenant_phone', 'users', ['tenant_id', 'phone'])
    op.create_unique_constraint('uq_users_tenant_openid', 'users', ['tenant_id', 'openid'])
    op.create_unique_constraint('uq_users_tenant_unionid', 'users', ['tenant_id', 'unionid'])

    # 2.4 stores 表: code -> (tenant_id, code)
    # 实际约束名是 stores_code_key
    op.drop_constraint('stores_code_key', 'stores', type_='unique')
    op.create_unique_constraint('uq_stores_tenant_code', 'stores', ['tenant_id', 'code'])

    # 2.5 roles 表: code -> (tenant_id, code)
    # 实际约束名是 roles_code_key
    op.drop_constraint('roles_code_key', 'roles', type_='unique')
    op.create_unique_constraint('uq_roles_tenant_code', 'roles', ['tenant_id', 'code'])

    # 2.6 patients 表: card_no -> (tenant_id, card_no)
    # patients 表当前没有唯一约束，直接创建新的
    op.create_unique_constraint('uq_patients_tenant_card_no', 'patients', ['tenant_id', 'card_no'])


def downgrade() -> None:
    # 2.6 回滚 patients 唯一约束
    op.drop_constraint('uq_patients_tenant_card_no', 'patients', type_='unique')
    # 注意：不恢复原有约束，因为数据可能已不兼容

    # 2.5 回滚 roles 唯一约束
    op.drop_constraint('uq_roles_tenant_code', 'roles', type_='unique')

    # 2.4 回滚 stores 唯一约束
    op.drop_constraint('uq_stores_tenant_code', 'stores', type_='unique')

    # 2.3 回滚 users 唯一约束
    op.drop_constraint('uq_users_tenant_unionid', 'users', type_='unique')
    op.drop_constraint('uq_users_tenant_openid', 'users', type_='unique')
    op.drop_constraint('uq_users_tenant_phone', 'users', type_='unique')

    # 2.2 回滚 doctors 唯一约束
    op.drop_constraint('uq_doctors_tenant_phone', 'doctors', type_='unique')
    op.drop_constraint('uq_doctors_tenant_username', 'doctors', type_='unique')

    # 2.1 回滚 admins 唯一约束
    op.drop_constraint('uq_admins_tenant_username', 'admins', type_='unique')

    # 1.8 删除 departments 表的 tenant_id
    op.drop_index('idx_departments_tenant_id', 'departments')
    op.drop_column('departments', 'tenant_id')

    # 1.7 删除 roles 表的 tenant_id
    op.drop_index('idx_roles_tenant_id', 'roles')
    op.drop_column('roles', 'tenant_id')

    # 1.6 删除 appointments 表的 tenant_id
    op.drop_index('idx_appointments_tenant_id', 'appointments')
    op.drop_column('appointments', 'tenant_id')

    # 1.5 删除 schedule_templates 表的 tenant_id
    op.drop_index('idx_schedule_templates_tenant_id', 'schedule_templates')
    op.drop_column('schedule_templates', 'tenant_id')

    # 1.4 删除 schedules 表的 tenant_id
    op.drop_index('idx_schedules_tenant_id', 'schedules')
    op.drop_column('schedules', 'tenant_id')

    # 1.3 删除 patients 表的 tenant_id
    op.drop_index('idx_patients_tenant_id', 'patients')
    op.drop_column('patients', 'tenant_id')

    # 1.2 删除 doctors 表的 tenant_id
    op.drop_index('idx_doctors_tenant_id', 'doctors')
    op.drop_column('doctors', 'tenant_id')

    # 1.1 删除 users 表的 tenant_id
    op.drop_index('idx_users_tenant_id', 'users')
    op.drop_column('users', 'tenant_id')
