"""低代码模板版本历史与模板 Fork 模型。"""

import uuid

from sqlalchemy import Column, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import AuditMixin, Base


class LowCodeTemplateVersion(Base, AuditMixin):
    """低代码模板版本历史，每次发布或手动保存时生成。"""

    __tablename__ = "lowcode_template_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    template_id = Column(
        String(36),
        ForeignKey("lowcode_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="模板ID",
    )
    version = Column(String(20), nullable=False, comment="语义化版本号，如 1.0.0")
    schema_data = Column(JSONB, nullable=False, comment="模板Schema快照")
    data_sources = Column(JSONB, nullable=False, default=dict, comment="数据源配置快照")
    changelog = Column(Text, nullable=True, comment="版本变更说明")
    status = Column(Integer, nullable=False, default=1, comment="版本状态: 1-草稿 2-已发布 3-已废弃")
    created_by = Column(
        String(36),
        ForeignKey("accounts.id"),
        nullable=True,
        comment="创建人账号ID",
    )

    __table_args__ = (
        UniqueConstraint("template_id", "version", name="uq_lowcode_template_versions_template_version"),
        Index("ix_lowcode_template_versions_template_id", "template_id"),
        {"comment": "低代码模板版本历史表"},
    )


class LowCodeTemplateFork(Base):
    """低代码模板 Fork 记录，追踪谁 fork 了哪个模板。"""

    __tablename__ = "lowcode_template_forks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    original_template_id = Column(
        String(36),
        ForeignKey("lowcode_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="原始模板ID",
    )
    forked_page_id = Column(
        String(36),
        ForeignKey("lowcode_pages.id", ondelete="SET NULL"),
        nullable=True,
        comment="Fork 生成的页面ID",
    )
    forked_by_tenant_id = Column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Fork 操作的租户ID",
    )
    forked_by_account_id = Column(
        String(36),
        ForeignKey("accounts.id"),
        nullable=False,
        comment="Fork 操作的账号ID",
    )
    created_at = Column(
        Integer,
        nullable=False,
        comment="Fork 时间戳（秒级 Unix 时间戳）",
    )

    __table_args__ = (
        Index("ix_lowcode_template_forks_original_template_id", "original_template_id"),
        Index("ix_lowcode_template_forks_forked_by_tenant_id", "forked_by_tenant_id"),
        {"comment": "低代码模板Fork记录表"},
    )
