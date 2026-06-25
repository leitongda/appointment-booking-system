"""通知相关常量 — 渠道映射、类型映射、默认策略、去重 TTL。

单一来源，供 dispatcher / unified_message / notification_preferences 共用。
"""

# 渠道 → 用户偏好表字段名映射
CHANNEL_FIELD_MAP = {
    "in_app": "in_app_enabled",
    "sms": "sms_enabled",
    "wechat": "wechat_enabled",
    "email": "email_enabled",
    "websocket": "in_app_enabled",  # WebSocket 复用站内信偏好
    # 第三方集成平台
    "dingtalk": "dingtalk_enabled",
    "wecom": "wecom_enabled",
    "feishu": "feishu_enabled",
}

# 消息类型 → 用户偏好表字段名映射
TYPE_FIELD_MAP = {
    "appointment": "appointment_enabled",
    "appointment_success": "appointment_enabled",
    "appointment_reminder": "reminder_enabled",
    "appointment_cancelled": "appointment_enabled",
    "schedule": "reminder_enabled",
    "stop_clinic": "stop_clinic_enabled",
    "system": "system_enabled",
    "consultation": "consultation_enabled",
    "feedback": "feedback_enabled",
    "queue_call": "appointment_enabled",
}

# 默认渠道策略（按消息类型，按降级优先级排序）
DEFAULT_CHANNEL_STRATEGY = {
    "appointment": ["wechat", "sms", "in_app"],
    "appointment_success": ["wechat", "sms", "in_app"],
    "appointment_reminder": ["wechat", "sms", "in_app"],
    "appointment_cancelled": ["wechat", "sms", "in_app"],
    "schedule": ["websocket", "in_app"],
    "stop_clinic": ["wechat", "sms", "in_app"],
    "system": ["email", "in_app"],
    "consultation": ["in_app"],
    "feedback": ["in_app"],
    "queue_call": ["websocket", "in_app"],
}

# 去重缓存过期时间（秒）
DEDUP_TTL = 86400  # 24 小时
