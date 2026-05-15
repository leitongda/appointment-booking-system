"""Add consultation_enabled and feedback_enabled to notification_preferences

Revision ID: 085_add_consultation_feedback_to_notification_preferences
Revises: 084_create_unified_message_tables
Create Date: 2026-05-15
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '085_add_consultation_feedback_to_notification_preferences'
down_revision = '084_create_unified_message_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add consultation_enabled column (default True)
    op.add_column(
        'notification_preferences',
        sa.Column('consultation_enabled', sa.Boolean(), nullable=False, server_default='true')
    )

    # Add feedback_enabled column (default True)
    op.add_column(
        'notification_preferences',
        sa.Column('feedback_enabled', sa.Boolean(), nullable=False, server_default='true')
    )


def downgrade() -> None:
    op.drop_column('notification_preferences', 'feedback_enabled')
    op.drop_column('notification_preferences', 'consultation_enabled')
