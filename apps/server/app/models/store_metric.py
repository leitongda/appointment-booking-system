"""门店经营数据预聚合模型

平台经营看台的数据底座。由 Celery 定时任务每日聚合写入，
看板查询直接读此表，避免实时全表扫描业务库。

口径说明：
- stat_date 取自 Schedule.schedule_date（就诊日），即"那一天门店实际营业情况"，
  而非 Appointment.created_at（下单日）。经营分析按就诊日归属更准确。
- 门店归属统一走 Schedule.store_id（Appointment 无 store_id 字段）。
- revenue 为预聚合值，复诊判断采用"该患者在同门店此前已有就诊记录"的批量近似
  （见 metrics 聚合服务），与 RevenueService 口径基本一致。
"""
from sqlalchemy import Column, String, Integer, Numeric, Date, ForeignKey, UniqueConstraint

from app.db.base import Base, AuditMixin
import uuid


class StoreDailyMetric(Base, AuditMixin):
    """门店每日经营指标快照

    联合唯一：(tenant_id, store_id, stat_date)。
    tenant_id 允许为 NULL（平台级门店），PG 对 NULL 不参与唯一约束判定。
    """
    __tablename__ = "store_daily_metrics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID（NULL=平台级门店）")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=False, index=True, comment="门店ID")
    stat_date = Column(Date, nullable=False, index=True, comment="统计日期（就诊日）")

    # 预约计数（按 status 分类）
    appointment_count = Column(Integer, default=0, comment="当日预约总数")
    visit_count = Column(Integer, default=0, comment="已到院数（status>=2 且非取消/爽约/过期）")
    completed_count = Column(Integer, default=0, comment="已完成数（status=5）")
    no_show_count = Column(Integer, default=0, comment="爽约数（status=8）")
    cancelled_count = Column(Integer, default=0, comment="取消/过期数（status in 6,7）")

    # 患者指标
    new_patient_count = Column(Integer, default=0, comment="当日首次到该门店就诊的新患者数")

    # 营收（预聚合，诊费累计）
    revenue = Column(Numeric(12, 2), default=0, comment="当日营收（诊费累计，预聚合）")

    __table_args__ = (
        UniqueConstraint('tenant_id', 'store_id', 'stat_date', name='uq_store_daily_metrics'),
        {'comment': '门店每日经营指标快照（平台经营看台预聚合表）'},
    )
