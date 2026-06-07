"""add data scope model and role foreign key

Revision ID: a3b4c5d6e7f8
Revises: f1a2b3c4d5e6
Create Date: 2026-06-06 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a3b4c5d6e7f8'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 data_scopes 表
    op.create_table(
        'data_scopes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, index=True, comment='租户ID（NULL表示平台级）'),
        sa.Column('name', sa.String(100), nullable=False, comment='范围名称'),
        sa.Column('scope_type', sa.String(20), nullable=False, comment='范围类型: all/tenant/store/custom'),
        sa.Column('store_ids', sa.Text(), nullable=True, comment='门店ID列表，JSON格式'),
        sa.Column('description', sa.String(200), nullable=True, comment='描述'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), comment='更新时间'),
        sa.Column('created_by', sa.String(36), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.String(36), nullable=True, comment='更新人ID'),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_data_scope_tenant_name'),
        comment='数据权限范围表',
    )

    # roles 表新增 data_scope_id 外键
    op.add_column('roles', sa.Column(
        'data_scope_id', sa.String(36),
        sa.ForeignKey('data_scopes.id'),
        nullable=True,
        comment='数据权限范围ID',
    ))


def downgrade() -> None:
    op.drop_column('roles', 'data_scope_id')
    op.drop_table('data_scopes')
