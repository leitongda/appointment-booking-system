"""安全策略配置辅助函数

从 SystemSetting 读取安全相关配置，fallback 到 config.py 默认值。
供 auth/admin/doctor 等路由在签发 token 时使用。

注意：此模块通过接口注入解耦对 app.modules.settings.service 的依赖。
调用方负责创建 SettingsService 并传入。
"""
from datetime import timedelta
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.settings import DEFAULT_SETTINGS


class SecurityConfigProvider(Protocol):
    """安全配置提供者接口"""
    async def get_by_category(self, category: str) -> dict: ...
    async def get_value(self, category: str, key: str, default=None): ...


async def get_token_expire_config(
    db: AsyncSession,
    config_provider: SecurityConfigProvider,
) -> tuple[timedelta, timedelta, int]:
    """读取 token 过期配置。

    Args:
        db: 数据库会话（保留用于签名兼容，实际使用 config_provider）
        config_provider: 安全配置提供者（如 SettingsService 实例）

    Returns:
        (access_token_delta, refresh_token_delta, access_expire_seconds)
    """
    sec = await config_provider.get_by_category("security")

    access_minutes = int(sec.get("access_token_expire_minutes",
                                 DEFAULT_SETTINGS["security"]["access_token_expire_minutes"]["value"]))
    refresh_days = int(sec.get("refresh_token_expire_days",
                               DEFAULT_SETTINGS["security"]["refresh_token_expire_days"]["value"]))

    return (
        timedelta(minutes=access_minutes),
        timedelta(days=refresh_days),
        access_minutes * 60,
    )


async def get_default_password(
    db: AsyncSession,
    config_provider: SecurityConfigProvider,
) -> str:
    """读取新用户默认密码。

    Args:
        db: 数据库会话（保留用于签名兼容）
        config_provider: 安全配置提供者

    Returns:
        默认密码字符串
    """
    return await config_provider.get_value("security", "default_password",
                                           default=settings.DEFAULT_USER_PASSWORD)
