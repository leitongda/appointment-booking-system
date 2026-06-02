"""低代码模板市场数据模型。"""

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base, AuditMixin
import uuid


class LowCodeTemplate(Base, AuditMixin):
    """低代码市场模板。"""

    __tablename__ = "lowcode_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_page_id = Column(
        String(36),
        ForeignKey("lowcode_pages.id"),
        nullable=True,
        index=True,
        comment="来源页面ID",
    )
    source_tenant_id = Column(
        String(36),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True,
        comment="来源租户ID",
    )
    name = Column(String(200), nullable=False, comment="模板名称")
    description = Column(Text, nullable=True, comment="模板描述")
    thumbnail_url = Column(String(500), nullable=True, comment="缩略图URL")
    category = Column(String(50), nullable=False, index=True, comment="模板分类")
    tags = Column(JSONB, nullable=True, default=list, comment="标签列表")
    schema_data = Column(JSONB, nullable=False, comment="模板Schema JSON")
    data_sources = Column(JSONB, nullable=True, default=list, comment="数据源配置")
    version = Column(String(20), nullable=False, default="1.0.0", comment="模板版本")
    is_public = Column(Boolean, nullable=False, default=False, comment="是否公开")
    is_official = Column(Boolean, nullable=False, default=False, comment="是否官方")
    download_count = Column(Integer, nullable=False, default=0, comment="下载次数")
    fork_count = Column(Integer, nullable=False, default=0, comment="Fork次数")
    like_count = Column(Integer, nullable=False, default=0, comment="收藏次数")
    status = Column(Integer, nullable=False, default=1, comment="状态: 0禁用 1正常")
    created_by = Column(
        String(36),
        ForeignKey("accounts.id"),
        nullable=True,
        index=True,
        comment="创建人ID",
    )

    __table_args__ = (
        UniqueConstraint("source_page_id", name="uq_lowcode_templates_source_page"),
        {"comment": "低代码市场模板表"},
    )
