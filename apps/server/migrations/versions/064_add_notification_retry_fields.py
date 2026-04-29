"""add notification retry fields

Revision ID: 064
Revises: 063
Create Date: 2026-04-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '064'
down_revision: Union[str, None] = '063'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add max_retries and next_retry_at columns to notification_logs table."""
    op.add_column(
        'notification_logs',
        sa.Column(
            'max_retries',
            sa.Integer,
            nullable=True,
            server_default='3',
            comment='最大重试次数'
        )
    )

    op.add_column(
        'notification_logs',
        sa.Column(
            'next_retry_at',
            sa.DateTime,
            nullable=True,
            comment='下次重试时间'
        )
    )

    # 为现有记录设置默认 max_retries 为 3
    op.execute("""
        UPDATE notification_logs
        SET max_retries = 3
        WHERE max_retries IS NULL
    """)

    # 设置 max_retries 列为 NOT NULL 并设置默认值
    op.alter_column(
        'notification_logs',
        'max_retries',
        nullable=False,
        server_default='3'
    )


def downgrade() -> None:
    """Remove max_retries and next_retry_at columns from notification_logs table."""
    op.drop_column('notification_logs', 'next_retry_at')
    op.drop_column('notification_logs', 'max_retries')
