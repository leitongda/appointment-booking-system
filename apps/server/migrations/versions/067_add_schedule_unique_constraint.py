"""添加排班唯一约束防止并发重复

Revision ID: 067_add_schedule_unique_constraint
Revises: 066
Create Date: 2026-04-28

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '067_add_schedule_unique_constraint'
down_revision = '066_add_three_level_reminder_fields'
branch_labels = None
depends_on = None


def upgrade():
    """添加排班唯一约束：(doctor_id, schedule_date, start_time, end_time)"""

    # Step 1: 去重已有的重复排班记录，保留最早创建的
    op.execute("""
        DELETE FROM schedules
        WHERE id IN (
            SELECT a.id
            FROM schedules a
            JOIN schedules b ON
                a.doctor_id = b.doctor_id
                AND a.schedule_date = b.schedule_date
                AND a.start_time = b.start_time
                AND a.end_time = b.end_time
                AND a.start_time IS NOT NULL
                AND b.start_time IS NOT NULL
                AND a.tenant_id = b.tenant_id
                AND a.created_at > b.created_at
        )
    """)

    # Step 2: 创建部分唯一索引
    # 仅对 start_time IS NOT NULL AND end_time IS NOT NULL 的记录生效
    # 覆盖模板生成和自定义排班的主要路径
    op.execute("""
        CREATE UNIQUE INDEX uq_schedule_doctor_date_time
        ON schedules (doctor_id, schedule_date, start_time, end_time)
        WHERE start_time IS NOT NULL AND end_time IS NOT NULL
    """)


def downgrade():
    """移除唯一约束"""
    op.execute("DROP INDEX IF EXISTS uq_schedule_doctor_date_time")
