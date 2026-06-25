"""
通知配额管理服务

提供租户级通知配额检查、用量统计和配额告警功能。
"""
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import SystemSetting
from app.models.tenant import Tenant
from app.modules.notification_logs.service import NotificationLogService

logger = logging.getLogger(__name__)


class NotificationQuotaService:
    """通知配额管理服务

    功能:
    - 检查租户通知配额是否充足
    - 获取剩余配额
    - 递增已用量
    - 配额告警检查
    """

    # 默认配额配置
    DEFAULT_QUOTAS = {
        "sms_monthly_limit": 1000,
        "email_monthly_limit": 5000,
        "wechat_monthly_limit": 10000,
        "in_app_monthly_limit": None,  # 站内信通常不限
    }

    # Redis 缓存键前缀
    CACHE_PREFIX = "notification:quota"

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_quota_config(
        self, tenant_id: str, channel: str
    ) -> int | None:
        """获取租户指定渠道的配额配置

        优先级:
        1. 租户自定义配额 (system_settings)
        2. 订阅计划配额 (SubscriptionPlan)
        3. 默认配额

        Args:
            tenant_id: 租户ID
            channel: 通知渠道 (sms/email/wechat/in_app)

        Returns:
            配额数量，None 表示不限制
        """
        # 构建配置键名
        quota_key = f"{channel}_monthly_limit"

        # 1. 尝试从 system_settings 读取租户自定义配额
        #    SystemSetting 以 store_id 为隔离维度，通过 stores 表关联 tenant_id
        try:
            from app.models.store import Store

            # 先查该租户下的门店列表
            store_result = await self.db.execute(
                select(Store.id).where(Store.tenant_id == tenant_id)
            )
            store_ids = [row[0] for row in store_result.all()]

            if store_ids:
                result = await self.db.execute(
                    select(SystemSetting).where(
                        and_(
                            SystemSetting.store_id.in_(store_ids),
                            SystemSetting.category == "notification_quota",
                            SystemSetting.key == quota_key,
                        )
                    ).order_by(SystemSetting.store_id.desc()).limit(1)
                )
                setting = result.scalar_one_or_none()
                if setting and setting.value:
                    return int(setting.value)

            # 兜底：查全局配置（store_id 为 NULL）
            result = await self.db.execute(
                select(SystemSetting).where(
                    and_(
                        SystemSetting.store_id.is_(None),
                        SystemSetting.category == "notification_quota",
                        SystemSetting.key == quota_key,
                    )
                )
            )
            setting = result.scalar_one_or_none()
            if setting and setting.value:
                return int(setting.value)
        except Exception as e:
            logger.warning(f"从 system_settings 读取配额失败: {e}")

        # 2. 从租户的订阅计划读取
        try:
            result = await self.db.execute(
                select(Tenant).where(Tenant.id == tenant_id)
            )
            tenant = result.scalar_one_or_none()
            if tenant and tenant.subscription_plan_id:
                # 从 SubscriptionPlan 读取
                # 注意：这里需要 SubscriptionPlan 有相应的配额字段
                # 目前先使用默认值
                pass
        except Exception as e:
            logger.warning(f"从订阅计划读取配额失败: {e}")

        # 3. 使用默认配额
        return self.DEFAULT_QUOTAS.get(quota_key)

    async def get_current_month_usage(
        self, tenant_id: str, channel: str
    ) -> int:
        """获取租户当前月某渠道的使用量

        Args:
            tenant_id: 租户ID
            channel: 通知渠道

        Returns:
            已发送成功的数量
        """
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        service = NotificationLogService(self.db)
        return await service.get_channel_usage_in_period(
            tenant_id=tenant_id,
            channel=channel,
            start_date=month_start,
            end_date=now,
        )

    async def check_quota(
        self, tenant_id: str, channel: str
    ) -> tuple[bool, int]:
        """检查租户在指定渠道的配额是否充足

        Args:
            tenant_id: 租户ID
            channel: 通知渠道

        Returns:
            (是否允许发送, 剩余配额)
        """
        quota = await self.get_quota_config(tenant_id, channel)

        # 如果配额为 None，表示不限制
        if quota is None:
            return True, -1

        usage = await self.get_current_month_usage(tenant_id, channel)
        remaining = quota - usage

        return remaining > 0, max(0, remaining)

    async def get_remaining_quota(
        self, tenant_id: str, channel: str
    ) -> int:
        """获取剩余配额

        Args:
            tenant_id: 租户ID
            channel: 通知渠道

        Returns:
            剩余配额，-1 表示不限制
        """
        quota = await self.get_quota_config(tenant_id, channel)
        if quota is None:
            return -1

        usage = await self.get_current_month_usage(tenant_id, channel)
        return max(0, quota - usage)

    async def increment_usage(
        self, tenant_id: str, channel: str
    ) -> None:
        """递增已用量（发送成功后调用）

        使用 Redis 缓存计数，避免频繁查询数据库

        Args:
            tenant_id: 租户ID
            channel: 通知渠道
        """
        from app.core.redis import RedisCache

        now = datetime.utcnow()
        cache_key = f"{self.CACHE_PREFIX}:{tenant_id}:{channel}:{now.year}-{now.month}"

        # Redis 计数，过期时间设为月度结束
        month_end = (now.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(seconds=1)
        ttl = int((month_end - now).total_seconds())

        val = await RedisCache.incr(cache_key, 1)
        if val == 1:
            await RedisCache.expire(cache_key, ttl)

    async def get_quota_info(self, tenant_id: str) -> dict[str, Any]:
        """获取租户完整的配额信息

        Args:
            tenant_id: 租户ID

        Returns:
            配额信息字典
        """
        channels = ["sms", "email", "wechat", "in_app"]

        quotas = {}
        usage = {}
        remaining = {}
        usage_percent = {}

        for channel in channels:
            quota = await self.get_quota_config(tenant_id, channel)
            used = await self.get_current_month_usage(tenant_id, channel)

            quotas[channel] = quota
            usage[channel] = used

            if quota is None:
                remaining[channel] = -1
                usage_percent[channel] = 0
            elif quota == 0:
                remaining[channel] = 0
                usage_percent[channel] = 100
            else:
                remaining[channel] = max(0, quota - used)
                usage_percent[channel] = round((used / quota) * 100, 2)

        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(seconds=1)

        return {
            "tenant_id": tenant_id,
            "quotas": quotas,
            "usage": usage,
            "remaining": remaining,
            "usage_percent": usage_percent,
            "period_start": month_start.isoformat(),
            "period_end": month_end.isoformat(),
        }

    async def check_and_alert(self, tenant_id: str) -> list:
        """检查用量，达 80% 或 100% 时发送告警

        Args:
            tenant_id: 租户ID

        Returns:
            需要发送的告警列表
        """
        from app.infrastructure.notifications.service import TenantNotificationService

        quota_info = await self.get_quota_info(tenant_id)
        notifications = []
        notification_service = TenantNotificationService(self.db)

        channels = ["sms", "email", "wechat"]  # in_app 不需要告警

        for channel in channels:
            quota = quota_info["quotas"][channel]
            if quota is None or quota == 0:
                continue

            usage_percent = quota_info["usage_percent"][channel]
            used = quota_info["usage"][channel]

            # 检查是否需要发送告警
            alert = None
            if usage_percent >= 100:
                channel_name = self._get_channel_name(channel)
                alert = {
                    "notification_type": "notification_quota_exceeded",
                    "title": f"{channel_name}配额已用尽",
                    "content": f"您的{channel_name}月度配额已用尽（{used}/{quota}），请升级订阅计划以获得更多配额。",
                    "priority": 2,
                    "metadata": {"channel": channel, "usage_percent": usage_percent, "quota": quota, "used": used},
                }
            elif usage_percent >= 90:
                channel_name = self._get_channel_name(channel)
                alert = {
                    "notification_type": "notification_quota_warning",
                    "title": f"{channel_name}配额即将用尽",
                    "content": f"您的{channel_name}使用量已达{usage_percent}%（{used}/{quota}），请及时升级订阅计划。",
                    "priority": 1,
                    "metadata": {"channel": channel, "usage_percent": usage_percent, "quota": quota, "used": used},
                }
            elif usage_percent >= 80:
                channel_name = self._get_channel_name(channel)
                alert = {
                    "notification_type": "notification_quota_warning",
                    "title": f"{channel_name}用量警告",
                    "content": f"您的{channel_name}使用量已达{usage_percent}%（{used}/{quota}），请注意控制使用或升级订阅计划。",
                    "priority": 0,
                    "metadata": {"channel": channel, "usage_percent": usage_percent, "quota": quota, "used": used},
                }

            if alert:
                # 检查今天是否已发送过该渠道的告警
                now = datetime.utcnow()
                today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

                from app.models.tenant import TenantNotification
                existing_result = await self.db.execute(
                    select(TenantNotification).where(
                        and_(
                            TenantNotification.tenant_id == tenant_id,
                            TenantNotification.notification_type == alert["notification_type"],
                            TenantNotification.created_at >= today_start,
                        )
                    )
                )
                existing = existing_result.scalars().all()

                # 检查是否已有相同渠道的告警
                already_sent = False
                for exist in existing:
                    import json
                    exist_metadata = json.loads(exist.metadata) if exist.metadata else {}
                    if exist_metadata.get("channel") == channel:
                        already_sent = True
                        break

                if not already_sent:
                    notification = await notification_service.create_notification(
                        tenant_id=tenant_id,
                        **alert,
                    )
                    notifications.append(notification)

        return notifications

    def _get_channel_name(self, channel: str) -> str:
        """获取渠道中文名称"""
        name_map = {
            "sms": "短信",
            "email": "邮件",
            "wechat": "微信",
            "in_app": "站内信",
        }
        return name_map.get(channel, channel)