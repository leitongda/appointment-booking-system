"""安全配置便捷函数

包装 app.infrastructure.security_settings，注入 SettingsService 依赖。
供 modules 层调用方使用，避免每个调用点都手动注入。
"""
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.security_settings import (
    get_default_password as _get_default_password,
    get_token_expire_config as _get_token_expire_config,
)
from app.modules.settings.service import SettingsService


async def get_token_expire_config(db: AsyncSession) -> tuple[timedelta, timedelta, int]:
    """读取 token 过期配置（自动注入 SettingsService）"""
    return await _get_token_expire_config(db, SettingsService(db))


async def get_default_password(db: AsyncSession) -> str:
    """读取新用户默认密码（自动注入 SettingsService）"""
    return await _get_default_password(db, SettingsService(db))
