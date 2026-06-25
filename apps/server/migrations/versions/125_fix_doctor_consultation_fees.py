"""fix doctor_consultation_fees: add use_template column, dedupe, unique constraint

Revision ID: 125_fix_doctor_consultation_fees
Revises: 124_add_doctor_review_schema
Create Date: 2026-06-24

历史问题修复：
1. 补充遗漏的 use_template 列（代码已在读写，但建表迁移漏掉了该列）
2. 按 (doctor_id, store_id, department_id, fee_type_id) 清理重复数据，保留最新一条
3. 增加唯一约束，从数据库层杜绝重复配置，避免 revenue 统计的 MultipleResultsFound
"""
from alembic import op
import sqlalchemy as sa


revision = '125_fix_doctor_consultation_fees'
down_revision = '124_add_doctor_review_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 补充遗漏的 use_template 列（默认 1 = 使用模板，兼容历史数据语义）
    op.execute(
        "ALTER TABLE doctor_consultation_fees "
        "ADD COLUMN IF NOT EXISTS use_template INTEGER DEFAULT 1"
    )
    op.execute(
        "COMMENT ON COLUMN doctor_consultation_fees.use_template "
        "IS '是否使用诊费模板: 0否 1是'"
    )

    # 2. 清理重复数据：同一 (doctor_id, store_id, department_id, fee_type_id) 只保留一条
    #    保留策略：优先 status=1，其次 created_at 最新，最后 updated_at 最新
    op.execute(
        """
        DELETE FROM doctor_consultation_fees
        WHERE id IN (
            SELECT id FROM (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY doctor_id, store_id, department_id, fee_type_id
                        ORDER BY
                            status DESC,                  -- status=1 优先
                            created_at DESC NULLS LAST,   -- 较新创建优先
                            updated_at DESC NULLS LAST    -- 较新更新优先
                    ) AS rn
                FROM doctor_consultation_fees
            ) ranked
            WHERE rn > 1
        )
        """
    )

    # 3. 增加唯一约束，从根本上杜绝重复
    op.create_unique_constraint(
        'uq_doctor_consultation_fees_doctor_store_dept_type',
        'doctor_consultation_fees',
        ['doctor_id', 'store_id', 'department_id', 'fee_type_id'],
    )


def downgrade() -> None:
    op.drop_constraint(
        'uq_doctor_consultation_fees_doctor_store_dept_type',
        'doctor_consultation_fees',
        type_='unique',
    )
    op.drop_column('doctor_consultation_fees', 'use_template')
