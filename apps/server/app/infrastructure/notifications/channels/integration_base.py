"""第三方集成通知渠道公共基类。

钉钉/企业微信/飞书 三个渠道的逻辑高度相似：
1. 解析收件人外部 ID（event.recipient_*_id 或查 IntegrationBinding）
2. 加载租户 Integration 配置
3. 优先走企业应用点对点消息；未配置则降级群机器人
4. 写 NotificationLog

本基类收敛通用流程，子类只需声明 provider_name 与少量差异。
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.secret_refs import resolve_secret_ref
from app.infrastructure.integrations import get_provider
from app.infrastructure.notifications.channels.base import BaseNotificationChannel
from app.models.integration import Integration, IntegrationBinding
from app.models.notification_log import NotificationLog
from app.schemas.notification import NotificationContent, NotificationEvent

logger = logging.getLogger(__name__)


class BaseIntegrationChannel(BaseNotificationChannel):
    """第三方集成通知渠道基类。

    子类必须设置 ``provider_name``（dingtalk/wecom/feishu）。
    """

    provider_name: str = ""

    @property
    def channel_name(self) -> str:
        return self.provider_name

    # ============================================================
    # 收件人解析
    # ============================================================

    async def _resolve_external_id(self, event: NotificationEvent) -> str | None:
        """解析收件人在该平台的用户 ID。

        优先级：
        1. event 上的 recipient_{provider}_id 字段（显式传入）
        2. event.extra_data 里的 recipient_{provider}_id
        3. 查 IntegrationBinding 表（tenant_id + user_id + provider）
        """
        # 1. event schema 级别字段
        schema_field = f"recipient_{self.provider_name}_id"
        direct = getattr(event, schema_field, None)
        if direct:
            return direct

        # 2. extra_data 携带
        if event.extra_data:
            direct = event.extra_data.get(schema_field)
            if direct:
                return direct

        # 3. 查绑定表
        stmt = select(IntegrationBinding.external_id).where(
            IntegrationBinding.tenant_id == event.tenant_id,
            IntegrationBinding.user_id == event.recipient_id,
            IntegrationBinding.provider == self.provider_name,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _load_integration(self, event: NotificationEvent) -> Integration | None:
        """加载租户在该平台的集成配置（仅启用状态）。"""
        stmt = select(Integration).where(
            Integration.tenant_id == event.tenant_id,
            Integration.provider == self.provider_name,
            Integration.status == 1,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def validate_recipient(self, event: NotificationEvent) -> tuple[bool, str | None]:
        external_id = await self._resolve_external_id(event)
        if not external_id:
            return False, f"用户未绑定{self.channel_name}账号"
        # 缓存到 extra_data 供 send 复用，避免二次查询
        if event.extra_data is None:
            event.extra_data = {}
        event.extra_data[f"_external_id_{self.provider_name}"] = external_id
        return True, None

    # ============================================================
    # 发送
    # ============================================================

    async def send(self, event: NotificationEvent, content: NotificationContent) -> bool:
        try:
            external_id = (event.extra_data or {}).get(f"_external_id_{self.provider_name}")
            if not external_id:
                external_id = await self._resolve_external_id(event)
            if not external_id:
                logger.warning("[%s] 无法解析收件人外部ID: user=%s", self.channel_name, event.recipient_id)
                return False

            integration = await self._load_integration(event)
            if not integration:
                logger.warning("[%s] 租户未配置集成: tenant=%s", self.channel_name, event.tenant_id)
                return False

            provider = get_provider(self.provider_name)
            if not provider:
                logger.error("[%s] Provider 未注册", self.channel_name)
                return False

            # 优先企业应用点对点消息
            sent = False
            if integration.app_id:
                sent = await self._send_work_message(provider, integration, external_id, content, event)

            # 降级群机器人
            if not sent and integration.webhook_url:
                secret = resolve_secret_ref(integration.webhook_secret_ref)
                sent = await provider.send_robot_message(
                    webhook_url=integration.webhook_url,
                    secret=secret,
                    msg_type="markdown",
                    content=self._build_robot_content(content),
                )

            self._log(event, content, external_id, sent)
            return sent

        except Exception as e:
            logger.error("[%s] 发送失败: %s", self.channel_name, e, exc_info=True)
            self._log(event, content, "", False, error=str(e))
            return False

    # ============================================================
    # 子类可覆盖的差异化逻辑
    # ============================================================

    async def _send_work_message(
        self,
        provider,
        integration: Integration,
        external_id: str,
        content: NotificationContent,
        event: NotificationEvent,
    ) -> bool:
        """发送企业应用消息。默认用 text 类型，子类可覆盖以支持卡片/模板。"""
        title = content.title or ""
        body = content.content or ""
        text = f"{title}\n{body}" if title and body else (body or title)
        return await provider.send_work_message(
            integration=integration,
            to_user_id=external_id,
            msg_type="text",
            msg_content=text,
        )

    def _build_robot_content(self, content: NotificationContent) -> str:
        """构造群机器人 markdown 正文（子类可覆盖平台特有格式）。"""
        title = content.title or ""
        body = content.content or ""
        if title and body:
            return f"## {title}\n\n{body}"
        return body or title

    # ============================================================
    # 日志
    # ============================================================

    def _log(
        self,
        event: NotificationEvent,
        content: NotificationContent,
        recipient: str,
        success: bool,
        error: str | None = None,
    ) -> None:
        try:
            dispatch_meta = (event.extra_data or {}).get("_dispatch", {})
            log = NotificationLog(
                tenant_id=event.tenant_id,
                store_id=event.store_id,
                user_id=event.recipient_id,
                user_type=event.recipient_type,
                channel=self.channel_name,
                message_type=event.message_type,
                title=content.title,
                content=content.content,
                status="sent" if success else "failed",
                recipient=recipient,
                related_id=event.related_id,
                sent_at=datetime.utcnow() if success else None,
                error_message=error,
                primary_channel=dispatch_meta.get("primary_channel"),
                fallback_reason=dispatch_meta.get("fallback_reason"),
                channel_attempt_order=dispatch_meta.get("channel_attempt_order"),
            )
            self.db.add(log)
        except Exception:
            logger.exception("[%s] 写日志失败", self.channel_name)
