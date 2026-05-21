"""add rule_set_id to schedule_templates and schedules

Revision ID: 103
Revises: 102
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision = '103'
down_revision = '102'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # schedule_templates 增加 rule_set_id
    op.add_column(
        'schedule_templates',
        sa.Column('rule_set_id', sa.String(36), sa.ForeignKey('rule_sets.id'), nullable=True, comment='关联规则组ID'),
    )
    op.create_index('idx_schedule_templates_rule_set_id', 'schedule_templates', ['rule_set_id'])

    # schedules 增加 rule_set_id
    op.add_column(
        'schedules',
        sa.Column('rule_set_id', sa.String(36), sa.ForeignKey('rule_sets.id'), nullable=True, comment='关联规则组ID'),
    )
    op.create_index('idx_schedules_rule_set_id', 'schedules', ['rule_set_id'])


def downgrade() -> None:
    op.drop_index('idx_schedules_rule_set_id', table_name='schedules')
    op.drop_column('schedules', 'rule_set_id')
    op.drop_index('idx_schedule_templates_rule_set_id', table_name='schedule_templates')
    op.drop_column('schedule_templates', 'rule_set_id')
