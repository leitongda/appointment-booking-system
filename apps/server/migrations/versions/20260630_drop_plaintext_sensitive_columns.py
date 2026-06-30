"""删除敏感数据明文列（阶段 6）

⚠️ 不可逆操作！执行前必须确认：
1. 所有患者数据已加密（运行 migrate_encrypt_sensitive_data.py 并验证）
2. 所有 API 已使用脱敏返回（mask_patient_data）
3. 所有搜索已使用哈希匹配（phone_hash/id_card_hash）
4. 前端已适配脱敏显示

执行此迁移后，明文 phone 和 id_card 列将永久删除。
如需恢复，只能从数据库备份中恢复。

Revision ID: 20260630_drop_plaintext
Revises: 20260630_merge_heads
Create Date: 2026-06-30
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20260630_drop_plaintext'
down_revision = '20260630_merge_heads'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 删除明文列（不可逆）
    op.drop_column('patients', 'id_card')
    op.drop_column('patients', 'phone')


def downgrade() -> None:
    # 恢复明文列（需要从备份中恢复数据）
    op.add_column('patients', sa.Column('phone', sa.String(20), nullable=False))
    op.add_column('patients', sa.Column('id_card', sa.String(18), nullable=True))
