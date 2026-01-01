"""add break_times column to schedule_templates table

Revision ID: 032
Revises: 031_add_appointment_snapshot_fields
Create Date: 2025-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '032_add_break_times'
down_revision = '031_add_appointment_snapshot_fields'
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # 添加 break_times 字段到 schedule_templates 表
    # 用于存储排除时间段（如午休时间）
    # JSON 格式：[{"startTime": "12:00", "endTime": "13:30"}]
    if not column_exists('schedule_templates', 'break_times'):
        op.add_column(
            'schedule_templates',
            sa.Column(
                'break_times',
                sa.Text,
                nullable=True,
                comment='排除时间段 JSON格式 [{"startTime": "12:00", "endTime": "13:30"}]'
            )
        )


def downgrade() -> None:
    # 回滚：删除 break_times 字段
    if column_exists('schedule_templates', 'break_times'):
        op.drop_column('schedule_templates', 'break_times')

