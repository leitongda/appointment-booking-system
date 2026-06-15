"""安全策略配置辅助函数

从 SystemSetting 读取安全相关配置，fallback 到 config.py 默认值。
供 auth/admin/doctor 等路由在签发 token 时使用。
"""
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.settings import DEFAULT_SETTINGS


async def get_token_expire_config(db: AsyncSession) -> tuple[timedelta, timedelta, int]:
    """读取 token 过期配置。

    Returns:
        (access_token_delta, refresh_token_delta, access_expire_seconds)
    """
    from app.modules.settings.service import SettingsService

    service = SettingsService(db)
    sec = await service.get_by_category("security")

    access_minutes = int(sec.get("access_token_expire_minutes",
                                 DEFAULT_SETTINGS["security"]["access_token_expire_minutes"]["value"]))
    refresh_days = int(sec.get("refresh_token_expire_days",
                               DEFAULT_SETTINGS["security"]["refresh_token_expire_days"]["value"]))

    return (
        timedelta(minutes=access_minutes),
        timedelta(days=refresh_days),
        access_minutes * 60,
    )


async def get_default_password(db: AsyncSession) -> str:
    """读取新用户默认密码。"""
    from app.modules.settings.service import SettingsService

    service = SettingsService(db)
    return await service.get_value("security", "default_password",
                                   default=settings.DEFAULT_USER_PASSWORD)
