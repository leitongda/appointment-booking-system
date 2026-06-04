"""
通知配额默认配置

用于初始化 system_settings 中的通知配额配置项。
"""
import logging

logger = logging.getLogger(__name__)

# 通知配额默认配置
NOTIFICATION_QUOTA_DEFAULTS = {
    "sms_monthly_limit": {
        "value": "1000",
        "description": "短信月度发送配额",
    },
    "email_monthly_limit": {
        "value": "5000",
        "description": "邮件月度发送配额",
    },
    "wechat_monthly_limit": {
        "value": "10000",
        "description": "微信月度发送配额",
    },
    "in_app_monthly_limit": {
        "value": "-1",
        "description": "站内信月度发送配额（-1 表示不限制）",
    },
}


async def ensure_notification_quota_settings(db):
    """确保通知配额配置项存在

    Args:
        db: 异步数据库会话
    """
    from app.models.settings import SystemSetting
    from sqlalchemy import select

    for key, config in NOTIFICATION_QUOTA_DEFAULTS.items():
        # 检查是否已存在
        result = await db.execute(
            select(SystemSetting).where(
                SystemSetting.category == "notification_quota",
                SystemSetting.key == key,
            )
        )
        existing = result.scalar_one_or_none()

        if not existing:
            setting = SystemSetting(
                category="notification_quota",
                key=key,
                value=config["value"],
                description=config["description"],
            )
            db.add(setting)
            await db.flush()
            logger.info("创建通知配额配置: %s = %s", key, config["value"])
        else:
            logger.debug("通知配额配置已存在: %s", key)

    await db.commit()
    logger.info("通知配额配置初始化完成")


if __name__ == "__main__":
    """独立运行脚本初始化配置"""
    import asyncio
    from app.db.session import get_async_db_context

    async def init():
        async for db in get_async_db_context():
            await ensure_notification_quota_settings(db)

    asyncio.run(init())