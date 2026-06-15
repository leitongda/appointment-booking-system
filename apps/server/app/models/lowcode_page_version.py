"""低代码页面版本历史模型。"""

import uuid

from sqlalchemy import Column, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import AuditMixin, Base


class LowCodePageVersion(Base, AuditMixin):
    """低代码页面版本历史，每次发布或手动保存时生成。"""

    __tablename__ = "lowcode_page_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    page_id = Column(
        String(36),
        ForeignKey("lowcode_pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="页面ID",
    )
    tenant_id = Column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="租户ID",
    )
    version = Column(Integer, nullable=False, comment="版本号，从1递增")
    schema_data = Column(JSONB, nullable=False, comment="页面Schema快照")
    data_sources = Column(JSONB, nullable=False, default=list, comment="数据源配置快照")
    snapshot_label = Column(
        String(200), nullable=True, comment="版本标签，如 '发布 v1.2'"
    )
    created_by = Column(
        String(36),
        ForeignKey("accounts.id"),
        nullable=True,
        comment="创建人账号ID",
    )

    __table_args__ = (
        UniqueConstraint("page_id", "version", name="uq_lowcode_page_versions_page_version"),
        Index("ix_lowcode_page_versions_page_id", "page_id"),
        Index("ix_lowcode_page_versions_tenant_id", "tenant_id"),
        {"comment": "低代码页面版本历史表"},
    )
