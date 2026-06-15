import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


class Doctor(Base, AuditMixin):
    __tablename__ = "doctors"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"))
    # 租户关联（多租户支持）
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    store_id = Column(String(36), ForeignKey("stores.id"), comment="所属门店ID")
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=False)

    # 基础信息
    name = Column(String(50), nullable=False, comment="医生姓名")
    username = Column(String(50), index=True, comment="医生登录账号，租户内唯一")
    phone = Column(String(20), index=True, comment="手机号，租户内唯一")
    password_hash = Column(String(255), comment="登录密码")
    gender = Column(Integer, default=0, comment="性别 0未知 1男 2女")
    avatar = Column(String(255), comment="头像URL")
    banner = Column(String(255), comment="医生banner图URL")
    title = Column(String(50), comment="职称")
    years_of_experience = Column(Integer, default=0, comment="医龄(年)")

    # 资质信息
    education = Column(String(50), comment="学历")
    graduate_school = Column(String(100), comment="毕业院校")
    license_number = Column(String(100), comment="执业证书编号")
    license_image = Column(String(255), comment="执业证书图片URL")
    honors = Column(Text, comment="所获荣誉")

    # 坐诊设置
    schedule_desc = Column(String(255), comment="坐诊时间说明")
    max_daily_appointments = Column(Integer, default=0, comment="每日最大接诊量,0表示不限制")
    online_consult_enabled = Column(Integer, default=0, comment="是否支持在线问诊 0否 1是")
    online_consult_fee = Column(Numeric(10, 2), default=0, comment="在线问诊费用")

    # 展示设置
    page_style = Column(Integer, default=1, comment="页面风格 1/2/3")
    promo_video = Column(String(255), comment="宣传视频URL")
    tags = Column(String(255), comment="标签,逗号分隔")
    specialty = Column(Text, comment="擅长")
    introduction = Column(Text, comment="简介")

    # 其他设置
    is_recommended = Column(Integer, default=0, comment="是否推荐 0否 1是")
    sort_order = Column(Integer, default=0, comment="排序")
    status = Column(Integer, default=1, comment="状态 0禁用 1正常")
    last_login_at = Column(DateTime, comment="最后登录时间")
    last_login_ip = Column(String(50), comment="最后登录IP")

    # 诊费设置
    use_fee_template = Column(Integer, default=0, comment="是否使用诊费模板 0否 1是")

    # 评价统计
    avg_rating = Column(Numeric(3, 2), default=0, comment="平均评分")
    review_count = Column(Integer, default=0, comment="评价数量")

    # 软删除
    deleted_at = Column(DateTime, nullable=True, comment="软删除时间")

    # 关联关系
    tenant = relationship("Tenant", back_populates="doctors")
    store = relationship("Store", backref="doctors")
    department = relationship("Department", back_populates="doctors")
    schedules = relationship("Schedule", back_populates="doctor")
    consultation_fees = relationship("DoctorConsultationFee", back_populates="doctor", cascade="all, delete-orphan")

    # 租户内唯一约束
    __table_args__ = (
        UniqueConstraint('tenant_id', 'username', name='uq_doctors_tenant_username'),
        UniqueConstraint('tenant_id', 'phone', name='uq_doctors_tenant_phone'),
        {'comment': '医生表（多租户支持）'},
    )
