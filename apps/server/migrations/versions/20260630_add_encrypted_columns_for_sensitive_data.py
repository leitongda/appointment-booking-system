"""添加敏感数据加密列

为 patients 表添加 phone 和 id_card 的加密列 + 哈希列。
阶段 1：新增列（此迁移）
阶段 2：迁移脚本填充数据（单独脚本）
阶段 3：删除明文列（后续迁移，需确认数据迁移完成）

Revision ID: 20260630_add_encrypted
Revises: f1a2b3c4d5e6_fix_email_template_unique_constraint
Create Date: 2026-06-30
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20260630_add_encrypted'
down_revision = 'c7d8e9f0a1b2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加加密列（BYTEA 类型，存储 AES-256-GCM 加密后的数据）
    op.add_column('patients', sa.Column('phone_encrypted', sa.LargeBinary(), nullable=True, comment='手机号加密存储'))
    op.add_column('patients', sa.Column('id_card_encrypted', sa.LargeBinary(), nullable=True, comment='身份证号加密存储'))

    # 添加哈希列（VARCHAR(64)，存储 SHA-256 哈希，用于搜索/去重）
    op.add_column('patients', sa.Column('phone_hash', sa.String(64), nullable=True, comment='手机号哈希（SHA-256）'))
    op.add_column('patients', sa.Column('id_card_hash', sa.String(64), nullable=True, comment='身份证号哈希（SHA-256）'))

    # 创建哈希列索引（用于搜索/去重查询）
    op.create_index('ix_patients_phone_hash', 'patients', ['phone_hash'])
    op.create_index('ix_patients_id_card_hash', 'patients', ['id_card_hash'])


def downgrade() -> None:
    # 删除索引
    op.drop_index('ix_patients_id_card_hash', table_name='patients')
    op.drop_index('ix_patients_phone_hash', table_name='patients')

    # 删除加密列
    op.drop_column('patients', 'id_card_hash')
    op.drop_column('patients', 'phone_hash')
    op.drop_column('patients', 'id_card_encrypted')
    op.drop_column('patients', 'phone_encrypted')
