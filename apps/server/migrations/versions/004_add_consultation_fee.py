"""add consultation fee tables

Revision ID: 004
Revises: 003_add_store_fields
Create Date: 2024-01-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004_add_consultation_fee'
down_revision = '003_add_store_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建诊费类型表
    op.create_table(
        'consultation_fee_types',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(50), nullable=False, comment='诊费类型名称'),
        sa.Column('code', sa.String(50), nullable=True, comment='类型编码'),
        sa.Column('description', sa.String(255), nullable=True, comment='描述'),
        sa.Column('sort_order', sa.Integer, server_default='0', comment='排序'),
        sa.Column('status', sa.Integer, server_default='1', comment='状态: 0禁用 1启用'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_consultation_fee_types_code', 'consultation_fee_types', ['code'], unique=True)
    
    # 创建诊费模板表（全局默认诊费配置）
    op.create_table(
        'consultation_fee_templates',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('fee_type_id', sa.String(36), sa.ForeignKey('consultation_fee_types.id'), nullable=False, comment='诊费类型ID'),
        sa.Column('initial_fee', sa.Numeric(10, 2), server_default='0', comment='初诊金额'),
        sa.Column('follow_up_fee', sa.Numeric(10, 2), server_default='0', comment='复诊金额'),
        sa.Column('status', sa.Integer, server_default='1', comment='状态: 0禁用 1启用'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_consultation_fee_templates_fee_type', 'consultation_fee_templates', ['fee_type_id'], unique=True)
    
    # 创建医生诊费配置表
    op.create_table(
        'doctor_consultation_fees',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('doctor_id', sa.String(36), sa.ForeignKey('doctors.id'), nullable=False, comment='医生ID'),
        sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id'), nullable=False, comment='门店ID'),
        sa.Column('department_id', sa.String(36), sa.ForeignKey('departments.id'), nullable=False, comment='科室ID'),
        sa.Column('fee_type_id', sa.String(36), sa.ForeignKey('consultation_fee_types.id'), nullable=False, comment='诊费类型ID'),
        sa.Column('initial_fee', sa.Numeric(10, 2), server_default='0', comment='初诊金额'),
        sa.Column('follow_up_fee', sa.Numeric(10, 2), server_default='0', comment='复诊金额'),
        sa.Column('status', sa.Integer, server_default='1', comment='状态: 0禁用 1启用'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_doctor_consultation_fees_doctor', 'doctor_consultation_fees', ['doctor_id'])
    op.create_index('ix_doctor_consultation_fees_store', 'doctor_consultation_fees', ['store_id'])
    op.create_index('ix_doctor_consultation_fees_department', 'doctor_consultation_fees', ['department_id'])
    # 唯一索引：同一医生在同一门店同一科室的同一诊费类型只能有一条记录
    op.create_index(
        'ix_doctor_consultation_fees_unique',
        'doctor_consultation_fees',
        ['doctor_id', 'store_id', 'department_id', 'fee_type_id'],
        unique=True
    )
    
    # 医生表添加是否使用诊费模板字段
    op.add_column('doctors', sa.Column('use_fee_template', sa.Integer, server_default='0', comment='是否使用诊费模板 0否 1是'))
    
    # 插入默认诊费类型
    op.execute("""
        INSERT INTO consultation_fee_types (id, name, code, description, sort_order, status) VALUES
        (gen_random_uuid()::text, '专家', 'expert', '专家诊费', 1, 1),
        (gen_random_uuid()::text, '普通', 'normal', '普通诊费', 2, 1),
        (gen_random_uuid()::text, '加急', 'urgent', '加急诊费', 3, 1),
        (gen_random_uuid()::text, '医保', 'medical_insurance', '医保诊费', 4, 1),
        (gen_random_uuid()::text, '自费', 'self_pay', '自费诊费', 5, 1)
    """)


def downgrade() -> None:
    # 删除医生表的诊费模板字段
    op.drop_column('doctors', 'use_fee_template')
    
    # 删除医生诊费配置表
    op.drop_index('ix_doctor_consultation_fees_unique', 'doctor_consultation_fees')
    op.drop_index('ix_doctor_consultation_fees_department', 'doctor_consultation_fees')
    op.drop_index('ix_doctor_consultation_fees_store', 'doctor_consultation_fees')
    op.drop_index('ix_doctor_consultation_fees_doctor', 'doctor_consultation_fees')
    op.drop_table('doctor_consultation_fees')
    
    # 删除诊费模板表
    op.drop_index('ix_consultation_fee_templates_fee_type', 'consultation_fee_templates')
    op.drop_table('consultation_fee_templates')
    
    # 删除诊费类型表
    op.drop_index('ix_consultation_fee_types_code', 'consultation_fee_types')
    op.drop_table('consultation_fee_types')
