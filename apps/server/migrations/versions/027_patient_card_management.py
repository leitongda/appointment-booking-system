"""add age field to patients and max_cards_per_user to stores

Revision ID: 027_patient_card_management
Revises: 026_add_content_store_id
Create Date: 2024-12-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '027_patient_card_management'
down_revision = '026_add_content_store_id'
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


def upgrade():
    """添加 age 字段到 patients 表，添加 max_cards_per_user 字段到 stores 表"""
    
    # 1. patients 表添加 age 字段
    if not column_exists('patients', 'age'):
        op.add_column(
            'patients',
            sa.Column('age', sa.Integer(), nullable=True, comment='年龄')
        )
        print("patients 表已添加 age 字段")
    else:
        print("patients 表已存在 age 字段，跳过")
    
    # 2. stores 表添加 max_cards_per_user 字段
    if not column_exists('stores', 'max_cards_per_user'):
        op.add_column(
            'stores',
            sa.Column('max_cards_per_user', sa.Integer(), nullable=True, server_default='5', comment='每用户可建就诊卡数量上限')
        )
        print("stores 表已添加 max_cards_per_user 字段")
    else:
        print("stores 表已存在 max_cards_per_user 字段，跳过")


def downgrade():
    """删除新增的字段"""
    
    # 删除 patients 表的 age 字段
    if column_exists('patients', 'age'):
        op.drop_column('patients', 'age')
    
    # 删除 stores 表的 max_cards_per_user 字段
    if column_exists('stores', 'max_cards_per_user'):
        op.drop_column('stores', 'max_cards_per_user')

