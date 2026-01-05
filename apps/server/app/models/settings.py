"""系统设置模型"""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.base import Base, AuditMixin
from datetime import datetime
import uuid


class SystemSetting(Base, AuditMixin):
    """系统设置表（键值对存储）
    
    支持门店级别配置：
    - store_id 为空：全局默认配置
    - store_id 有值：门店特定配置（优先级高于全局配置）
    """
    __tablename__ = "system_settings"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id = Column(String(36), ForeignKey("stores.id", ondelete="CASCADE"), nullable=True, comment="门店ID，为空表示全局配置")
    category = Column(String(50), nullable=False, comment="分类: booking, hospital, wechat, sms, time_periods")
    key = Column(String(100), nullable=False, comment="设置项键名")
    value = Column(Text, comment="设置项值")
    description = Column(String(200), comment="描述")
    
    # 关联门店
    store = relationship("Store", backref="settings")
    
    # 索引：加速按门店和分类查询
    __table_args__ = (
        Index('ix_system_settings_store_category', 'store_id', 'category'),
        Index('ix_system_settings_store_category_key', 'store_id', 'category', 'key'),
        {'sqlite_autoincrement': True},
    )


# 预定义的设置项
DEFAULT_SETTINGS = {
    # 预约设置
    'booking': {
        'advance_days': {'value': '10', 'description': '可提前预约天数'},
        'same_day_booking': {'value': 'true', 'description': '允许当天预约'},
        'cancel_hours': {'value': '2', 'description': '就诊前不可取消时间(小时)'},
        'per_day_limit': {'value': '3', 'description': '每人每天预约限制'},
        'per_doctor_limit': {'value': '1', 'description': '每人每医生预约限制'},
        'no_show_limit': {'value': '3', 'description': '爽约次数限制'},
        'blacklist_days': {'value': '30', 'description': '黑名单禁止天数'},
        # 提前预约截止配置
        'advance_booking_minutes': {'value': '0', 'description': '提前预约截止时间(分钟)，0表示不限制'},
        'advance_booking_direction': {'value': 'before', 'description': '时间方向: before(往前), after(往后)'},
        'advance_booking_reference': {'value': 'end', 'description': '基准时间: start(开始时间), end(结束时间)'},
        # 签到时间配置
        'sign_in_advance_minutes': {'value': '30', 'description': '提前签到时间(分钟)，班次开始前多少分钟可以签到'},
        'sign_in_late_minutes': {'value': '30', 'description': '迟到签到时间(分钟)，班次开始后多少分钟还可以签到'},
    },
    # 医院信息
    'hospital': {
        'name': {'value': '', 'description': '医院名称'},
        'level': {'value': '', 'description': '医院等级'},
        'address': {'value': '', 'description': '医院地址'},
        'phone': {'value': '', 'description': '联系电话'},
        'work_time': {'value': '', 'description': '工作时间'},
        'introduction': {'value': '', 'description': '医院简介'},
        'logo': {'value': '', 'description': '医院Logo'},
    },
    # 微信配置
    'wechat': {
        'app_id': {'value': '', 'description': '小程序AppID'},
        'app_secret': {'value': '', 'description': '小程序Secret'},
        'mch_id': {'value': '', 'description': '商户号'},
        'api_key': {'value': '', 'description': 'API密钥'},
        'notify_url': {'value': '', 'description': '支付回调地址'},
    },
    # 短信配置
    'sms': {
        'provider': {'value': 'aliyun', 'description': '短信服务商'},
        'access_key_id': {'value': '', 'description': 'AccessKey ID'},
        'access_key_secret': {'value': '', 'description': 'AccessKey Secret'},
        'sign_name': {'value': '', 'description': '短信签名'},
        'template_code': {'value': '', 'description': '模板编码'},
        'template_code_booking': {'value': '', 'description': '预约成功模板'},
        'template_code_remind': {'value': '', 'description': '就诊提醒模板'},
        'template_code_cancel': {'value': '', 'description': '取消预约模板'},
    },
    # 预约选项配置（控制就诊人表单字段的启用/禁用、必填/非必填）
    'booking_fields': {
        'name': {'value': '{"enabled": true, "required": true}', 'description': '姓名'},
        'phone': {'value': '{"enabled": true, "required": true}', 'description': '联系电话'},
        'gender': {'value': '{"enabled": true, "required": true}', 'description': '性别'},
        'province_city_district': {'value': '{"enabled": false, "required": false}', 'description': '省/市/区'},
        'street': {'value': '{"enabled": false, "required": false}', 'description': '街道/社区'},
        'card_no': {'value': '{"enabled": false, "required": false}', 'description': '就诊卡编号'},
        'id_card_type': {'value': '{"enabled": false, "required": false}', 'description': '证件类型'},
        'id_card': {'value': '{"enabled": false, "required": false}', 'description': '证件号'},
        'ethnicity': {'value': '{"enabled": false, "required": false}', 'description': '民族'},
        'birthday': {'value': '{"enabled": false, "required": false}', 'description': '出生日期'},
        'age': {'value': '{"enabled": true, "required": true}', 'description': '年龄'},
        'relationship': {'value': '{"enabled": false, "required": false}', 'description': '关系'},
        'address': {'value': '{"enabled": false, "required": false}', 'description': '详细地址'},
    },
    # 就诊卡配置
    'patient_card': {
        'card_name': {'value': '就诊卡', 'description': '就诊卡名称'},
        'card_description': {'value': '', 'description': '就诊卡描述文字（限16字以内）'},
        'max_cards_per_user': {'value': '5', 'description': '每用户可建卡数量'},
        'show_on_homepage': {'value': 'false', 'description': '首页是否展示'},
    },
    # 图片处理配置
    'image': {
        'thumbnail_sizes': {
            'value': '[{"name": "small", "width": 200, "height": 200}, {"name": "medium", "width": 800, "height": 800}]',
            'description': '缩略图尺寸配置（JSON数组）'
        },
        'compress_quality': {'value': '85', 'description': '压缩质量（1-100）'},
    },
    # 时段划分配置（支持门店级别覆盖）
    'time_periods': {
        'periods': {
            'value': '[{"key":"morning","name":"上午","startTime":"06:00","endTime":"12:00"},{"key":"afternoon","name":"下午","startTime":"12:00","endTime":"18:00"}]',
            'description': '时段划分配置，用于排班预览和预约显示'
        },
    },
}


