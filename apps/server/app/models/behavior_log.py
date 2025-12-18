"""用户行为日志模型"""
from sqlalchemy import Column, String, Integer, Text, DateTime
from app.db.base import Base
from datetime import datetime
import uuid


class UserBehaviorLog(Base):
    """用户行为日志表"""
    __tablename__ = "user_behavior_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    platform = Column(String(20), nullable=False, comment="平台: admin/h5/miniapp")
    user_id = Column(String(36), nullable=True, comment="用户ID")
    session_id = Column(String(64), nullable=True, comment="会话ID")
    event_type = Column(String(30), nullable=False, comment="事件类型: page_view/page_leave/click/search/custom")
    page_path = Column(String(255), nullable=True, comment="页面路径")
    page_title = Column(String(100), nullable=True, comment="页面标题")
    element_id = Column(String(100), nullable=True, comment="元素ID")
    element_text = Column(String(200), nullable=True, comment="元素文本")
    search_keyword = Column(String(200), nullable=True, comment="搜索关键词")
    event_name = Column(String(100), nullable=True, comment="自定义事件名称")
    duration = Column(Integer, nullable=True, comment="停留时长(毫秒)")
    referrer = Column(String(255), nullable=True, comment="来源页面")
    extra_data = Column(Text, nullable=True, comment="额外数据(JSON)")
    ip = Column(String(50), nullable=True, comment="IP地址")
    user_agent = Column(String(500), nullable=True, comment="User-Agent")
    device_type = Column(String(20), nullable=True, comment="设备类型: desktop/mobile/tablet")
    browser = Column(String(50), nullable=True, comment="浏览器")
    os = Column(String(50), nullable=True, comment="操作系统")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

