"""add cms sites/categories/articles

Revision ID: 8de6e51b859f
Revises: a1b2c3d4e5f6
Create Date: 2026-06-25 21:48:15.741618

新增 CMS 内容站点模块三张表：
- cms_sites       站点（多站点 CMS，租户隔离）
- cms_categories  栏目（树形，归属站点）
- cms_articles    文章（富文本，归属站点，可选归属门店）

注意：autogenerate 同时检测到若干既有表的结构偏差（注释/索引/重复建表），
均与本次 CMS 改动无关，此处不纳入，仅创建 CMS 三表。
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8de6e51b859f'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- 站点 ---
    op.create_table(
        'cms_sites',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False, comment='租户ID'),
        sa.Column('name', sa.String(length=100), nullable=False, comment='站点名称'),
        sa.Column('code', sa.String(length=50), nullable=False, comment='站点编码（租户内唯一）'),
        sa.Column('description', sa.String(length=500), nullable=True, comment='站点描述'),
        sa.Column('domain', sa.String(length=200), nullable=True, comment='绑定域名'),
        sa.Column('logo_url', sa.String(length=500), nullable=True, comment='站点Logo URL'),
        sa.Column('favicon_url', sa.String(length=500), nullable=True, comment='站点图标 URL'),
        sa.Column('theme_config', sa.Text(), nullable=True, comment='主题配置 JSON（主色等）'),
        sa.Column('seo_config', sa.Text(), nullable=True, comment='SEO 配置 JSON'),
        sa.Column('status', sa.Integer(), nullable=True, comment='状态 0禁用 1正常'),
        sa.Column('is_default', sa.Integer(), nullable=True, comment='是否默认站点 0否 1是'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, comment='是否软删除'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, comment='软删除时间'),
        sa.Column('created_by', sa.String(length=36), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.String(length=36), nullable=True, comment='更新人ID'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'code', name='uq_cms_site_tenant_code'),
        comment='CMS 站点表',
    )
    op.create_index(op.f('ix_cms_sites_tenant_id'), 'cms_sites', ['tenant_id'], unique=False)

    # --- 栏目（树形） ---
    op.create_table(
        'cms_categories',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False, comment='租户ID'),
        sa.Column('site_id', sa.String(length=36), nullable=False, comment='所属站点ID'),
        sa.Column('name', sa.String(length=100), nullable=False, comment='栏目名称'),
        sa.Column('slug', sa.String(length=100), nullable=False, comment='栏目标识（站点内唯一）'),
        sa.Column('parent_id', sa.String(length=36), nullable=True, comment='父栏目ID（树形）'),
        sa.Column('sort_order', sa.Integer(), nullable=True, comment='排序'),
        sa.Column('icon', sa.String(length=255), nullable=True, comment='栏目图标'),
        sa.Column('description', sa.String(length=500), nullable=True, comment='栏目描述'),
        sa.Column('status', sa.Integer(), nullable=True, comment='状态 0禁用 1正常'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, comment='是否软删除'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, comment='软删除时间'),
        sa.Column('created_by', sa.String(length=36), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.String(length=36), nullable=True, comment='更新人ID'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
        sa.ForeignKeyConstraint(['parent_id'], ['cms_categories.id']),
        sa.ForeignKeyConstraint(['site_id'], ['cms_sites.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('site_id', 'slug', name='uq_cms_category_site_slug'),
        comment='CMS 栏目表（树形）',
    )
    op.create_index(op.f('ix_cms_categories_site_id'), 'cms_categories', ['site_id'], unique=False)
    op.create_index(op.f('ix_cms_categories_tenant_id'), 'cms_categories', ['tenant_id'], unique=False)

    # --- 文章 ---
    op.create_table(
        'cms_articles',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False, comment='租户ID'),
        sa.Column('site_id', sa.String(length=36), nullable=False, comment='所属站点ID'),
        sa.Column('store_id', sa.String(length=36), nullable=True, comment='所属门店ID（NULL=站点级）'),
        sa.Column('category_id', sa.String(length=36), nullable=True, comment='所属栏目ID'),
        sa.Column('title', sa.String(length=200), nullable=False, comment='文章标题'),
        sa.Column('subtitle', sa.String(length=200), nullable=True, comment='副标题'),
        sa.Column('slug', sa.String(length=200), nullable=True, comment='文章标识'),
        sa.Column('cover_image', sa.String(length=500), nullable=True, comment='封面图 URL'),
        sa.Column('summary', sa.String(length=500), nullable=True, comment='摘要'),
        sa.Column('content', sa.Text(), nullable=True, comment='正文（富文本 HTML）'),
        sa.Column('author', sa.String(length=50), nullable=True, comment='作者'),
        sa.Column('source', sa.String(length=100), nullable=True, comment='来源'),
        sa.Column('tags', sa.Text(), nullable=True, comment='标签 JSON 数组'),
        sa.Column('sort_order', sa.Integer(), nullable=True, comment='排序'),
        sa.Column('is_top', sa.Integer(), nullable=True, comment='是否置顶 0否 1是'),
        sa.Column('status', sa.Integer(), nullable=True, comment='状态 0草稿 1已发布 2已下线'),
        sa.Column('publish_time', sa.DateTime(), nullable=True, comment='发布时间'),
        sa.Column('view_count', sa.Integer(), nullable=True, comment='浏览量'),
        sa.Column('seo_title', sa.String(length=200), nullable=True, comment='SEO 标题'),
        sa.Column('seo_keywords', sa.String(length=500), nullable=True, comment='SEO 关键词'),
        sa.Column('seo_description', sa.String(length=500), nullable=True, comment='SEO 描述'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, comment='是否软删除'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, comment='软删除时间'),
        sa.Column('created_by', sa.String(length=36), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.String(length=36), nullable=True, comment='更新人ID'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
        sa.ForeignKeyConstraint(['category_id'], ['cms_categories.id']),
        sa.ForeignKeyConstraint(['site_id'], ['cms_sites.id']),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
        comment='CMS 文章表',
    )
    op.create_index(op.f('ix_cms_articles_category_id'), 'cms_articles', ['category_id'], unique=False)
    op.create_index(op.f('ix_cms_articles_site_id'), 'cms_articles', ['site_id'], unique=False)
    op.create_index(op.f('ix_cms_articles_store_id'), 'cms_articles', ['store_id'], unique=False)
    op.create_index(op.f('ix_cms_articles_tenant_id'), 'cms_articles', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_cms_articles_tenant_id'), table_name='cms_articles')
    op.drop_index(op.f('ix_cms_articles_store_id'), table_name='cms_articles')
    op.drop_index(op.f('ix_cms_articles_site_id'), table_name='cms_articles')
    op.drop_index(op.f('ix_cms_articles_category_id'), table_name='cms_articles')
    op.drop_table('cms_articles')
    op.drop_index(op.f('ix_cms_categories_tenant_id'), table_name='cms_categories')
    op.drop_index(op.f('ix_cms_categories_site_id'), table_name='cms_categories')
    op.drop_table('cms_categories')
    op.drop_index(op.f('ix_cms_sites_tenant_id'), table_name='cms_sites')
    op.drop_table('cms_sites')
