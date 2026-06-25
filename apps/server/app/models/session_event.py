"""会话回放与热力图数据模型

- SessionEvent: rrweb 录制事件批次（每个 batch 一行，session_id 串联成完整会话）
- HeatmapPoint: 热力图坐标聚合点（相对坐标 + 视口分桶 + 量化网格）
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)

from app.db.base import Base


class SessionEvent(Base):
    """会话回放事件批次表

    每行 = 前端一次批量上报的 rrweb 事件段。同一 session_id 的多行
    按 created_at 顺序拼接即为完整会话。rrweb 原始事件 JSON 落对象存储，
    本表只存索引（storage_url）。
    """
    __tablename__ = "session_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    platform = Column(String(20), nullable=False, comment="平台: admin/h5/miniapp")
    session_id = Column(String(64), nullable=False, index=True, comment="会话ID，与 behavior_log 共用")
    actor_id = Column(String(36), nullable=True, index=True, comment="操作者ID（员工 account_id）")
    actor_name = Column(String(100), nullable=True, comment="操作者姓名")
    viewport_w = Column(Integer, nullable=True, comment="录制视口宽(px)，热力图分桶用")
    viewport_h = Column(Integer, nullable=True, comment="录制视口高(px)")
    page_path = Column(String(255), nullable=True, index=True, comment="本批次主要页面路径")
    event_count = Column(Integer, nullable=False, default=0, comment="本批次事件数")
    storage_url = Column(String(512), nullable=True, comment="rrweb 事件 JSON 的对象存储路径")
    storage_key = Column(String(512), nullable=True, comment="对象存储 key（清理用）")
    sequence = Column(Integer, nullable=False, default=0, comment="会话内批次序号")
    started_at = Column(DateTime, nullable=True, comment="本批次起始时间")
    ended_at = Column(DateTime, nullable=True, comment="本批次结束时间")
    ip = Column(String(50), nullable=True, comment="IP地址")
    user_agent = Column(String(500), nullable=True, comment="User-Agent")
    created_at = Column(DateTime, default=datetime.utcnow, index=True, comment="创建时间")


class HeatmapPoint(Base):
    """热力图坐标聚合点

    存相对坐标（0~1）+ 视口分桶 + 量化网格（0.01 步进，最多 100×100 格/页/桶/天）。
    通过 (tenant_id, page_path, viewport_bucket, event_type, x_ratio, y_ratio, day)
    唯一约束 + ON CONFLICT DO UPDATE 实现 upsert 聚合。
    """
    __tablename__ = "heatmap_points"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "page_path",
            "viewport_bucket",
            "event_type",
            "x_ratio",
            "y_ratio",
            "day",
            name="uq_heatmap_point_cell",
        ),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    page_path = Column(String(255), nullable=False, index=True, comment="页面路径")
    viewport_bucket = Column(
        String(20), nullable=False, index=True,
        comment="视口分桶: lg(>1440)/md(768-1440)/sm(<768)",
    )
    event_type = Column(String(20), nullable=False, comment="事件类型: click/move")
    x_ratio = Column(Numeric(5, 4), nullable=False, comment="x/视口宽，0~1 相对坐标（量化到 0.01）")
    y_ratio = Column(Numeric(5, 4), nullable=False, comment="y/视口高，0~1 相对坐标（量化到 0.01）")
    weight = Column(Integer, nullable=False, default=1, comment="聚合计数")
    day = Column(Date, nullable=False, index=True, comment="日期，按天分区清理")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
