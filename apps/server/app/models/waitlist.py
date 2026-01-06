"""
候补队列模型

当班次容量已满时，用户可以选择进入候补队列
当有号源释放时，系统可以自动或手动将候补用户提升为预约
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.base import Base


class WaitlistEntry(Base):
    """候补队列表项

    记录用户对某个班次的候补请求
    """
    __tablename__ = 'waitlist_entries'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment='候补ID')

    # 关联信息
    user_id = Column(String(36), nullable=False, index=True, comment='用户ID')
    patient_id = Column(String(36), nullable=False, comment='就诊人ID')
    schedule_id = Column(String(36), nullable=False, index=True, comment='排班ID')
    shift_type_id = Column(String(36), nullable=True, comment='班次类型ID')

    # 候补状态
    status = Column(String(20), nullable=False, default='WAITING', comment='状态: WAITING-等待中, PROMOTED-已转预约, CANCELLED-已取消, EXPIRED-已过期')

    # 队列位置（冗余字段，便于快速查询）
    position = Column(Integer, nullable=False, comment='在队列中的位置')

    # 优先级（值越小优先级越高）
    priority = Column(Integer, nullable=False, default=100, comment='优先级')

    # 预约信息快照（用于后续创建预约）
    symptom_description = Column(String(500), nullable=True, comment='症状描述')

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment='加入候补时间')
    promoted_at = Column(DateTime, nullable=True, comment='转预约时间')
    cancelled_at = Column(DateTime, nullable=True, comment='取消时间')

    # 操作人信息
    operator_id = Column(String(36), nullable=True, comment='操作人ID')
    operator_type = Column(String(20), nullable=True, comment='操作人类型: USER/ADMIN/SYSTEM')

    # 关系 - 使用 primaryjoin 显式指定 join 条件
    schedule = relationship('Schedule', primaryjoin="WaitlistEntry.schedule_id == Schedule.id")

    # 索引
    __table_args__ = (
        Index('ix_waitlist_schedule_status', 'schedule_id', 'status'),
        Index('ix_waitlist_created_at', 'created_at'),
        Index('ix_waitlist_position', 'schedule_id', 'position'),
    )

    def __repr__(self):
        return f'<WaitlistEntry(id={self.id}, user_id={self.user_id}, schedule_id={self.schedule_id}, position={self.position})>'
