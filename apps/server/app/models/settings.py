"""系统设置模型"""
from sqlalchemy import Column, String, Integer, Text, DateTime
from app.db.base import Base, TimestampMixin
from datetime import datetime
import uuid


class SystemSetting(Base, TimestampMixin):
    """系统设置表（键值对存储）"""
    __tablename__ = "system_settings"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    category = Column(String(50), nullable=False, comment="分类: booking, hospital, wechat, sms")
    key = Column(String(100), nullable=False, comment="设置项键名")
    value = Column(Text, comment="设置项值")
    description = Column(String(200), comment="描述")
    
    # 联合唯一索引
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )


# 预定义的设置项
DEFAULT_SETTINGS = {
    # 预约设置
    'booking': {
        'advance_days': {'value': '14', 'description': '可提前预约天数'},
        'same_day_booking': {'value': 'true', 'description': '允许当天预约'},
        'cancel_hours': {'value': '2', 'description': '就诊前不可取消时间(小时)'},
        'per_day_limit': {'value': '3', 'description': '每人每天预约限制'},
        'per_doctor_limit': {'value': '1', 'description': '每人每医生预约限制'},
        'no_show_limit': {'value': '3', 'description': '爽约次数限制'},
        'blacklist_days': {'value': '30', 'description': '黑名单禁止天数'},
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
}


