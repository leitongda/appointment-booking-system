"""add must_change_password flag and refresh token blacklist

Revision ID: 8c3d04cbc758
Revises: 120
Create Date: 2026-05-31 21:40:44.649606

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '8c3d04cbc758'
down_revision = '120'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # admins 表: 新增 must_change_password 字段
    op.add_column('admins', sa.Column(
        'must_change_password', sa.Boolean(),
        nullable=False, server_default='0',
        comment='首次登录是否强制修改密码',
    ))

    # users 表: 新增 must_change_password 字段
    op.add_column('users', sa.Column(
        'must_change_password', sa.Boolean(),
        nullable=False, server_default='0',
        comment='首次登录是否强制修改密码',
    ))


def downgrade() -> None:
    op.drop_column('users', 'must_change_password')
    op.drop_column('admins', 'must_change_password')
