"""租户通知服务

提供订阅到期提醒、用量警告、欠费通知等功能。
同时通过外部渠道（邮件/短信）推送高优先级告警。
"""
import json
import logging
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant, TenantNotification, TenantUsageLog
from app.models.admin import Admin

logger = logging.getLogger(__name__)


class TenantNotificationService:
    """租户通知服务

    用法:
        service = TenantNotificationService(db)
        await service.check_subscription_expiry(tenant_id)
        await service.check_usage_limits(tenant_id)
        await service.send_overdue_notification(tenant_id)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(
        self,
        tenant_id: str,
        notification_type: str,
        title: str,
        content: str,
        priority: int = 0,
        related_subscription_id: Optional[str] = None,
        related_usage_log_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TenantNotification:
        """创建通知

        Args:
            tenant_id: 租户ID
            notification_type: 通知类型（subscription_expiry/usage_warning/overdue）
            title: 通知标题
            content: 通知内容
            priority: 优先级（0-普通 1-重要 2-紧急）
            related_subscription_id: 关联的订阅ID
            related_usage_log_id: 关联的用量日志ID
            metadata: 元数据（字典格式）

        Returns:
            创建的通知对象
        """
        notification = TenantNotification(
            tenant_id=tenant_id,
            notification_type=notification_type,
            title=title,
            content=content,
            priority=priority,
            related_subscription_id=related_subscription_id,
            related_usage_log_id=related_usage_log_id,
            metadata=json.dumps(metadata) if metadata else None,
        )
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)

        # 高优先级通知推送外部渠道（邮件/短信）
        if priority >= 1:
            await self._dispatch_external(notification)

        return notification

    async def _dispatch_external(self, notification: TenantNotification) -> None:
        """通过外部渠道推送通知给租户联系人（邮件 + 短信）。

        仅对重要(priority>=1)和紧急(priority==2)通知启用外部推送。
        """
        tenant_id = notification.tenant_id
        try:
            # 获取租户联系人信息
            result = await self.db.execute(
                select(Tenant).where(Tenant.id == tenant_id)
            )
            tenant = result.scalar_one_or_none()
            if not tenant:
                return

            # 邮件推送
            if tenant.contact_email:
                await self._send_email_alert(tenant, notification)

            # 短信推送（仅紧急通知）
            if notification.priority == 2 and tenant.contact_phone:
                await self._send_sms_alert(tenant, notification)

        except Exception as e:
            logger.error(f"外部告警推送失败 tenant={tenant_id}: {e}")

    async def _send_email_alert(self, tenant: Tenant, notification: TenantNotification) -> None:
        """通过邮件发送租户告警"""
        try:
            from app.infrastructure.email.service import EmailService
            email_service = EmailService(self.db)

            variables = {
                "tenant_name": tenant.name,
                "notification_title": notification.title,
                "notification_content": notification.content,
                "priority_label": ["普通", "重要", "紧急"][notification.priority] if notification.priority <= 2 else "通知",
            }

            # 优先使用告警模板，fallback 到直接发送
            success = await email_service.send_by_template(
                template_code="tenant_alert",
                to_email=tenant.contact_email,
                variables=variables,
            )
            if not success:
                # fallback: 直接发送
                await email_service.send_direct(
                    to_email=tenant.contact_email,
                    subject=f"[{tenant.name}] {notification.title}",
                    body=notification.content,
                )
            logger.info(f"租户告警邮件已发送: tenant={tenant.id}, to={tenant.contact_email}")
        except Exception as e:
            logger.error(f"租户告警邮件发送失败: tenant={tenant.id}, error={e}")

    async def _send_sms_alert(self, tenant: Tenant, notification: TenantNotification) -> None:
        """通过短信发送租户紧急告警"""
        try:
            from app.infrastructure.sms.factory import SMSFactory
            sms_service = SMSFactory.create()
            if not sms_service:
                return

            message = f"【{tenant.name}】{notification.title}: {notification.content[:100]}"
            await sms_service.send(tenant.contact_phone, message)
            logger.info(f"租户告警短信已发送: tenant={tenant.id}, to={tenant.contact_phone}")
        except Exception as e:
            logger.error(f"租户告警短信发送失败: tenant={tenant.id}, error={e}")

    async def get_unread_notifications(
        self,
        tenant_id: str,
        limit: int = 50
    ) -> List[TenantNotification]:
        """获取未读通知

        Args:
            tenant_id: 租户ID
            limit: 返回数量限制

        Returns:
            未读通知列表
        """
        result = await self.db.execute(
            select(TenantNotification)
            .where(
                and_(
                    TenantNotification.tenant_id == tenant_id,
                    TenantNotification.is_read == False
                )
            )
            .order_by(TenantNotification.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_as_read(self, notification_id: str) -> Optional[TenantNotification]:
        """标记通知为已读

        Args:
            notification_id: 通知ID

        Returns:
            更新后的通知对象
        """
        result = await self.db.execute(
            select(TenantNotification).where(TenantNotification.id == notification_id)
        )
        notification = result.scalar_one_or_none()
        if notification:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(notification)
        return notification

    async def mark_all_as_read(self, tenant_id: str) -> int:
        """标记所有通知为已读

        Args:
            tenant_id: 租户ID

        Returns:
            更新的通知数量
        """
        result = await self.db.execute(
            select(TenantNotification).where(
                and_(
                    TenantNotification.tenant_id == tenant_id,
                    TenantNotification.is_read == False
                )
            )
        )
        notifications = result.scalars().all()

        count = 0
        for notification in notifications:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            count += 1

        await self.db.commit()
        return count

    async def check_subscription_expiry(self, tenant_id: str) -> Optional[TenantNotification]:
        """检查订阅到期并发送提醒

        检查规则：
        - 距离到期7天：普通提醒
        - 距离到期3天：重要提醒
        - 距离到期1天：紧急提醒
        - 已到期：紧急提醒

        Args:
            tenant_id: 租户ID

        Returns:
            如果发送了通知则返回通知对象，否则返回 None
        """
        # 获取租户
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant or not tenant.subscription_end_at:
            return None

        now = datetime.utcnow()
        days_until_expiry = (tenant.subscription_end_at - now).days

        # 检查是否需要发送通知
        notification_data = None
        if days_until_expiry == 7:
            notification_data = {
                "title": "订阅即将到期提醒",
                "content": f"您的订阅将于 {days_until_expiry} 天后到期（{tenant.subscription_end_at.strftime('%Y-%m-%d')}），请及时续费以免影响使用。",
                "priority": 0,
            }
        elif days_until_expiry == 3:
            notification_data = {
                "title": "订阅到期重要提醒",
                "content": f"您的订阅将于 {days_until_expiry} 天后到期（{tenant.subscription_end_at.strftime('%Y-%m-%d')}），请尽快续费。",
                "priority": 1,
            }
        elif days_until_expiry == 1:
            notification_data = {
                "title": "订阅即将到期紧急提醒",
                "content": f"您的订阅将于明天到期（{tenant.subscription_end_at.strftime('%Y-%m-%d')}），请立即续费以免服务中断。",
                "priority": 2,
            }
        elif days_until_expiry < 0:
            # 已到期
            days_overdue = abs(days_until_expiry)
            notification_data = {
                "title": "订阅已到期",
                "content": f"您的订阅已于 {days_overdue} 天前到期（{tenant.subscription_end_at.strftime('%Y-%m-%d')}），请立即续费以恢复服务。",
                "priority": 2,
            }

        if not notification_data:
            return None

        # 检查今天是否已发送过相同类型的通知
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        existing_result = await self.db.execute(
            select(TenantNotification).where(
                and_(
                    TenantNotification.tenant_id == tenant_id,
                    TenantNotification.notification_type == "subscription_expiry",
                    TenantNotification.created_at >= today_start
                )
            )
        )
        if existing_result.scalar_one_or_none():
            return None  # 今天已发送过

        # 创建通知
        return await self.create_notification(
            tenant_id=tenant_id,
            notification_type="subscription_expiry",
            **notification_data,
            metadata={"days_until_expiry": days_until_expiry}
        )

    async def check_usage_limits(self, tenant_id: str) -> List[TenantNotification]:
        """检查用量限制并发送警告

        检查规则：
        - 用量达到80%：普通警告
        - 用量达到90%：重要警告
        - 用量达到100%：紧急警告

        Args:
            tenant_id: 租户ID

        Returns:
            发送的通知列表
        """
        # 获取租户配额
        from app.common.quota import QuotaChecker

        checker = QuotaChecker(self.db)
        usage = await checker.get_quota_usage(tenant_id)

        notifications = []
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # 检查各项配额
        for resource_type, data in usage.items():
            usage_percent = data["usage_percent"]
            current = data["current"]
            limit = data["limit"]

            notification_data = None
            if usage_percent >= 100:
                resource_name = self._get_resource_name(resource_type)
                notification_data = {
                    "title": f"{resource_name}配额已用尽",
                    "content": f"您的{resource_name}数量已达上限（{current}/{limit}），请升级订阅计划以获得更多配额。",
                    "priority": 2,
                }
            elif usage_percent >= 90:
                resource_name = self._get_resource_name(resource_type)
                notification_data = {
                    "title": f"{resource_name}配额即将用尽",
                    "content": f"您的{resource_name}使用量已达{usage_percent}%（{current}/{limit}），请及时升级订阅计划。",
                    "priority": 1,
                }
            elif usage_percent >= 80:
                resource_name = self._get_resource_name(resource_type)
                notification_data = {
                    "title": f"{resource_name}用量警告",
                    "content": f"您的{resource_name}使用量已达{usage_percent}%（{current}/{limit}），请注意控制使用或升级订阅计划。",
                    "priority": 0,
                }

            if notification_data:
                # 检查今天是否已发送过相同资源类型的警告
                existing_result = await self.db.execute(
                    select(TenantNotification).where(
                        and_(
                            TenantNotification.tenant_id == tenant_id,
                            TenantNotification.notification_type == "usage_warning",
                            TenantNotification.created_at >= today_start
                        )
                    )
                )
                existing = existing_result.scalars().all()
                # 检查是否已有相同资源类型的通知
                for exist in existing:
                    exist_metadata = json.loads(exist.metadata) if exist.metadata else {}
                    if exist_metadata.get("resource_type") == resource_type:
                        continue  # 已发送过

                # 创建通知
                notification = await self.create_notification(
                    tenant_id=tenant_id,
                    notification_type="usage_warning",
                    **notification_data,
                    metadata={"resource_type": resource_type, "usage_percent": usage_percent}
                )
                notifications.append(notification)

        return notifications

    async def send_overdue_notification(self, tenant_id: str) -> Optional[TenantNotification]:
        """发送欠费通知

        Args:
            tenant_id: 租户ID

        Returns:
            创建的通知对象
        """
        # 获取租户
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            return None

        if tenant.status != 2:  # 不是欠费状态
            return None

        # 检查今天是否已发送过欠费通知
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        existing_result = await self.db.execute(
            select(TenantNotification).where(
                and_(
                    TenantNotification.tenant_id == tenant_id,
                    TenantNotification.notification_type == "overdue",
                    TenantNotification.created_at >= today_start
                )
            )
        )
        if existing_result.scalar_one_or_none():
            return None  # 今天已发送过

        # 创建欠费通知
        return await self.create_notification(
            tenant_id=tenant_id,
            notification_type="overdue",
            title="账户欠费提醒",
            content="您的账户已欠费，请及时充值以免影响服务使用。如已充值请忽略此提醒。",
            priority=2,
        )

    def _get_resource_name(self, resource_type: str) -> str:
        """获取资源类型的中文名称"""
        name_map = {
            "stores": "门店",
            "admins": "管理员",
            "doctors": "医生",
            "appointments_per_month": "月预约数",
        }
        return name_map.get(resource_type, resource_type)
