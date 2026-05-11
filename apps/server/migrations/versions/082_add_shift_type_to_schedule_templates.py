"""schedule_templates 表新增 shift_type_id 字段

Revision ID: 082_add_shift_type_to_schedule_templates
Revises: 081_add_email_to_users
Create Date: 2026-05-11

变更内容：
  - schedule_templates 表新增 shift_type_id 列
  - 新增索引 ix_schedule_templates_shift_type_id
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "082_add_shift_type_to_schedule_templates"
down_revision = "081_add_email_to_users"
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = [idx["name"] for idx in inspector.get_indexes(table_name)]
    return index_name in indexes


def upgrade() -> None:
    if not column_exists("schedule_templates", "shift_type_id"):
        op.add_column(
            "schedule_templates",
            sa.Column(
                "shift_type_id",
                sa.String(length=36),
                sa.ForeignKey("shift_types.id"),
                nullable=True,
                comment="班次类型ID",
            ),
        )
    if not index_exists("schedule_templates", "ix_schedule_templates_shift_type_id"):
        op.create_index(
            "ix_schedule_templates_shift_type_id",
            "schedule_templates",
            ["shift_type_id"],
        )


def downgrade() -> None:
    if index_exists("schedule_templates", "ix_schedule_templates_shift_type_id"):
        op.drop_index("ix_schedule_templates_shift_type_id", table_name="schedule_templates")
    if column_exists("schedule_templates", "shift_type_id"):
        op.drop_column("schedule_templates", "shift_type_id")
