"""支付订单号生成 — 纯函数模块。

把原本耦合在 PaymentService 内的商户订单号生成逻辑提取为模块级纯函数，
使退款模块（refunds）无需 import PaymentService 即可复用同一规则，
从而消除 payments <-> refunds 之间的循环依赖。
"""

from __future__ import annotations

from app.models.appointment import Appointment


def generate_out_trade_no(appointment: Appointment) -> str:
    """生成商户订单号。

    微信支付 V3 要求 out_trade_no 长度 6-32 字符。
    appointment_no 形如 YY+yyyymmddHHMMSS+4 字符随机串=22 字符，符合要求且租户内唯一。
    历史数据若曾使用 APPT+UUID(40字符)会被微信拒单，回调反查保留兼容。
    """
    if not appointment.appointment_no:
        raise ValueError(f"预约缺少 appointment_no，无法生成商户订单号: {appointment.id}")
    return appointment.appointment_no
