from sqlalchemy import Column, String, Integer, Text, Time, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base, AuditMixin
import uuid


class Store(Base, AuditMixin):
    """门店/分院模型"""
    __tablename__ = "stores"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 租户关联（多租户支持）
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID（NULL表示平台级门店）")
    name = Column(String(100), nullable=False, comment="门店名称")
    code = Column(String(50), index=True, comment="门店编码，租户内唯一")
    address = Column(String(255), comment="详细地址")
    province = Column(String(50), comment="省份")
    city = Column(String(50), comment="城市")
    district = Column(String(50), comment="区县")
    latitude = Column(String(20), comment="纬度")
    longitude = Column(String(20), comment="经度")
    phone = Column(String(50), comment="联系电话")
    contact_person = Column(String(50), comment="联系人")
    description = Column(Text, comment="门店简介")
    opening_time = Column(Time, comment="营业开始时间")
    closing_time = Column(Time, comment="营业结束时间")
    working_days = Column(String(50), default="1,2,3,4,5,6,7", comment="工作日(1-7)")
    business_hours = Column(String(100), comment="营业时间描述")
    image = Column(String(255), comment="门店图片")
    logo = Column(String(255), comment="门店logo")
    password = Column(String(255), comment="门店密码（bcrypt 哈希）")
    email = Column(String(100), comment="邮箱")
    theme_style = Column(String(50), comment="风格选择")
    sort_order = Column(Integer, default=0, comment="排序")
    status = Column(Integer, default=1, comment="状态: 0-停业 1-营业 2-禁用")

    # 微信小程序配置
    wechat_app_id = Column(String(100), comment="微信小程序AppID")
    wechat_app_secret = Column(String(100), comment="微信小程序Secret")
    wechat_mch_id = Column(String(100), comment="微信支付商户号")
    wechat_api_key = Column(String(100), comment="微信支付API密钥")
    wechat_notify_url = Column(String(255), comment="微信支付回调地址")

    # 就诊卡配置
    max_cards_per_user = Column(Integer, default=5, comment="每用户可建就诊卡数量上限")

    # 关联关系
    tenant = relationship("Tenant", back_populates="stores")
    # 通过 backref 在 Department, Doctor, Admin 等模型中自动创建其他关联

    # 租户内唯一约束
    __table_args__ = (
        UniqueConstraint('tenant_id', 'code', name='uq_stores_tenant_code'),
        {'comment': '门店表（多租户支持）'},
    )
