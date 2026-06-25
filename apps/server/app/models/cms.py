"""CMS 内容站点相关模型

三级结构：站点(Site) → 栏目(Category，树形) → 文章(Article)

4 张表：
- CmsSite — 站点（多站点 CMS，租户下可建多个站点）
- CmsCategory — 栏目（树形，归属站点）
- CmsArticle — 文章（富文本，归属站点，可选归属门店）
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


# ============================================================
# CmsSite — 站点
# ============================================================

class CmsSite(Base, AuditMixin):
    """站点 — 多站点 CMS，一个租户可拥有多个站点（官网、活动专题站等）"""
    __tablename__ = "cms_sites"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")

    # --- 基础信息 ---
    name = Column(String(100), nullable=False, comment="站点名称")
    code = Column(String(50), nullable=False, comment="站点编码（租户内唯一）")
    description = Column(String(500), nullable=True, comment="站点描述")
    domain = Column(String(200), nullable=True, comment="绑定域名")

    # --- 视觉资源 ---
    logo_url = Column(String(500), nullable=True, comment="站点Logo URL")
    favicon_url = Column(String(500), nullable=True, comment="站点图标 URL")

    # --- 配置（JSON 文本） ---
    theme_config = Column(Text, nullable=True, comment="主题配置 JSON（主色等）")
    seo_config = Column(Text, nullable=True, comment="SEO 配置 JSON")

    # --- 状态 ---
    status = Column(Integer, default=1, comment="状态 0禁用 1正常")
    is_default = Column(Integer, default=0, comment="是否默认站点 0否 1是")

    # --- 软删除 ---
    is_deleted = Column(Boolean, default=False, nullable=False, comment="是否软删除")
    deleted_at = Column(DateTime, nullable=True, comment="软删除时间")

    # --- 关联关系 ---
    categories = relationship("CmsCategory", back_populates="site", lazy="selectin")
    articles = relationship("CmsArticle", back_populates="site", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_cms_site_tenant_code"),
        {"comment": "CMS 站点表"},
    )


# ============================================================
# CmsCategory — 栏目（树形）
# ============================================================

class CmsCategory(Base, AuditMixin):
    """栏目 — 树形结构，归属站点，支持多级父子"""
    __tablename__ = "cms_categories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    site_id = Column(String(36), ForeignKey("cms_sites.id"), nullable=False, index=True, comment="所属站点ID")

    # --- 栏目信息 ---
    name = Column(String(100), nullable=False, comment="栏目名称")
    slug = Column(String(100), nullable=False, comment="栏目标识（站点内唯一）")
    parent_id = Column(String(36), ForeignKey("cms_categories.id"), nullable=True, comment="父栏目ID（树形）")
    sort_order = Column(Integer, default=0, comment="排序")
    icon = Column(String(255), nullable=True, comment="栏目图标")
    description = Column(String(500), nullable=True, comment="栏目描述")

    # --- 状态 ---
    status = Column(Integer, default=1, comment="状态 0禁用 1正常")
    is_deleted = Column(Boolean, default=False, nullable=False, comment="是否软删除")
    deleted_at = Column(DateTime, nullable=True, comment="软删除时间")

    # --- 关联关系 ---
    site = relationship("CmsSite", back_populates="categories")
    children = relationship("CmsCategory", backref="parent", remote_side="CmsCategory.id", lazy="selectin")
    articles = relationship("CmsArticle", back_populates="category", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("site_id", "slug", name="uq_cms_category_site_slug"),
        {"comment": "CMS 栏目表（树形）"},
    )


# ============================================================
# CmsArticle — 文章
# ============================================================

class CmsArticle(Base, AuditMixin):
    """文章 — 富文本内容，归属站点，可选归属门店"""
    __tablename__ = "cms_articles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    site_id = Column(String(36), ForeignKey("cms_sites.id"), nullable=False, index=True, comment="所属站点ID")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=True, index=True, comment="所属门店ID（NULL=站点级）")
    category_id = Column(String(36), ForeignKey("cms_categories.id"), nullable=True, index=True, comment="所属栏目ID")

    # --- 内容信息 ---
    title = Column(String(200), nullable=False, comment="文章标题")
    subtitle = Column(String(200), nullable=True, comment="副标题")
    slug = Column(String(200), nullable=True, comment="文章标识")
    cover_image = Column(String(500), nullable=True, comment="封面图 URL")
    summary = Column(String(500), nullable=True, comment="摘要")
    content = Column(Text, nullable=True, comment="正文（富文本 HTML）")
    author = Column(String(50), nullable=True, comment="作者")
    source = Column(String(100), nullable=True, comment="来源")
    tags = Column(Text, nullable=True, comment="标签 JSON 数组")

    # --- 排序与置顶 ---
    sort_order = Column(Integer, default=0, comment="排序")
    is_top = Column(Integer, default=0, comment="是否置顶 0否 1是")

    # --- 发布状态 ---
    status = Column(Integer, default=0, comment="状态 0草稿 1已发布 2已下线")
    publish_time = Column(DateTime, nullable=True, comment="发布时间")

    # --- 统计 ---
    view_count = Column(Integer, default=0, comment="浏览量")

    # --- SEO ---
    seo_title = Column(String(200), nullable=True, comment="SEO 标题")
    seo_keywords = Column(String(500), nullable=True, comment="SEO 关键词")
    seo_description = Column(String(500), nullable=True, comment="SEO 描述")

    # --- 软删除 ---
    is_deleted = Column(Boolean, default=False, nullable=False, comment="是否软删除")
    deleted_at = Column(DateTime, nullable=True, comment="软删除时间")

    # --- 关联关系 ---
    site = relationship("CmsSite", back_populates="articles")
    category = relationship("CmsCategory", back_populates="articles")

    __table_args__ = (
        {"comment": "CMS 文章表"},
    )
