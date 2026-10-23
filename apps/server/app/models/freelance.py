"""兼职费用相关模型"""
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


class Freelancer(Base, AuditMixin):
    """兼职人员"""
    __tablename__ = "freelance_freelancers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=True, index=True, comment="绑定门店ID")
    name = Column(String(50), nullable=False, comment="姓名")
    phone = Column(String(20), nullable=True, comment="手机号")
    account_name = Column(String(100), nullable=True, comment="社交媒体账号名")
    account_platform = Column(String(20), default="xiaohongshu", comment="平台: xiaohongshu/douyin/weibo/wechat/other")
    account_type = Column(String(20), default="old", comment="账号类型: old/new")
    status = Column(Integer, default=1, comment="状态: 0禁用 1正常")
    access_token = Column(String(64), nullable=True, unique=True, index=True, comment="自助查看访问令牌")
    remark = Column(Text, nullable=True, comment="备注")

    # 关联关系
    store = relationship("Store", backref="freelancers")
    tasks = relationship("FreelanceTask", back_populates="freelancer")
    settlements = relationship("FreelanceSettlement", back_populates="freelancer")


class FreelanceTask(Base, AuditMixin):
    """兼职发布任务"""
    __tablename__ = "freelance_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=True, index=True, comment="门店ID")
    freelancer_id = Column(String(36), ForeignKey("freelance_freelancers.id"), nullable=False, index=True, comment="兼职人员ID")
    title = Column(String(200), nullable=False, comment="笔记标题")
    content_url = Column(String(500), nullable=True, comment="笔记链接")
    published_at = Column(DateTime, nullable=True, comment="发布时间")
    status = Column(String(20), default="pending", comment="状态: pending/published/indexed/need_modify/rejected")

    # 外部数据（管理员录入）
    is_indexed = Column(Boolean, default=False, comment="是否被平台收录")
    likes_count = Column(Integer, default=0, comment="点赞数")
    comments_count = Column(Integer, default=0, comment="评论数")

    # 金额（系统计算 + 管理员调整）
    base_amount = Column(Numeric(10, 2), default=5, comment="基础金额（固定 5 元）")
    bonus_amount = Column(Numeric(10, 2), default=0, comment="一周后补贴金额（管理员输入 5~30）")
    likes_bonus_amount = Column(Numeric(10, 2), default=0, comment="点赞奖励（0 或 10）")

    # 结算时间
    planned_base_settle_at = Column(DateTime, nullable=True, comment="理论基础结算日")
    planned_bonus_settle_at = Column(DateTime, nullable=True, comment="理论补贴结算日")
    planned_likes_settle_at = Column(DateTime, nullable=True, comment="理论点赞奖励结算日")

    remark = Column(Text, nullable=True, comment="备注")

    # 关联关系
    freelancer = relationship("Freelancer", back_populates="tasks")
    interactions = relationship("FreelanceInteraction", back_populates="task")
    settlement_items = relationship("FreelanceSettlementItem", back_populates="task")


class FreelanceInteraction(Base, AuditMixin):
    """互动记录"""
    __tablename__ = "freelance_interactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    task_id = Column(String(36), ForeignKey("freelance_tasks.id"), nullable=False, index=True, comment="关联任务ID")
    interaction_type = Column(String(20), nullable=False, comment="类型: comment/dm")
    content = Column(Text, nullable=True, comment="互动内容")
    amount = Column(Numeric(10, 2), default=0.5, comment="金额（0.5 元/条）")
    interacted_at = Column(DateTime, nullable=True, comment="互动时间")

    # 关联关系
    task = relationship("FreelanceTask", back_populates="interactions")
    settlement_item = relationship("FreelanceSettlementItem", back_populates="interaction", uselist=False)


class FreelanceSettlement(Base, AuditMixin):
    """结算单"""
    __tablename__ = "freelance_settlements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=True, index=True, comment="门店ID")
    freelancer_id = Column(String(36), ForeignKey("freelance_freelancers.id"), nullable=False, index=True, comment="兼职人员ID")
    settlement_no = Column(String(32), nullable=False, comment="结算单号（租户内唯一）")

    __table_args__ = (
        UniqueConstraint('tenant_id', 'settlement_no', name='uq_freelance_settlements_tenant_no'),
        Index(
            'uq_freelance_settlements_no_platform',
            'settlement_no',
            unique=True,
            postgresql_where=text('tenant_id IS NULL'),
            sqlite_where=text('tenant_id IS NULL'),
        ),
    )

    # 结算周期
    period_start = Column(DateTime, nullable=True, comment="结算周期开始")
    period_end = Column(DateTime, nullable=True, comment="结算周期结束")

    # 金额明细
    base_total = Column(Numeric(10, 2), default=0, comment="基础金额合计")
    bonus_total = Column(Numeric(10, 2), default=0, comment="补贴金额合计")
    likes_bonus_total = Column(Numeric(10, 2), default=0, comment="点赞奖励合计")
    interaction_total = Column(Numeric(10, 2), default=0, comment="互动金额合计")
    total_amount = Column(Numeric(10, 2), default=0, comment="总金额")
    tax_amount = Column(Numeric(10, 2), default=0, comment="税额")
    actual_amount = Column(Numeric(10, 2), default=0, comment="实际支付金额")

    # 状态和审核
    status = Column(String(20), default="pending", comment="状态: pending/confirmed/paid/cancelled")
    confirmed_at = Column(DateTime, nullable=True, comment="确认时间")
    confirmed_by = Column(String(36), nullable=True, comment="确认人ID")
    paid_at = Column(DateTime, nullable=True, comment="支付时间")
    reject_reason = Column(Text, nullable=True, comment="驳回原因")
    remark = Column(Text, nullable=True, comment="备注")

    # 关联关系
    freelancer = relationship("Freelancer", back_populates="settlements")
    items = relationship("FreelanceSettlementItem", back_populates="settlement", cascade="all, delete-orphan")


class FreelanceSettlementItem(Base):
    """结算明细"""
    __tablename__ = "freelance_settlement_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    settlement_id = Column(String(36), ForeignKey("freelance_settlements.id", ondelete="CASCADE"), nullable=False, index=True, comment="结算单ID")
    item_type = Column(String(20), nullable=False, comment="明细类型: base/bonus/likes_bonus/interaction")
    task_id = Column(String(36), ForeignKey("freelance_tasks.id"), nullable=True, comment="关联任务ID")
    interaction_id = Column(String(36), ForeignKey("freelance_interactions.id"), nullable=True, comment="关联互动ID")
    description = Column(String(200), nullable=True, comment="描述")
    amount = Column(Numeric(10, 2), default=0, comment="金额")
    created_at = Column(DateTime, nullable=True, comment="创建时间")

    # 关联关系
    settlement = relationship("FreelanceSettlement", back_populates="items")
    task = relationship("FreelanceTask", back_populates="settlement_items")
    interaction = relationship("FreelanceInteraction", back_populates="settlement_item")
