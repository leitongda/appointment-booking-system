"""expand store password column for bcrypt hash

Revision ID: 049_store_password_hash
Revises: 048_doctor_soft_delete
Create Date: 2026-03-29

将 stores.password 列从 VARCHAR(100) 扩展到 VARCHAR(255)，
以适应 bcrypt 哈希值（60 字符）以及未来可能的算法变更。
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '049_store_password_hash'
down_revision = '048_doctor_soft_delete'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        'stores', 'password',
        existing_type=sa.String(100),
        type_=sa.String(255),
        existing_comment='门店密码',
        comment='门店密码（bcrypt 哈希）',
    )


def downgrade() -> None:
    op.alter_column(
        'stores', 'password',
        existing_type=sa.String(255),
        type_=sa.String(100),
        existing_comment='门店密码（bcrypt 哈希）',
        comment='门店密码',
    )
