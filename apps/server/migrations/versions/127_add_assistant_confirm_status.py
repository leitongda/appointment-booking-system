"""add assistant_confirm_status to appointments

Revision ID: 127_assistant_confirm_status
Revises: 20260630_drop_plaintext
Create Date: 2026-10-23

Add assistant_confirm_status column to appointments table for the
medical-assistant phone confirmation flow:
0无需 1待联系 2已联系 3已确认到店时间（默认 1 待联系）。
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '127_assistant_confirm_status'
down_revision = '20260630_drop_plaintext'
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


def upgrade() -> None:
    # 添加医助确认状态列
    if not column_exists('appointments', 'assistant_confirm_status'):
        op.add_column('appointments', sa.Column(
            'assistant_confirm_status',
            sa.SmallInteger(),
            nullable=True,
            server_default=sa.text('1'),
            comment='医助确认: 0无需 1待联系 2已联系 3已确认到店时间'
        ))
        # 契约默认 1（待联系）：回填存量历史预约，否则该列为 NULL，
        # 与前端展示（NULL 视为 1）及后端过滤 assistant_confirm_status=1 不一致
        op.execute(
            "UPDATE appointments SET assistant_confirm_status = 1 "
            "WHERE assistant_confirm_status IS NULL"
        )


def downgrade() -> None:
    # 删除医助确认状态列
    if column_exists('appointments', 'assistant_confirm_status'):
        op.drop_column('appointments', 'assistant_confirm_status')
