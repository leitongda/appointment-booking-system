"""fix email template unique constraint for multi-tenant

Revision ID: f1a2b3c4d5e6
Revises: 8eb75db476d4
Create Date: 2026-06-06
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = '8eb75db476d4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 删除旧的全局唯一约束（code 列上的 unique=True）
    # PostgreSQL: 先查约束名再删除
    op.execute(
        "ALTER TABLE email_templates DROP CONSTRAINT IF EXISTS email_templates_code_key"
    )
    # 添加租户级复合唯一约束
    op.create_unique_constraint(
        'uq_email_template_code_tenant',
        'email_templates',
        ['code', 'tenant_id'],
    )


def downgrade() -> None:
    # 删除复合唯一约束
    op.drop_constraint('uq_email_template_code_tenant', 'email_templates', type_='unique')
    # 恢复全局唯一约束
    op.create_unique_constraint('email_templates_code_key', 'email_templates', ['code'])
