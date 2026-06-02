"""create lowcode_pages table

Revision ID: 4520ac91df2d
Revises: 8c3d04cbc758
Create Date: 2026-06-01 23:38:29.379934

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4520ac91df2d'
down_revision = '8c3d04cbc758'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建低代码搭建页面表。"""
    op.create_table(
        'lowcode_pages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False, comment='租户ID'),
        sa.Column('name', sa.String(length=100), nullable=False, comment='页面名称'),
        sa.Column('slug', sa.String(length=100), nullable=False, comment='页面标识(租户内唯一)'),
        sa.Column('description', sa.String(length=500), nullable=True, comment='页面描述'),
        sa.Column('schema_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='页面Schema JSON'),
        sa.Column('status', sa.Integer(), nullable=True, comment='状态: 0草稿 1已发布 2已归档'),
        sa.Column('thumbnail_url', sa.String(length=500), nullable=True, comment='缩略图URL'),
        sa.Column('miniapp_instance_id', sa.String(length=36), nullable=True, comment='关联小程序实例ID'),
        sa.Column('created_by', sa.String(length=36), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.String(length=36), nullable=True, comment='更新人ID'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
        sa.ForeignKeyConstraint(['miniapp_instance_id'], ['miniapp_instances.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'slug', name='uq_lowcode_pages_tenant_slug'),
        comment='低代码搭建页面表',
    )
    op.create_index(
        op.f('ix_lowcode_pages_tenant_id'),
        'lowcode_pages',
        ['tenant_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_lowcode_pages_miniapp_instance_id'),
        'lowcode_pages',
        ['miniapp_instance_id'],
        unique=False,
    )


def downgrade() -> None:
    """删除低代码搭建页面表。"""
    op.drop_index(op.f('ix_lowcode_pages_miniapp_instance_id'), table_name='lowcode_pages')
    op.drop_index(op.f('ix_lowcode_pages_tenant_id'), table_name='lowcode_pages')
    op.drop_table('lowcode_pages')
