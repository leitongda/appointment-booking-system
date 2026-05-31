"""预约相关枚举"""
from enum import Enum


class CheckinMethod(str, Enum):
    """签到方式

    来源: modules/appointments/common.py CHECKIN_METHOD dict
    """
    MANUAL = "MANUAL"      # 手动签到（默认）
    QR_CODE = "QR_CODE"    # 扫码签到
    PHONE = "PHONE"        # 手机签到（患者端自助）
