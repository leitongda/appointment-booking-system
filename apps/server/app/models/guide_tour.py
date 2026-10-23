"""操作指引模型

GuideTour: 指引定义（平台管理员配置）
GuideTourProgress: 用户进度（每人每条指引一行）
"""
import uuid

from sqlalchemy import Column, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import AuditMixin, Base


class GuideTour(Base, AuditMixin):
    """操作指引定义

    steps JSONB 结构示例:
    [
      {
        "target": ".dashboard-stat-card",
        "placement": "bottom",
        "route": "/dashboard",
        "title": {"zh": "欢迎", "en": "Welcome"},
        "description": {"zh": "这是您的工作台", "en": "This is your workspace"},
        "highlightPadding": 8
      }
    ]
    """
    __tablename__ = "guide_tours"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(100), nullable=False, index=True, comment="唯一标识（租户内唯一，NULL 租户为平台指引）")
    title = Column(JSONB, nullable=False, comment="多语言标题 {zh, en}")
    description = Column(JSONB, nullable=True, comment="多语言描述 {zh, en}")
    steps = Column(JSONB, nullable=False, default=list, comment="步骤数组")
    status = Column(Integer, default=0, nullable=False, comment="0=草稿, 1=已发布")
    sort_order = Column(Integer, default=0, comment="排序")
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="NULL=全局指引")

    __table_args__ = (
        UniqueConstraint('tenant_id', 'code', name='uq_guide_tours_tenant_code'),
        Index(
            'uq_guide_tours_code_platform',
            'code',
            unique=True,
            postgresql_where=text('tenant_id IS NULL'),
            sqlite_where=text('tenant_id IS NULL'),
        ),
        {'comment': '操作指引定义'},
    )


class GuideTourProgress(Base):
    """用户指引进度"""
    __tablename__ = "guide_tour_progress"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tour_id = Column(String(36), ForeignKey("guide_tours.id", ondelete="CASCADE"), nullable=False, index=True)
    admin_id = Column(String(36), ForeignKey("admins.id"), nullable=False, index=True)
    current_step = Column(Integer, default=0, comment="当前步骤索引")
    status = Column(Integer, default=0, comment="0=进行中, 1=已完成, 2=跳过")

    __table_args__ = (
        UniqueConstraint('tour_id', 'admin_id', name='uq_guide_tour_progress'),
        {'comment': '用户指引进度'},
    )
