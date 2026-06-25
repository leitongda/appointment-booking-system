"""add doctor review schema

Revision ID: 124_add_doctor_review_schema
Revises: 520ef7fe0ba7
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa


revision = '124_add_doctor_review_schema'
down_revision = '520ef7fe0ba7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE doctors "
        "ADD COLUMN IF NOT EXISTS avg_rating NUMERIC(3, 2) DEFAULT 0"
    )
    op.execute("COMMENT ON COLUMN doctors.avg_rating IS '平均评分'")
    op.execute(
        "ALTER TABLE doctors "
        "ADD COLUMN IF NOT EXISTS review_count INTEGER DEFAULT 0"
    )
    op.execute("COMMENT ON COLUMN doctors.review_count IS '评价数量'")

    op.create_table(
        'doctor_reviews',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, comment='租户ID'),
        sa.Column('appointment_id', sa.String(36), sa.ForeignKey('appointments.id'), nullable=False, comment='预约ID'),
        sa.Column('doctor_id', sa.String(36), sa.ForeignKey('doctors.id'), nullable=False, comment='医生ID'),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False, comment='评价用户ID'),
        sa.Column('patient_id', sa.String(36), sa.ForeignKey('patients.id'), nullable=True, comment='就诊人ID'),
        sa.Column('rating', sa.Integer, nullable=False, comment='评分 1-5'),
        sa.Column('content', sa.Text, nullable=True, comment='评价内容'),
        sa.Column('tags', sa.JSON, nullable=True, comment='评价标签(JSON数组)'),
        sa.Column('is_anonymous', sa.Boolean, nullable=True, server_default=sa.false(), comment='是否匿名'),
        sa.Column('status', sa.Integer, nullable=True, server_default='1', comment='状态: 0-隐藏 1-正常 2-置顶'),
        sa.Column('reply', sa.Text, nullable=True, comment='医生/管理回复'),
        sa.Column('reply_at', sa.DateTime, nullable=True, comment='回复时间'),
        sa.Column('created_by', sa.String(36), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.String(36), nullable=True, comment='更新人ID'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), nullable=True, comment='更新时间'),
        sa.UniqueConstraint('appointment_id', name='uq_doctor_reviews_appointment'),
        comment='医生评价表',
        if_not_exists=True,
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_doctor_reviews_tenant_id ON doctor_reviews (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_doctor_reviews_doctor_id ON doctor_reviews (doctor_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_doctor_reviews_user_id ON doctor_reviews (user_id)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_doctor_reviews_appointment ON doctor_reviews (appointment_id)")

    op.execute(
        """
        UPDATE doctors AS d
        SET
            avg_rating = COALESCE(r.avg_rating, 0),
            review_count = COALESCE(r.review_count, 0)
        FROM (
            SELECT
                doctor_id,
                ROUND(AVG(rating)::numeric, 2) AS avg_rating,
                COUNT(*) AS review_count
            FROM doctor_reviews
            WHERE status = 1
            GROUP BY doctor_id
        ) AS r
        WHERE d.id = r.doctor_id
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_doctor_reviews_appointment")
    op.execute("DROP INDEX IF EXISTS ix_doctor_reviews_user_id")
    op.execute("DROP INDEX IF EXISTS ix_doctor_reviews_doctor_id")
    op.execute("DROP INDEX IF EXISTS ix_doctor_reviews_tenant_id")
    op.execute("DROP TABLE IF EXISTS doctor_reviews")
    op.execute("ALTER TABLE doctors DROP COLUMN IF EXISTS review_count")
    op.execute("ALTER TABLE doctors DROP COLUMN IF EXISTS avg_rating")
