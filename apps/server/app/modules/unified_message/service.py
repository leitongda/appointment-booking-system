"""统一消息服务

替代 MessageService + NotificationDispatcher，操作新表。
"""
import asyncio
import logging
import uuid
from datetime import datetime, time
from typing import Any, Dict, List, Optional, Tuple

from jinja2 import BaseLoader, TemplateSyntaxError
from jinja2.sandbox import SandboxedEnvironment
from sqlalchemy import and_, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.unified_message.models import (
    NotificationDelivery,
    NotificationGroup,
    NotificationRecipient,
    UnifiedTemplate,
    ChannelStrategy,
    RecipientRule,
)
from app.modules.unified_message.schemas import (
    MessageQuery,
    MessageResponse,
    NotificationEvent,
    SendResult,
    BatchSendResult,
    UnreadCountResponse,
)
from app.modules.unified_message.rule_engine import RecipientRuleEngine
from app.infrastructure.notifications.registry import channel_registry, register_channels
from app.infrastructure.notifications.channels.base import BaseNotificationChannel
from app.infrastructure.notifications.metrics import (
    record_send,
    record_dedup_hit,
    track_send_latency,
)
from app.schemas.notification import NotificationContent
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

# 渠道字段映射（与 dispatcher.py 保持一致）
_CHANNEL_FIELD_MAP = {
    "in_app": "in_app_enabled",
    "sms": "sms_enabled",
    "wechat": "wechat_enabled",
    "email": "email_enabled",
    "websocket": "in_app_enabled",
}

# 消息类型字段映射（与 dispatcher.py 保持一致）
_TYPE_FIELD_MAP = {
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

# 默认渠道策略（与 dispatcher.py 保持一致）
_DEFAULT_CHANNEL_STRATEGY = {
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

_DEDUP_TTL = 86400  # 24 小时


class UnifiedMessageService:
    """统一消息服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        register_channels()

    # -----------------------------------------------------------------------
    # 发送
    # -----------------------------------------------------------------------

    async def send(self, event: NotificationEvent) -> SendResult:
        """统一发送入口

        流程：去重 → 解析接收人 → 渲染模板 → 获取渠道策略 → 偏好过滤 → 发送 → 记录
        """
        # 1. 去重检查（Redis 第一层 + DB dedup_key 第二层）
        if await self._check_dedup(event):
            logger.info(f"[统一消息] 重复通知已跳过: template={event.template_code}, user={event.recipient_id}")
            return SendResult(success=True, channels_attempted=0, channels_succeeded=0, channels_failed=0)

        # 2. 创建通知组
        group = await self._create_group(event)

        # 3. 创建接收人记录
        recipient = await self._create_recipient(event, group.id)

        # 4. 获取渠道列表和策略
        channels, strategy_type = await self._get_target_channels(event)

        # 5. 偏好过滤 + 静默时段检查
        channels = await self._filter_by_preference_and_quiet_hours(event, channels)

        if not channels:
            logger.warning(f"[统一消息] 无可用渠道: user={event.recipient_id}, type={event.message_type}")
            group.status = "failed"
            await self.db.commit()
            return SendResult(success=False, group_id=group.id, error_message="无可用渠道")

        # 6. 渲染内容
        content = await self._render_content(event)

        # 7. 按策略发送
        if strategy_type == "parallel" or strategy_type == "all":
            channels_attempted, channels_succeeded, channels_failed = await self._send_parallel(
                event, group, recipient, channels, content
            )
        else:
            channels_attempted, channels_succeeded, channels_failed = await self._send_fallback(
                event, group, recipient, channels, content
            )

        # 8. 更新通知组状态
        if channels_succeeded > 0 and channels_failed > 0:
            group.status = "partial"
        elif channels_succeeded > 0:
            group.status = "sent"
        else:
            group.status = "failed"

        recipient.status = "sent" if channels_succeeded > 0 else "failed"

        try:
            await self.db.commit()
        except Exception as e:
            logger.error(f"[统一消息] 提交事务失败: {e}", exc_info=True)

        # 如果发送成功，通过 WebSocket 推送新消息通知
        if channels_succeeded > 0:
            await self._notify_new_message(event, group.id)

        return SendResult(
            success=channels_succeeded > 0,
            group_id=group.id,
            channels_attempted=channels_attempted,
            channels_succeeded=channels_succeeded,
            channels_failed=channels_failed,
        )

    def send_sync(self, event: NotificationEvent) -> SendResult:
        """同步版本发送入口，供 Celery 任务使用

        使用 asyncio.run() 在独立事件循环中执行异步代码。
        """
        import asyncio
        try:
            return asyncio.run(self.send(event))
        except RuntimeError as e:
            # 如果已有事件循环在运行（如 Jupyter 环境），回退到 new_loop 方式
            if "cannot be called from a running event loop" in str(e):
                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(self.send(event))
                finally:
                    loop.close()
            raise

    async def send_to_rule(
        self,
        event: NotificationEvent,
        rule_id: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
    ) -> BatchSendResult:
        """根据规则发送通知

        Args:
            event: 通知事件（recipient_id 和 recipient_type 会被忽略）
            rule_id: 指定规则ID（可选，不指定则使用事件类型匹配规则）
            event_data: 事件数据（用于动态规则和事件驱动规则）

        Returns:
            批量发送结果
        """
        rule_engine = RecipientRuleEngine(self.db)

        # 解析接收人
        if rule_id:
            # 使用指定的规则
            rule = await self.db.get(RecipientRule, rule_id)
            if not rule:
                return BatchSendResult(
                    total=0, succeeded=0, failed=0,
                    results=[SendResult(success=False, error_message=f"规则不存在: {rule_id}")]
                )
            recipients = await rule_engine._resolve_rule(rule, event_data or {})
        else:
            # 根据事件类型匹配规则
            recipients = await rule_engine.resolve_recipients(
                tenant_id=event.tenant_id,
                event_type=event.template_code,
                event_data=event_data or {},
            )

        if not recipients:
            logger.warning(f"[统一消息] 规则未解析到接收人: template={event.template_code}")
            return BatchSendResult(total=0, succeeded=0, failed=0)

        # 批量发送
        results = []
        succeeded = 0
        failed = 0

        for recipient_info in recipients:
            # 创建新的事件（替换接收人信息）
            recipient_event = event.model_copy(
                update={
                    "recipient_id": recipient_info["user_id"],
                    "recipient_type": recipient_info["user_type"],
                }
            )

            result = await self.send(recipient_event)
            results.append(result)

            if result.success:
                succeeded += 1
            else:
                failed += 1

        return BatchSendResult(
            total=len(recipients),
            succeeded=succeeded,
            failed=failed,
            results=results,
        )

    async def get_rules(
        self, tenant_id: str, event_type: Optional[str] = None
    ) -> List[RecipientRule]:
        """获取接收人规则列表"""
        stmt = select(RecipientRule).where(RecipientRule.tenant_id == tenant_id)
        if event_type:
            stmt = stmt.where(
                (RecipientRule.event_type == event_type) | (RecipientRule.event_type.is_(None))
            )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_rule(self, tenant_id: str, rule_data: Dict[str, Any]) -> RecipientRule:
        """创建接收人规则"""
        rule = RecipientRule(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            **rule_data,
        )
        self.db.add(rule)
        await self.db.commit()
        return rule

    async def update_rule(
        self, rule_id: str, tenant_id: str, rule_data: Dict[str, Any]
    ) -> Optional[RecipientRule]:
        """更新接收人规则"""
        rule = await self.db.get(RecipientRule, rule_id)
        if not rule or rule.tenant_id != tenant_id:
            return None

        for key, value in rule_data.items():
            setattr(rule, key, value)

        await self.db.commit()
        return rule

    async def delete_rule(self, rule_id: str, tenant_id: str) -> bool:
        """删除接收人规则"""
        rule = await self.db.get(RecipientRule, rule_id)
        if not rule or rule.tenant_id != tenant_id:
            return False

        await self.db.delete(rule)
        await self.db.commit()
        return True

    # -----------------------------------------------------------------------
    # 模板管理
    # -----------------------------------------------------------------------

    async def get_templates(
        self,
        tenant_id: str,
        message_type: Optional[str] = None,
        status: Optional[int] = None,
    ) -> List[UnifiedTemplate]:
        """获取统一模板列表"""
        stmt = select(UnifiedTemplate).where(UnifiedTemplate.tenant_id == tenant_id)
        if message_type:
            stmt = stmt.where(UnifiedTemplate.message_type == message_type)
        if status is not None:
            stmt = stmt.where(UnifiedTemplate.status == status)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_template(
        self, tenant_id: str, template_data: Dict[str, Any]
    ) -> UnifiedTemplate:
        """创建统一模板"""
        # 检查 code 唯一性
        existing = await self.db.execute(
            select(UnifiedTemplate.id).where(
                and_(
                    UnifiedTemplate.tenant_id == tenant_id,
                    UnifiedTemplate.code == template_data.get("code"),
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"模板编码已存在: {template_data.get('code')}")

        template = UnifiedTemplate(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            **template_data,
        )
        self.db.add(template)
        await self.db.commit()
        return template

    async def update_template(
        self, template_id: str, tenant_id: str, template_data: Dict[str, Any]
    ) -> Optional[UnifiedTemplate]:
        """更新统一模板"""
        template = await self.db.get(UnifiedTemplate, template_id)
        if not template or template.tenant_id != tenant_id:
            return None

        # 如果更新了 code，检查唯一性
        new_code = template_data.get("code")
        if new_code and new_code != template.code:
            existing = await self.db.execute(
                select(UnifiedTemplate.id).where(
                    and_(
                        UnifiedTemplate.tenant_id == tenant_id,
                        UnifiedTemplate.code == new_code,
                        UnifiedTemplate.id != template_id,
                    )
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"模板编码已存在: {new_code}")

        for key, value in template_data.items():
            setattr(template, key, value)

        await self.db.commit()
        return template

    async def delete_template(self, template_id: str, tenant_id: str) -> bool:
        """删除统一模板"""
        template = await self.db.get(UnifiedTemplate, template_id)
        if not template or template.tenant_id != tenant_id:
            return False

        await self.db.delete(template)
        await self.db.commit()
        return True

    # -----------------------------------------------------------------------
    # 查询（兼容旧 API）
    # -----------------------------------------------------------------------

    async def get_user_messages(
        self, user_id: str, user_type: str, query: MessageQuery
    ) -> Tuple[List[dict], int]:
        """获取用户消息列表（兼容旧 MessageService.get_user_messages）"""
        # 使用 join 一次性获取 recipient 和 group 数据，避免 N+1 查询
        stmt = (
            select(
                NotificationRecipient,
                NotificationGroup.store_id,
                NotificationGroup.message_type,
                NotificationGroup.related_id,
            )
            .join(NotificationGroup, NotificationRecipient.group_id == NotificationGroup.id)
            .where(
                and_(
                    NotificationRecipient.user_id == user_id,
                    NotificationRecipient.user_type == user_type,
                )
            )
        )
        count_stmt = (
            select(func.count(NotificationRecipient.id))
            .where(
                and_(
                    NotificationRecipient.user_id == user_id,
                    NotificationRecipient.user_type == user_type,
                )
            )
        )

        # 按消息类型过滤
        if query.message_type:
            stmt = stmt.where(NotificationGroup.message_type == query.message_type)
            count_stmt = count_stmt.join(NotificationGroup, NotificationRecipient.group_id == NotificationGroup.id)
            count_stmt = count_stmt.where(NotificationGroup.message_type == query.message_type)

        # 按已读状态过滤
        if query.is_read is not None:
            stmt = stmt.where(NotificationRecipient.is_read == query.is_read)
            count_stmt = count_stmt.where(NotificationRecipient.is_read == query.is_read)

        stmt = stmt.order_by(NotificationRecipient.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)

        result = await self.db.execute(stmt)
        count_result = await self.db.execute(count_stmt)

        rows = result.all()
        total = count_result.scalar() or 0

        # 转换为与旧 API 兼容的 dict 格式
        messages = []
        for r, store_id, message_type, related_id in rows:
            messages.append({
                "id": r.id,
                "store_id": store_id,
                "user_id": r.user_id,
                "user_type": r.user_type,
                "title": r.title,
                "content": r.content,
                "message_type": message_type,
                "related_id": related_id,
                "is_read": r.is_read,
                "read_at": r.read_at,
                "created_at": r.created_at,
            })

        return messages, total

    async def get_unread_count(self, user_id: str, user_type: str) -> UnreadCountResponse:
        """获取未读消息数量（兼容旧 MessageService.get_unread_count）"""
        base_condition = and_(
            NotificationRecipient.user_id == user_id,
            NotificationRecipient.user_type == user_type,
            NotificationRecipient.is_read == 0,
        )

        # 使用单条 GROUP BY 查询获取所有消息类型的未读数
        stmt = (
            select(
                NotificationGroup.message_type,
                func.count(NotificationRecipient.id).label("count"),
            )
            .join(NotificationGroup, NotificationRecipient.group_id == NotificationGroup.id)
            .where(base_condition)
            .group_by(NotificationGroup.message_type)
        )
        result = await self.db.execute(stmt)
        type_counts = {row[0]: row[1] for row in result.all()}

        # 计算总数
        total = sum(type_counts.values())

        return UnreadCountResponse(
            total=total,
            appointment=type_counts.get("appointment", 0),
            consultation=type_counts.get("consultation", 0),
            schedule=type_counts.get("schedule", 0),
            system=type_counts.get("system", 0),
            stop_clinic=type_counts.get("stop_clinic", 0),
            feedback=type_counts.get("feedback", 0),
        )

    async def mark_as_read(self, message_id: str, user_id: str) -> bool:
        """标记单条消息为已读"""
        result = await self.db.execute(
            update(NotificationRecipient)
            .where(
                and_(
                    NotificationRecipient.id == message_id,
                    NotificationRecipient.user_id == user_id,
                )
            )
            .values(is_read=1, read_at=datetime.utcnow())
        )
        await self.db.commit()
        return result.rowcount > 0

    async def mark_all_as_read(
        self, user_id: str, user_type: str, message_type: Optional[str] = None
    ) -> int:
        """标记所有消息为已读"""
        stmt = (
            update(NotificationRecipient)
            .where(
                and_(
                    NotificationRecipient.user_id == user_id,
                    NotificationRecipient.user_type == user_type,
                    NotificationRecipient.is_read == 0,
                )
            )
            .values(is_read=1, read_at=datetime.utcnow())
        )

        if message_type:
            # 需要 join NotificationGroup 来过滤 message_type
            # SQLAlchemy update 不直接支持 join，使用 subquery
            group_ids = select(NotificationGroup.id).where(
                NotificationGroup.message_type == message_type
            )
            stmt = stmt.where(NotificationRecipient.group_id.in_(group_ids))

        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def delete(self, message_id: str, user_id: str) -> bool:
        """删除单条消息（软删除：标记为已删除）

        新表使用 NotificationRecipient，删除 = 将 is_read 标记为 2（已删除）。
        """
        result = await self.db.execute(
            update(NotificationRecipient)
            .where(
                and_(
                    NotificationRecipient.id == message_id,
                    NotificationRecipient.user_id == user_id,
                )
            )
            .values(is_read=2)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def delete_all_read(self, user_id: str, user_type: str) -> int:
        """删除所有已读消息（软删除：标记为已删除）"""
        result = await self.db.execute(
            update(NotificationRecipient)
            .where(
                and_(
                    NotificationRecipient.user_id == user_id,
                    NotificationRecipient.user_type == user_type,
                    NotificationRecipient.is_read == 1,
                )
            )
            .values(is_read=2)
        )
        await self.db.commit()
        return result.rowcount

    # -----------------------------------------------------------------------
    # 内部方法
    # -----------------------------------------------------------------------

    async def _create_group(self, event: NotificationEvent) -> NotificationGroup:
        """创建通知组"""
        related_id = event.related_id or ""
        dedup_key = f"{event.tenant_id}:{event.recipient_id}:{event.template_code}:{related_id}"

        group = NotificationGroup(
            id=str(uuid.uuid4()),
            tenant_id=event.tenant_id,
            store_id=event.store_id,
            event_type=event.template_code,
            template_code=event.template_code,
            message_type=event.message_type,
            priority="high" if event.priority >= 2 else "medium" if event.priority == 1 else "low",
            variables=event.variables,
            related_id=event.related_id,
            dedup_key=dedup_key,
            status="pending",
        )
        self.db.add(group)
        await self.db.flush()
        return group

    async def _create_recipient(
        self, event: NotificationEvent, group_id: str
    ) -> NotificationRecipient:
        """创建接收人记录"""
        recipient = NotificationRecipient(
            id=str(uuid.uuid4()),
            group_id=group_id,
            tenant_id=event.tenant_id,
            user_id=event.recipient_id,
            user_type=event.recipient_type,
            title=event.title,
            content=event.content,
            phone=event.recipient_phone,
            email=event.recipient_email,
            openid=event.recipient_openid,
            status="pending",
        )
        self.db.add(recipient)
        await self.db.flush()
        return recipient

    async def _check_dedup(self, event: NotificationEvent) -> bool:
        """去重检查（Redis 第一层 + DB 第二层）"""
        # Redis 第一层
        try:
            related_id = event.related_id or ""
            redis_key = f"notification:dedup:{event.tenant_id}:{event.recipient_id}:{event.template_code}:{related_id}"
            redis = await get_redis()
            is_first = await redis.set(redis_key, "1", ex=_DEDUP_TTL, nx=True)
            if not is_first:
                record_dedup_hit(event.tenant_id)
                return True  # Redis 命中，重复
        except Exception as e:
            logger.warning(f"[统一消息] Redis 去重检查失败: {e}")

        # DB 第二层
        related_id = event.related_id or ""
        dedup_key = f"{event.tenant_id}:{event.recipient_id}:{event.template_code}:{related_id}"
        existing = await self.db.execute(
            select(NotificationGroup.id).where(NotificationGroup.dedup_key == dedup_key)
        )
        if existing.scalar_one_or_none():
            record_dedup_hit(event.tenant_id)
            return True  # DB 命中，重复

        return False

    async def _get_target_channels(self, event: NotificationEvent) -> Tuple[List[str], str]:
        """获取目标渠道列表和策略类型

        Returns:
            (channels, strategy_type): 渠道列表和策略类型 (fallback/parallel/all)
        """
        if event.channels:
            return event.channels, "fallback"

        # 查询租户自定义渠道策略
        try:
            result = await self.db.execute(
                select(ChannelStrategy).where(
                    and_(
                        ChannelStrategy.tenant_id == event.tenant_id,
                        ChannelStrategy.event_type == event.template_code,
                        ChannelStrategy.status == 1,
                    )
                )
            )
            strategy = result.scalar_one_or_none()
            if strategy and strategy.channels:
                return strategy.channels, strategy.strategy or "fallback"
        except Exception:
            pass

        channels = _DEFAULT_CHANNEL_STRATEGY.get(event.message_type, ["in_app"])
        return channels, "fallback"

    async def _send_fallback(
        self,
        event: NotificationEvent,
        group: "NotificationGroup",
        recipient: "NotificationRecipient",
        channels: List[str],
        content: NotificationContent,
    ) -> Tuple[int, int, int]:
        """fallback 策略：按顺序尝试渠道，成功即停止"""
        attempted = 0
        succeeded = 0
        failed = 0

        for channel_name in channels:
            attempted += 1
            delivery = NotificationDelivery(
                id=str(uuid.uuid4()),
                group_id=group.id,
                recipient_id=recipient.id,
                tenant_id=event.tenant_id,
                channel=channel_name,
                status="pending",
                recipient_address=self._get_recipient_address(event, channel_name),
            )

            try:
                success, error_msg = await self._send_to_channel(event, channel_name, content)
                if success:
                    delivery.status = "sent"
                    delivery.sent_at = datetime.utcnow()
                    succeeded += 1
                    self.db.add(delivery)
                    return attempted, succeeded, failed
                else:
                    delivery.status = "failed"
                    delivery.error_message = error_msg
                    failed += 1
            except Exception as e:
                logger.error(f"[统一消息] 渠道 {channel_name} 发送异常: {e}", exc_info=True)
                delivery.status = "failed"
                delivery.error_message = str(e)
                failed += 1

            self.db.add(delivery)

        return attempted, succeeded, failed

    async def _send_parallel(
        self,
        event: NotificationEvent,
        group: "NotificationGroup",
        recipient: "NotificationRecipient",
        channels: List[str],
        content: NotificationContent,
    ) -> Tuple[int, int, int]:
        """parallel/all 策略：并发发送所有渠道"""
        attempted = len(channels)

        async def _try_channel(channel_name: str) -> Tuple[str, bool, str, Optional[datetime]]:
            """尝试单个渠道，返回 (channel_name, success, error_msg, sent_at)"""
            try:
                success, error_msg = await self._send_to_channel(event, channel_name, content)
                return channel_name, success, error_msg, datetime.utcnow() if success else None
            except Exception as e:
                logger.error(f"[统一消息] 渠道 {channel_name} 发送异常: {e}", exc_info=True)
                return channel_name, False, str(e), None

        results = await asyncio.gather(*[_try_channel(ch) for ch in channels])

        succeeded = 0
        failed = 0

        for channel_name, success, error_msg, sent_at in results:
            delivery = NotificationDelivery(
                id=str(uuid.uuid4()),
                group_id=group.id,
                recipient_id=recipient.id,
                tenant_id=event.tenant_id,
                channel=channel_name,
                recipient_address=self._get_recipient_address(event, channel_name),
            )

            if success:
                delivery.status = "sent"
                delivery.sent_at = sent_at
                succeeded += 1
            else:
                delivery.status = "failed"
                delivery.error_message = error_msg
                failed += 1

            self.db.add(delivery)

        return attempted, succeeded, failed

    async def _send_to_channel(
        self, event: NotificationEvent, channel_name: str, content: NotificationContent
    ) -> Tuple[bool, Optional[str]]:
        """发送到单个渠道

        Returns:
            (success, error_msg)
        """
        if not channel_registry.is_available(channel_name):
            record_send(channel_name, event.message_type, event.tenant_id, False)
            return False, "渠道不可用"

        channel_class = channel_registry.get(channel_name)
        if not channel_class:
            record_send(channel_name, event.message_type, event.tenant_id, False)
            return False, "渠道类未找到"

        channel = channel_class(self.db)

        valid, error_msg = await channel.validate_recipient(event)
        if not valid:
            record_send(channel_name, event.message_type, event.tenant_id, False)
            return False, error_msg

        with track_send_latency(channel_name):
            success = await channel.send(event, content)

        record_send(channel_name, event.message_type, event.tenant_id, success)
        if not success:
            return False, "发送失败"

        return True, None

    async def _filter_by_preference_and_quiet_hours(
        self, event: NotificationEvent, channels: List[str]
    ) -> List[str]:
        """根据用户偏好和免打扰时段过滤渠道"""
        try:
            stmt = text(
                "SELECT sms_enabled, email_enabled, wechat_enabled, in_app_enabled, "
                "appointment_enabled, reminder_enabled, stop_clinic_enabled, system_enabled, "
                "consultation_enabled, feedback_enabled, quiet_hours_start, quiet_hours_end "
                "FROM notification_preferences "
                "WHERE user_id = :uid AND user_type = :utype "
                "LIMIT 1"
            )
            result = await self.db.execute(
                stmt, {"uid": event.recipient_id, "utype": event.recipient_type}
            )
            row = result.first()

            if row is None:
                return channels

            prefs = dict(zip(
                ["sms_enabled", "email_enabled", "wechat_enabled", "in_app_enabled",
                 "appointment_enabled", "reminder_enabled", "stop_clinic_enabled",
                 "system_enabled", "consultation_enabled", "feedback_enabled",
                 "quiet_hours_start", "quiet_hours_end"],
                row,
            ))

            # 消息类型开关
            type_col = _TYPE_FIELD_MAP.get(event.message_type)
            if type_col and not prefs.get(type_col, True):
                return []

            # 渠道开关过滤
            filtered = []
            for ch in channels:
                channel_col = _CHANNEL_FIELD_MAP.get(ch)
                if channel_col and not prefs.get(channel_col, True):
                    continue
                filtered.append(ch)

            # 免打扰时段
            quiet_start = prefs.get("quiet_hours_start")
            quiet_end = prefs.get("quiet_hours_end")
            if quiet_start and quiet_end and self._in_quiet_hours(quiet_start, quiet_end):
                filtered = [ch for ch in filtered if ch == "in_app"]

            return filtered

        except Exception as e:
            logger.error(f"[统一消息] 偏好过滤失败: {e}", exc_info=True)
            return channels

    def _in_quiet_hours(self, start: str, end: str) -> bool:
        """检查当前时间是否在免打扰时段内"""
        try:
            now = datetime.now().time()
            start_time = time.fromisoformat(start)
            end_time = time.fromisoformat(end)
            if start_time <= end_time:
                return start_time <= now <= end_time
            else:
                return now >= start_time or now <= end_time
        except Exception:
            return False

    async def _render_content(self, event: NotificationEvent) -> NotificationContent:
        """渲染通知内容

        优先使用模板渲染，如果没有模板则使用简单的 title/content。
        """
        title = event.title or "系统通知"
        content = event.content or f"您有一条新的{event.message_type}通知。"

        # 尝试从模板渲染
        if event.template_code and event.variables:
            try:
                template = await self._get_template(event.tenant_id, event.template_code)
                if template:
                    rendered_title, rendered_content = self._render_template(template, event.variables)
                    title = rendered_title or title
                    content = rendered_content or content
            except Exception as e:
                logger.warning(f"[统一消息] 模板渲染失败，使用默认内容: {e}")

        return NotificationContent(
            title=title,
            content=content,
            template_variables=event.variables,
        )

    async def _get_template(self, tenant_id: str, template_code: str) -> Optional[UnifiedTemplate]:
        """获取模板（优先租户模板，其次全局模板）"""
        # 先查租户模板
        stmt = select(UnifiedTemplate).where(
            and_(
                UnifiedTemplate.tenant_id == tenant_id,
                UnifiedTemplate.code == template_code,
                UnifiedTemplate.status == 1,
            )
        )
        result = await self.db.execute(stmt)
        template = result.scalar_one_or_none()
        if template:
            return template

        # 再查全局模板（tenant_id 为 None）
        stmt = select(UnifiedTemplate).where(
            and_(
                UnifiedTemplate.tenant_id.is_(None),
                UnifiedTemplate.code == template_code,
                UnifiedTemplate.status == 1,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _notify_new_message(self, event: NotificationEvent, group_id: str):
        """通过 WebSocket 推送新消息通知

        仅对医生用户推送，患者端通常使用小程序/APP，不走 WebSocket。
        """
        if event.recipient_type != "doctor":
            return

        try:
            from app.core.websocket import notify_new_message

            message_data = {
                "group_id": group_id,
                "recipient_id": event.recipient_id,
                "recipient_type": event.recipient_type,
                "message_type": event.message_type,
                "title": event.title,
                "content": event.content,
                "template_code": event.template_code,
                "related_id": event.related_id,
            }

            await notify_new_message(
                doctor_id=event.recipient_id,
                message_data=message_data,
                tenant_id=event.tenant_id,
            )
            logger.debug(f"[统一消息] WebSocket 推送成功: doctor={event.recipient_id}")
        except Exception as e:
            # WebSocket 推送失败不影响主流程
            logger.warning(f"[统一消息] WebSocket 推送失败: {e}")

    def _render_template(self, template: UnifiedTemplate, variables: Dict[str, Any]) -> Tuple[str, str]:
        """使用 Jinja2 渲染模板"""
        env = SandboxedEnvironment(loader=BaseLoader())

        title = template.subject_template or ""
        content = template.text_template or ""

        try:
            if title:
                title_tmpl = env.from_string(title)
                title = title_tmpl.render(**variables)
            if content:
                content_tmpl = env.from_string(content)
                content = content_tmpl.render(**variables)

            # 向后兼容：如果渲染后仍包含单花括号占位符，执行简单替换
            if "{" in title or "{" in content:
                for key, value in variables.items():
                    placeholder = f"{{{key}}}"
                    title = title.replace(placeholder, str(value))
                    content = content.replace(placeholder, str(value))

            return title, content
        except TemplateSyntaxError as e:
            logger.warning(f"[统一消息] 模板语法错误: {e}")
            # 回退到简单替换
            for key, value in variables.items():
                placeholder = f"{{{key}}}"
                title = title.replace(placeholder, str(value))
                content = content.replace(placeholder, str(value))
            return title, content
        except Exception as e:
            logger.warning(f"[统一消息] 模板渲染异常: {e}")
            return title, content

    @staticmethod
    def _get_recipient_address(event: NotificationEvent, channel: str) -> Optional[str]:
        """获取接收地址"""
        if channel == "sms":
            return event.recipient_phone
        elif channel == "email":
            return event.recipient_email
        elif channel in ("wechat", "wechat_subscribe"):
            return event.recipient_openid
        elif channel in ("in_app", "websocket"):
            return f"{event.recipient_type}:{event.recipient_id}"
        return None
