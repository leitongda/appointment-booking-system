"""add examination_reports table

Revision ID: 098
Revises: 097
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa

revision = "098"
down_revision = "097_add_extra_quota_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "examination_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("store_id", sa.String(36), nullable=True, index=True),
        sa.Column("record_id", sa.String(36), sa.ForeignKey("medical_records.id"), nullable=True, index=True),
        sa.Column("appointment_id", sa.String(36), sa.ForeignKey("appointments.id"), nullable=False, index=True),
        sa.Column("patient_id", sa.String(36), sa.ForeignKey("patients.id"), nullable=False, index=True),
        sa.Column("doctor_id", sa.String(36), sa.ForeignKey("doctors.id"), nullable=False, index=True),
        sa.Column("report_type", sa.String(50), nullable=False, comment="报告类型: blood_test/imaging/pathology/other"),
        sa.Column("title", sa.String(200), nullable=False, comment="报告标题"),
        sa.Column("description", sa.Text, nullable=True, comment="报告描述/备注"),
        sa.Column("file_name", sa.String(255), nullable=False, comment="原始文件名"),
        sa.Column("file_key", sa.String(500), nullable=False, comment="存储key"),
        sa.Column("file_size", sa.BigInteger, nullable=False, comment="文件大小(bytes)"),
        sa.Column("file_type", sa.String(50), nullable=False, comment="MIME类型"),
        sa.Column("file_url", sa.String(1000), nullable=True, comment="文件访问URL"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("examination_reports")
