"""支付相关枚举"""
from enum import Enum


class PaymentStatus(str, Enum):
    """支付状态"""
    PENDING = "pending"        # 待支付
    PROCESSING = "processing"  # 支付中
    PAID = "paid"              # 已支付
    FAILED = "failed"          # 支付失败
    REFUNDED = "refunded"      # 已退款


class RefundStatus(str, Enum):
    """退款状态"""
    PENDING = "pending"        # 待退款
    PROCESSING = "processing"  # 退款中
    SUCCESS = "success"        # 退款成功
    FAILED = "failed"          # 退款失败
