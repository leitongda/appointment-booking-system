"""低代码页面数据模型。"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


class LowCodePage(Base, AuditMixin):
    """低代码搭建页面。"""

    __tablename__ = "lowcode_pages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    name = Column(String(100), nullable=False, comment="页面名称")
    slug = Column(String(100), nullable=False, comment="页面标识(租户内唯一)")
    description = Column(String(500), nullable=True, comment="页面描述")
    schema_data = Column(JSONB, nullable=False, default=dict, comment="页面Schema JSON")
    status = Column(Integer, default=0, comment="状态: 0草稿 1已发布 2已归档")
    current_version = Column(Integer, default=0, comment="当前版本号")
    publish_count = Column(Integer, default=0, comment="发布次数")
    thumbnail_url = Column(String(500), nullable=True, comment="缩略图URL")
    miniapp_instance_id = Column(
        String(36),
        ForeignKey("miniapp_instances.id"),
        nullable=True,
        index=True,
        comment="关联小程序实例ID",
    )
    deploy_status = Column(
        String(30),
        default="idle",
        nullable=False,
        comment="部署状态: idle|building|built|uploading|uploaded|auditing|published|failed",
    )
    last_deploy_at = Column(DateTime, nullable=True, comment="最近部署时间")
    last_build_job_id = Column(
        String(36),
        # use_alter=True 打破与 build_jobs.lowcode_page_id 的 FK 环：
        # 本列是可空的反向指针，标记为 ALTER 后建约束，
        # 让 SQLAlchemy 能正确排序建表 (消除 SAWarning 与 SQLite 测试建表失败)。
        # 生产库该约束本就以 op.create_foreign_key (ALTER) 方式创建，行为不变。
        ForeignKey("build_jobs.id", use_alter=True, name="fk_lowcode_pages_last_build_job_id"),
        nullable=True,
        index=True,
        comment="最近构建任务ID",
    )

    miniapp_instance = relationship("MiniappInstance", backref="lowcode_pages")
    last_build_job = relationship("BuildJob", foreign_keys=[last_build_job_id], uselist=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_lowcode_pages_tenant_slug"),
        {"comment": "低代码搭建页面表"},
    )
