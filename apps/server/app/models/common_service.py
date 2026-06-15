"""常见服务配置模型"""
import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


class CommonService(Base, AuditMixin):
    """常见服务配置（租户级）

    用于配置首页常见服务列表，支持服务到科室/页面的映射
    """
    __tablename__ = "common_services"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=True, index=True, comment="门店ID，NULL表示全租户")

    # 服务基本信息
    name = Column(String(100), nullable=False, comment="服务名称")
    code = Column(String(50), nullable=False, comment="服务代码（唯一标识）")

    # 视觉配置
    icon = Column(String(500), comment="图标URL")
    variant = Column(String(20), comment="样式变体：blue/orange/green/pink/purple/cyan等")

    # 跳转配置
    link_type = Column(Integer, default=1, comment="跳转类型：1内部页面 2外部链接 3科室")
    link_url = Column(String(500), comment="跳转URL或路径")
    department_id = Column(String(36), ForeignKey("departments.id"), comment="关联科室ID")

    # 显示配置
    sort_order = Column(Integer, default=0, comment="排序号，越小越靠前")
    status = Column(Integer, default=1, comment="状态：0禁用 1启用")

    # 扩展字段
    description = Column(Text, comment="服务描述")

    # 关系
    department = relationship("Department", backref="common_services")
    store = relationship("Store", backref="common_services")


class HealthReminder(Base, AuditMixin):
    """健康提醒配置（租户级）

    用于配置女性健康相关的检查提醒
    """
    __tablename__ = "health_reminders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=True, index=True, comment="门店ID，NULL表示全租户")

    # 提醒类型
    reminder_type = Column(String(50), nullable=False, comment="提醒类型：checkup/check等")
    name = Column(String(100), nullable=False, comment="提醒名称")

    # 提醒内容
    title = Column(String(200), comment="提醒标题")
    content = Column(Text, comment="提醒内容")
    tips = Column(Text, comment="健康贴士（JSON数组字符串）")

    # 推荐周期（天）
    recommended_interval = Column(Integer, default=365, comment="推荐检查周期（天）")

    # 排序和状态
    sort_order = Column(Integer, default=0, comment="排序号")
    status = Column(Integer, default=1, comment="状态：0禁用 1启用")

    # 关系
    store = relationship("Store", backref="health_reminders")
