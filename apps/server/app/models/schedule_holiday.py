"""节假日设置模型，用于排班冲突检测。"""

import uuid

from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


class ScheduleHoliday(Base, AuditMixin):
    """节假日设置

    用于排班冲突检测：当某日期为法定节假日且 allow_schedule=False 时，
    排班创建/更新会返回冲突警告。
    """
    __tablename__ = "schedule_holidays"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=True, comment="门店ID，NULL 表示全租户生效")
    holiday_date = Column(Date, nullable=False, index=True, comment="节假日日期")
    name = Column(String(100), nullable=False, comment="节日名称，如：元旦、春节、国庆节")
    holiday_type = Column(
        String(20), nullable=False, default="legal",
        comment="类型: legal法定节假日 / hospital院内假日 / makeup_workday调休上班日",
    )
    allow_schedule = Column(
        Boolean, nullable=False, default=False,
        comment="是否允许排班。法定节假日默认 False；调休上班日为 True",
    )
    status = Column(Integer, default=1, comment="状态: 0已取消 1生效中")

    # 关联关系
    tenant = relationship("Tenant", backref="schedule_holidays")
    store = relationship("Store", backref="schedule_holidays")
