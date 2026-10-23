"""P3-1: content tables add tenant_id + backfill

Revision ID: p3a1_content_tenant
Revises: 20260630_drop_plaintext
Create Date: 2026-10-23

新增 news/notices/banners/content_versions 的 tenant_id 列，并按门店回填。
store_id 为 NULL 的存量行保持 tenant_id=NULL（平台级全局内容）。
downgrade 只删列/索引，回填数据不可自动恢复——升级前请备份四表。
"""
import sqlalchemy as sa
from alembic import op

revision = "p3a1_content_tenant"
down_revision = "20260630_drop_plaintext"
branch_labels = None
depends_on = None

BACKFILL_STATEMENTS = (
    sa.text(
        "UPDATE news SET tenant_id = (SELECT s.tenant_id FROM stores s WHERE s.id = news.store_id) "
        "WHERE news.store_id IS NOT NULL AND news.tenant_id IS NULL"
    ),
    sa.text(
        "UPDATE notices SET tenant_id = (SELECT s.tenant_id FROM stores s WHERE s.id = notices.store_id) "
        "WHERE notices.store_id IS NOT NULL AND notices.tenant_id IS NULL"
    ),
    sa.text(
        "UPDATE banners SET tenant_id = (SELECT s.tenant_id FROM stores s WHERE s.id = banners.store_id) "
        "WHERE banners.store_id IS NOT NULL AND banners.tenant_id IS NULL"
    ),
)


def upgrade() -> None:
    op.add_column("news", sa.Column("tenant_id", sa.String(36), nullable=True))
    op.add_column("notices", sa.Column("tenant_id", sa.String(36), nullable=True))
    op.add_column("banners", sa.Column("tenant_id", sa.String(36), nullable=True))
    op.add_column("content_versions", sa.Column("tenant_id", sa.String(36), nullable=True))

    for statement in BACKFILL_STATEMENTS:
        op.execute(statement)

    op.create_index("ix_news_tenant_id", "news", ["tenant_id"])
    op.create_index("ix_notices_tenant_id", "notices", ["tenant_id"])
    op.create_index("ix_banners_tenant_id", "banners", ["tenant_id"])
    op.create_index("ix_content_versions_tenant_id", "content_versions", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_content_versions_tenant_id", table_name="content_versions")
    op.drop_index("ix_banners_tenant_id", table_name="banners")
    op.drop_index("ix_notices_tenant_id", table_name="notices")
    op.drop_index("ix_news_tenant_id", table_name="news")
    op.drop_column("content_versions", "tenant_id")
    op.drop_column("banners", "tenant_id")
    op.drop_column("notices", "tenant_id")
    op.drop_column("news", "tenant_id")
