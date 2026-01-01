"""移除挂号费字段，添加门店复诊规则配置表

Revision ID: 030_remove_registration_fee
Revises: 029_booking_features
Create Date: 2026-01-01

1. 移除 doctors 表的 registration_fee 字段
2. 创建 store_visit_type_configs 表（门店复诊规则配置）
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '030_remove_registration_fee'
down_revision = '029_booking_features'
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    try:
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False


def table_exists(table_name: str) -> bool:
    """检查表是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # 1. 移除 doctors 表的 registration_fee 字段
    if column_exists('doctors', 'registration_fee'):
        op.drop_column('doctors', 'registration_fee')
    
    # 2. 创建门店复诊规则配置表
    if not table_exists('store_visit_type_configs'):
        op.create_table(
            'store_visit_type_configs',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id', ondelete='CASCADE'), 
                      nullable=False, unique=True, comment='门店ID'),
            sa.Column('time_limit', sa.Integer, server_default='30', nullable=False, 
                      comment='复诊时间限制值'),
            sa.Column('time_unit', sa.String(10), server_default='days', nullable=False, 
                      comment='时间单位：hours/days'),
            sa.Column('scope', sa.String(20), server_default='same_doctor', nullable=False, 
                      comment='复诊范围：same_doctor/same_department/same_store'),
            sa.Column('status', sa.Integer, server_default='1', comment='状态: 0禁用 1启用'),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.Column('created_by', sa.String(36), nullable=True, comment='创建人ID'),
            sa.Column('updated_by', sa.String(36), nullable=True, comment='更新人ID'),
        )
        # 创建索引
        op.create_index('ix_store_visit_type_configs_store_id', 'store_visit_type_configs', ['store_id'], unique=True)


def downgrade() -> None:
    # 1. 删除门店复诊规则配置表
    if table_exists('store_visit_type_configs'):
        try:
            op.drop_index('ix_store_visit_type_configs_store_id', 'store_visit_type_configs')
        except Exception:
            pass
        op.drop_table('store_visit_type_configs')
    
    # 2. 恢复 doctors 表的 registration_fee 字段
    if not column_exists('doctors', 'registration_fee'):
        op.add_column(
            'doctors',
            sa.Column('registration_fee', sa.Numeric(10, 2), server_default='0', comment='挂号费')
        )

