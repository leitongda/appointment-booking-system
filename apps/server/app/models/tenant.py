"""租户相关模型

多租户架构核心模型：
- Tenant: 租户（医院/诊所/医疗集团）
- TenantSubscription: 租户订阅记录
- TenantUsageLog: 租户用量统计
- SubscriptionPlan: 订阅计划
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Numeric, Date, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base, AuditMixin
from datetime import datetime
import uuid


class SubscriptionPlan(Base, AuditMixin):
    """订阅计划表"""
    __tablename__ = "subscription_plans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_code = Column(String(50), unique=True, nullable=False, comment="计划编码: basic/pro/enterprise")
    name = Column(String(100), nullable=False, comment="计划名称")
    description = Column(Text, comment="计划描述")

    # 价格信息
    price_monthly = Column(Numeric(10, 2), default=0, comment="月付价格")
    price_yearly = Column(Numeric(10, 2), default=0, comment="年付价格")
    currency = Column(String(10), default="CNY", comment="货币单位")

    # 配额限制
    max_stores = Column(Integer, default=1, comment="最大门店数")
    max_admins = Column(Integer, default=5, comment="最大管理员数")
    max_doctors = Column(Integer, default=50, comment="最大医生数")
    max_appointments_per_month = Column(Integer, default=1000, comment="月预约上限")
    max_storage_mb = Column(Integer, default=1024, comment="存储空间上限(MB)")
    max_lowcode_pages = Column(Integer, default=5, comment="最大低代码页面数")
    max_miniapp_instances = Column(Integer, default=3, comment="最大小程序实例数")

    # 功能开关（JSON格式）
    features = Column(Text, comment="功能开关配置(JSON)")

    # 状态
    status = Column(Integer, default=1, comment="状态: 0-禁用 1-启用")
    sort_order = Column(Integer, default=0, comment="排序")
    is_default = Column(Boolean, default=False, comment="是否为默认计划")

    # 关联租户
    tenants = relationship("Tenant", back_populates="subscription_plan")


class Tenant(Base, AuditMixin):
    """租户表"""
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_code = Column(String(50), unique=True, nullable=False, comment="租户标识（用于域名/路由）")
    name = Column(String(100), nullable=False, comment="租户名称")
    status = Column(Integer, default=1, comment="状态: 0-禁用 1-正常 2-欠费 3-试用")

    # 软删除字段
    deleted_at = Column(DateTime, nullable=True, comment="软删除时间")
    deleted_by = Column(String(36), nullable=True, comment="删除操作人ID")

    # 订阅信息
    subscription_plan_id = Column(String(36), ForeignKey("subscription_plans.id"), comment="当前订阅计划ID")
    subscription_start_at = Column(DateTime, comment="订阅开始时间")
    subscription_end_at = Column(DateTime, comment="订阅结束时间")
    billing_cycle = Column(String(20), default="monthly", comment="计费周期: monthly/yearly")

    # 配额限制（覆盖计划默认值）
    max_stores = Column(Integer, comment="最大门店数（覆盖计划）")
    max_admins = Column(Integer, comment="最大管理员数（覆盖计划）")
    max_doctors = Column(Integer, comment="最大医生数（覆盖计划）")
    max_appointments_per_month = Column(Integer, comment="月预约上限（覆盖计划）")
    max_lowcode_pages = Column(Integer, comment="最大低代码页面数（覆盖计划）")
    max_miniapp_instances = Column(Integer, comment="最大小程序实例数（覆盖计划）")

    # 功能配置（JSON格式，覆盖计划默认值）
    features = Column(Text, comment="功能开关(JSON)")

    # 品牌配置
    branding_config = Column(Text, comment="品牌配置(JSON): logo, 主题色等")

    # 密码策略
    password_policy = Column(Text, comment="密码策略(JSON)")

    # 限流配置（可选，覆盖全局默认值）
    rate_limit_per_minute = Column(Integer, nullable=True, comment="每分钟请求上限（覆盖全局 300）")
    rate_limit_per_second = Column(Integer, nullable=True, comment="每秒请求上限（覆盖全局 50）")

    # 标签/分组
    tags = Column(Text, nullable=True, comment="租户标签(JSON数组)")
    log_retention_days = Column(Integer, nullable=True, default=90, server_default="90", comment="日志保留天数(默认90)")

    # 联系信息
    contact_name = Column(String(100), comment="联系人姓名")
    contact_phone = Column(String(20), comment="联系电话")
    contact_email = Column(String(100), comment="联系邮箱")
    address = Column(String(255), comment="详细地址")

    # 域名配置
    custom_domain = Column(String(255), comment="自定义域名")
    subdomain = Column(String(100), comment="子域名前缀")

    # 关联关系
    subscription_plan = relationship("SubscriptionPlan", back_populates="tenants")
    stores = relationship("Store", back_populates="tenant")
    admins = relationship("Admin", back_populates="tenant")
    users = relationship("User", back_populates="tenant")
    patients = relationship("Patient", back_populates="tenant")
    doctors = relationship("Doctor", back_populates="tenant")
    schedules = relationship("Schedule", back_populates="tenant")
    schedule_templates = relationship("ScheduleTemplate", back_populates="tenant")
    schedule_suspensions = relationship("ScheduleSuspension", back_populates="tenant")
    appointments = relationship("Appointment", back_populates="tenant")
    roles = relationship("Role", back_populates="tenant")
    departments = relationship("Department", back_populates="tenant")
    subscriptions = relationship("TenantSubscription", back_populates="tenant", order_by="desc(TenantSubscription.created_at)")
    usage_logs = relationship("TenantUsageLog", back_populates="tenant", order_by="desc(TenantUsageLog.usage_date)")
    notifications = relationship("TenantNotification", back_populates="tenant", order_by="desc(TenantNotification.created_at)")

    def get_effective_max_stores(self) -> int:
        """获取有效的门店上限（优先使用覆盖值）"""
        if self.max_stores is not None:
            return self.max_stores
        if self.subscription_plan:
            return self.subscription_plan.max_stores
        return 1

    def get_effective_max_admins(self) -> int:
        """获取有效的管理员上限"""
        if self.max_admins is not None:
            return self.max_admins
        if self.subscription_plan:
            return self.subscription_plan.max_admins
        return 5

    def get_effective_max_doctors(self) -> int:
        """获取有效的医生上限"""
        if self.max_doctors is not None:
            return self.max_doctors
        if self.subscription_plan:
            return self.subscription_plan.max_doctors
        return 50

    def get_effective_max_appointments(self) -> int:
        """获取有效的月预约上限"""
        if self.max_appointments_per_month is not None:
            return self.max_appointments_per_month
        if self.subscription_plan:
            return self.subscription_plan.max_appointments_per_month
        return 1000

    def get_effective_max_lowcode_pages(self) -> int:
        """获取有效的低代码页面上限"""
        if self.max_lowcode_pages is not None:
            return self.max_lowcode_pages
        if self.subscription_plan:
            return self.subscription_plan.max_lowcode_pages
        return 5

    def get_effective_max_miniapp_instances(self) -> int:
        """获取有效的小程序实例上限"""
        if self.max_miniapp_instances is not None:
            return self.max_miniapp_instances
        if self.subscription_plan:
            return self.subscription_plan.max_miniapp_instances
        return 3

    @property
    def is_subscription_active(self) -> bool:
        """检查订阅是否有效"""
        if self.status == 0:  # 禁用
            return False
        if self.status == 2:  # 欠费
            return False
        if self.subscription_end_at:
            return datetime.utcnow() <= self.subscription_end_at
        return True

    def is_in_trial(self) -> bool:
        """是否处于试用期"""
        return self.status == 3


class TenantSubscription(Base, AuditMixin):
    """租户订阅记录表"""
    __tablename__ = "tenant_subscriptions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, comment="租户ID")
    plan_id = Column(String(36), ForeignKey("subscription_plans.id"), nullable=False, comment="订阅计划ID")

    # 订阅信息
    plan_code = Column(String(50), nullable=False, comment="计划编码快照")
    plan_name = Column(String(100), nullable=False, comment="计划名称快照")
    billing_cycle = Column(String(20), nullable=False, comment="计费周期: monthly/yearly")

    # 时间范围
    start_at = Column(DateTime, nullable=False, comment="开始时间")
    end_at = Column(DateTime, nullable=False, comment="结束时间")

    # 金额信息
    amount = Column(Numeric(10, 2), comment="金额")
    currency = Column(String(10), default="CNY", comment="货币单位")
    discount_rate = Column(Numeric(5, 2), default=0, comment="折扣率(%)")
    final_amount = Column(Numeric(10, 2), comment="最终金额")

    # 支付状态
    payment_status = Column(String(20), default="pending", comment="支付状态: pending/paid/refunded/cancelled")
    payment_method = Column(String(50), comment="支付方式")
    payment_transaction_id = Column(String(100), comment="支付交易ID")
    paid_at = Column(DateTime, comment="支付时间")

    # 状态
    status = Column(Integer, default=1, comment="状态: 0-已取消 1-有效 2-已过期")
    auto_renew = Column(Boolean, default=False, comment="是否自动续费")

    # 关联关系
    tenant = relationship("Tenant", back_populates="subscriptions")


class TenantUsageLog(Base):
    """租户用量统计表"""
    __tablename__ = "tenant_usage_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, comment="租户ID")
    usage_date = Column(Date, nullable=False, comment="统计日期")

    # 预约统计
    appointment_count = Column(Integer, default=0, comment="预约数")
    appointment_completed_count = Column(Integer, default=0, comment="完成预约数")
    appointment_cancelled_count = Column(Integer, default=0, comment="取消预约数")

    # 用户统计
    new_user_count = Column(Integer, default=0, comment="新用户数")
    active_user_count = Column(Integer, default=0, comment="活跃用户数")

    # 医生统计
    active_doctor_count = Column(Integer, default=0, comment="活跃医生数")

    # 存储统计
    storage_used_mb = Column(Numeric(10, 2), default=0, comment="存储用量(MB)")

    # 消息统计
    sms_sent_count = Column(Integer, default=0, comment="短信发送数")
    push_sent_count = Column(Integer, default=0, comment="推送发送数")

    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    # 关联关系
    tenant = relationship("Tenant", back_populates="usage_logs")

    # 唯一约束：每个租户每天一条记录
    __table_args__ = (
        # 注意：唯一约束需要在 Alembic 迁移中添加
        # UniqueConstraint('tenant_id', 'usage_date', name='uq_tenant_usage_date'),
        {'comment': '租户用量统计表'},
    )


class TenantNotification(Base):
    """租户通知表"""
    __tablename__ = "tenant_notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, comment="租户ID")

    # 通知类型
    notification_type = Column(String(50), nullable=False, comment="通知类型: subscription_expiry/usage_warning/overdue")
    title = Column(String(255), nullable=False, comment="通知标题")
    content = Column(Text, nullable=False, comment="通知内容")

    # 通知状态
    is_read = Column(Boolean, default=False, comment="是否已读")
    read_at = Column(DateTime, comment="阅读时间")

    # 关联数据（可选）
    related_subscription_id = Column(String(36), comment="关联的订阅ID")
    related_usage_log_id = Column(String(36), comment="关联的用量日志ID")

    # 优先级
    priority = Column(Integer, default=0, comment="优先级: 0-普通 1-重要 2-紧急")

    # 元数据（JSON格式，存储额外信息）
    extra_metadata = Column(Text, comment="元数据(JSON)")

    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    # 关联关系
    tenant = relationship("Tenant", back_populates="notifications")

    __table_args__ = (
        {'comment': '租户通知表'},
    )
