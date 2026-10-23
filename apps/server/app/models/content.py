import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


class News(Base, AuditMixin):
    """新闻资讯"""
    __tablename__ = "news"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID（NULL表示平台级）")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=True, index=True, comment="所属门店ID，NULL表示全局")
    title = Column(String(200), nullable=False)
    type = Column(Integer, default=1)  # 1医院动态 2健康科普 3通知公告 4政策法规
    cover_image = Column(String(500))
    summary = Column(String(500))
    content = Column(Text)
    view_count = Column(Integer, default=0)
    is_top = Column(Integer, default=0)
    status = Column(Integer, default=0)  # 0草稿 1已发布
    publish_time = Column(DateTime)
    is_deleted = Column(Boolean, default=False, nullable=False, comment="是否已删除（回收站）")
    deleted_at = Column(DateTime, nullable=True, comment="删除时间")

    store = relationship("Store", backref="news")

class Notice(Base, AuditMixin):
    """公告通知"""
    __tablename__ = "notices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID（NULL表示平台级）")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=True, index=True, comment="所属门店ID，NULL表示全局")
    title = Column(String(200), nullable=False)
    type = Column(Integer, default=1)  # 1系统公告 2停诊通知 3活动通知 4重要提醒
    content = Column(Text)
    view_count = Column(Integer, default=0, comment="浏览量")
    is_top = Column(Integer, default=0)
    status = Column(Integer, default=0)
    publish_time = Column(DateTime)
    is_deleted = Column(Boolean, default=False, nullable=False, comment="是否已删除（回收站）")
    deleted_at = Column(DateTime, nullable=True, comment="删除时间")

    store = relationship("Store", backref="notices")

class Banner(Base, AuditMixin):
    """轮播图"""
    __tablename__ = "banners"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID（NULL表示平台级）")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=True, index=True, comment="所属门店ID，NULL表示全局")
    title = Column(String(100))
    image_url = Column(String(500), nullable=False)
    link_type = Column(Integer, default=0)  # 0无跳转 1内部页面 2外部链接 3新闻详情
    link_url = Column(String(500))
    position = Column(String(50), default='home')  # home首页 department科室 profile个人中心
    sort_order = Column(Integer, default=0)
    status = Column(Integer, default=1)
    is_deleted = Column(Boolean, default=False, nullable=False, comment="是否已删除（回收站）")
    deleted_at = Column(DateTime, nullable=True, comment="删除时间")

    store = relationship("Store", backref="banners")

