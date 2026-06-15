"""统一通知分发器"""
import logging
from datetime import datetime, time

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.infrastructure.notifications.registry import channel_registry, register_channels
from app.schemas.notification import (
    FallbackContext,
    NotificationContent,
    NotificationDispatchResult,
    NotificationEvent,
    NotificationSendResult,
)

logger = logging.getLogger(__name__)

# 渠道字段映射（与 MessageService 保持一致）
_CHANNEL_FIELD_MAP = {
    "in_app": "in_app_enabled",
    "sms": "sms_enabled",
    "wechat": "wechat_enabled",
    "email": "email_enabled",
    "websocket": "in_app_enabled",  # WebSocket 复用站内信偏好
}

# 消息类型字段映射（与 MessageService 保持一致）
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

# 默认渠道策略（按消息类型，按降级优先级排序）
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

# 去重缓存过期时间（秒）
_DEDUP_TTL = 86400  # 24 小时

# 短信内容最大长度
_SMS_MAX_CONTENT_LENGTH = 500


class NotificationDispatcher:
    """统一通知分发器

    负责将通知事件分发到合适的渠道，支持：
    - 用户偏好检查
    - 渠道策略选择
    - 失败降级（带上下文追踪）
    - 降级场景下的 SMS 内容适配
    - 日志记录（含降级元数据）
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        # 确保渠道已注册
        register_channels()

    async def dispatch(self, event: NotificationEvent) -> NotificationDispatchResult:
        """分发通知到合适的渠道，支持去重和渠道降级

        流程：
        1. 检查去重（24 小时内相同事件不重复发送）
        2. 获取并过滤渠道（偏好 + 免打扰）
        3. 按优先级依次尝试发送，失败后降级到下一渠道
        4. 任一渠道成功即停止降级
        5. 全部渠道失败则记录失败状态
        6. 降级场景下记录 FallbackContext 用于诊断

        Args:
            event: 通知事件

        Returns:
            分发结果（含降级上下文）
        """
        result = NotificationDispatchResult(event=event)

        # 1. 检查去重
        if await self._check_and_mark_dedup(event):
            logger.info(f"[通知分发] 重复通知已跳过: template={event.template_code}, user={event.recipient_id}, related_id={event.related_id}")
            result.skipped_channels = 1
            return result

        # 2. 获取并过滤渠道列表
        channels = await self._get_target_channels(event)
        channels = await self._filter_by_preference_and_quiet_hours(event, channels)

        result.total_channels = len(channels)

        if not channels:
            logger.warning(f"[通知分发] 无可用渠道（偏好过滤后）: user={event.recipient_id}, type={event.message_type}")
            return result

        # 3. 渲染通知内容
        content = await self._render_content(event)

        # 记录首选渠道（降级链中的第一个）
        primary_channel = channels[0] if channels else None

        # 记录降级过程中失败的渠道及原因
        failed_channel_reasons: dict[str, str] = {}

        # 4. 按渠道优先级依次发送（支持降级）
        for attempt_idx, channel_name in enumerate(channels):
            try:
                # 检查渠道是否可用
                if not channel_registry.is_available(channel_name):
                    logger.debug(f"[通知分发] 渠道不可用: {channel_name}")
                    result.skipped_channels += 1
                    failed_channel_reasons[channel_name] = "渠道未注册或不可用"
                    continue

                # 获取渠道实例
                channel_class = channel_registry.get(channel_name)
                if not channel_class:
                    logger.warning(f"[通知分发] 渠道类未找到: {channel_name}")
                    result.skipped_channels += 1
                    failed_channel_reasons[channel_name] = "渠道类未找到"
                    continue

                channel = channel_class(self.db)

                # 验证接收人信息
                valid, error_msg = await channel.validate_recipient(event)
                if not valid:
                    logger.debug(f"[通知分发] 接收人验证失败: {channel_name}, {error_msg}")
                    result.skipped_channels += 1
                    failed_channel_reasons[channel_name] = f"接收人验证失败: {error_msg}"
                    continue

                # 降级场景：如果是 SMS 渠道且非首选渠道，适配内容
                adapted_content = content
                is_fallback = attempt_idx > 0
                if is_fallback and channel_name == "sms":
                    adapted_content = self._adapt_content_for_sms(event, content)

                # 注入降级元数据到 event.extra_data，供渠道记录到 NotificationLog
                if is_fallback:
                    if event.extra_data is None:
                        event.extra_data = {}
                    event.extra_data["_dispatch"] = {
                        "primary_channel": primary_channel,
                        "fallback_reason": failed_channel_reasons.get(primary_channel, "发送失败"),
                        "channel_attempt_order": attempt_idx,
                    }

                # 发送通知
                success = await channel.send(event, adapted_content)

                send_result = NotificationSendResult(
                    channel=channel_name,
                    success=success,
                    error_message=None if success else "发送失败",
                    is_fallback=is_fallback,
                    attempt_order=attempt_idx,
                )
                result.results[channel_name] = send_result

                if success:
                    result.success_channels += 1

                    # 降级成功时记录 FallbackContext
                    if is_fallback and primary_channel:
                        result.fallback_context = FallbackContext(
                            primary_channel=primary_channel,
                            actual_channel=channel_name,
                            failed_channels=list(failed_channel_reasons.keys()),
                            fallback_reasons=failed_channel_reasons,
                        )
                        logger.info(
                            f"[通知分发] 渠道降级成功: 首选={primary_channel}, 实际={channel_name}, "
                            f"失败渠道={list(failed_channel_reasons.keys())}"
                        )
                    else:
                        logger.info(f"[通知分发] 渠道 {channel_name} 发送成功")

                    break
                else:
                    result.failed_channels += 1
                    failed_channel_reasons[channel_name] = "发送失败"
                    logger.warning(f"[通知分发] 渠道 {channel_name} 发送失败，尝试降级渠道")

            except Exception as e:
                logger.error(f"[通知分发] 渠道 {channel_name} 发送异常: {e}", exc_info=True)
                result.failed_channels += 1
                failed_channel_reasons[channel_name] = f"异常: {str(e)[:100]}"
                result.results[channel_name] = NotificationSendResult(
                    channel=channel_name,
                    success=False,
                    error_message=str(e),
                    is_fallback=attempt_idx > 0,
                    attempt_order=attempt_idx,
                )
                # 异常也继续尝试下一降级渠道

        # 5. 记录降级指标
        if result.fallback_context:
            try:
                from app.infrastructure.notifications.metrics import record_fallback
                record_fallback(
                    primary_channel=result.fallback_context.primary_channel,
                    actual_channel=result.fallback_context.actual_channel,
                    event_type=event.message_type,
                    tenant_id=event.tenant_id,
                )
            except Exception:
                pass  # 指标记录失败不影响主流程

        # 6. 提交数据库事务（通知日志）
        try:
            await self.db.commit()
        except Exception as e:
            logger.error(f"[通知分发] 提交事务失败: {e}", exc_info=True)

        return result

    async def _get_target_channels(self, event: NotificationEvent) -> list[str]:
        """获取目标渠道列表"""
        # 如果事件指定了渠道，使用指定渠道
        if event.channels:
            return event.channels

        # 否则使用默认策略
        return _DEFAULT_CHANNEL_STRATEGY.get(event.message_type, ["in_app"])

    async def _render_content(self, event: NotificationEvent) -> NotificationContent:
        """渲染通知内容

        TODO: 集成模板系统
        """
        # 临时实现：直接使用 event 中的 title 和 content
        if event.title and event.content:
            return NotificationContent(
                title=event.title,
                content=event.content,
                template_variables=event.variables,
            )

        # 如果没有提供，使用默认内容
        title = event.title or "系统通知"
        content = event.content or f"您有一条新的{event.message_type}通知。"

        return NotificationContent(
            title=title,
            content=content,
            template_variables=event.variables,
        )

    def _adapt_content_for_sms(
        self, event: NotificationEvent, content: NotificationContent
    ) -> NotificationContent:
        """降级场景下将通知内容适配为 SMS 友好格式

        当首选渠道（如微信）失败，降级到 SMS 时，需要确保：
        1. 核心信息（医生名、日期、时间、操作项）完整保留
        2. 去除不适用于纯文本的富文本标记
        3. 内容截断到 SMS 长度限制内，同时保留关键信息尾部
        4. 在内容末尾添加降级提示（通知用户此为短信降级发送）

        Args:
            event: 通知事件
            content: 原始渲染后的内容

        Returns:
            适配后的 SMS 友好内容
        """
        sms_title = content.title.strip()
        sms_content = content.content.strip()

        # 去除常见的富文本标记（Markdown/HTML 片段）
        import re
        sms_content = re.sub(r'<[^>]+>', '', sms_content)  # HTML tags
        sms_content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', sms_content)  # Markdown links: [text](url) -> text
        sms_content = re.sub(r'[*_~`]+', '', sms_content)  # Markdown emphasis
        sms_content = re.sub(r'\n{2,}', '\n', sms_content)  # 多余空行

        # 确保核心模板变量在内容中被提及（如果 content 中缺少则补充）
        variables = event.variables or {}
        essential_vars = {
            "doctor_name": "医生",
            "date": "日期",
            "time_slot": "时段",
            "time": "时间",
        }
        missing_essentials = []
        for var_key, var_label in essential_vars.items():
            var_value = variables.get(var_key)
            if var_value and str(var_value) not in sms_content:
                missing_essentials.append(f"{var_label}: {var_value}")

        if missing_essentials:
            sms_content = sms_content + "（" + "，".join(missing_essentials) + "）"

        # 截断到 SMS 长度限制，保留尾部关键信息
        if len(sms_content) > _SMS_MAX_CONTENT_LENGTH:
            sms_content = sms_content[:_SMS_MAX_CONTENT_LENGTH - 10] + "...详情请查看APP"

        return NotificationContent(
            title=sms_title,
            content=sms_content,
            template_variables=content.template_variables,
        )

    async def _check_preference(self, event: NotificationEvent, channel: str) -> bool:
        """检查用户是否启用了该渠道

        默认返回 True（未设置偏好时允许通知）。
        """
        from app.common.notification_preference import check_notification_preference
        return await check_notification_preference(
            self.db, event.recipient_id, event.recipient_type, channel, event.message_type
        )

    async def _check_and_mark_dedup(self, event: NotificationEvent) -> bool:
        """检查并标记去重

        使用 Redis SET NX EX 实现原子性去重检查和标记。

        Args:
            event: 通知事件

        Returns:
            True 表示已发送过（应跳过），False 表示首次发送
        """
        try:
            # 构建去重键：包含租户、接收人、模板、关联业务ID
            related_id = event.related_id or ""
            dedup_key = f"notification:dedup:{event.tenant_id}:{event.recipient_id}:{event.template_code}:{related_id}"

            # 尝试设置键（NX：仅当键不存在时设置）
            # 返回 True 表示设置成功（首次发送），False 表示键已存在（重复）
            redis = await get_redis()
            is_first = await redis.set(dedup_key, "1", ex=_DEDUP_TTL, nx=True)

            if is_first:
                logger.debug(f"[通知分发] 去重检查通过（首次发送）: {dedup_key}")
            else:
                logger.debug(f"[通知分发] 去重拦截（重复发送）: {dedup_key}")

            return not is_first  # 返回 True 表示重复

        except Exception as e:
            logger.error(f"[通知分发] 去重检查失败: {e}", exc_info=True)
            return False  # 出错时不拦截，允许发送

    async def _filter_by_preference_and_quiet_hours(self, event: NotificationEvent, channels: list[str]) -> list[str]:
        """根据用户偏好和免打扰时段过滤渠道

        Args:
            event: 通知事件
            channels: 原始渠道列表

        Returns:
            过滤后的渠道列表
        """
        try:
            from app.common.notification_preference import (
                CHANNEL_FIELD_MAP as SHARED_CHANNEL_MAP,
            )
            from app.common.notification_preference import (
                TYPE_FIELD_MAP as SHARED_TYPE_MAP,
            )
            from app.common.notification_preference import (
                get_user_preferences,
            )

            prefs = await get_user_preferences(self.db, event.recipient_id, event.recipient_type)
            if prefs is None:
                return channels  # 无偏好设置，不过滤

            # 检查消息类型是否启用
            type_col = SHARED_TYPE_MAP.get(event.message_type)
            if type_col and not prefs.get(type_col, True):
                logger.debug(f"[通知分发] 用户已禁用消息类型: {event.message_type}")
                return []

            # 按通道开关过滤
            filtered = []
            for ch in channels:
                channel_col = SHARED_CHANNEL_MAP.get(ch)
                if channel_col and not prefs.get(channel_col, True):
                    logger.debug(f"[通知分发] 用户已禁用通道: {ch}")
                    continue
                filtered.append(ch)

            # 检查免打扰时段
            quiet_start = prefs.get("quiet_hours_start")
            quiet_end = prefs.get("quiet_hours_end")
            if quiet_start and quiet_end and self._in_quiet_hours(quiet_start, quiet_end):
                logger.info("[通知分发] 当前处于免打扰时段，仅保留 in_app 渠道")
                filtered = [ch for ch in filtered if ch == "in_app"]

            return filtered

        except Exception as e:
            logger.error(f"[通知分发] 偏好过滤失败: {e}", exc_info=True)
            return channels  # 出错时使用原列表

    def _in_quiet_hours(self, start: str, end: str) -> bool:
        """检查当前时间是否在免打扰时段内

        Args:
            start: 开始时间，格式 "HH:MM"
            end: 结束时间，格式 "HH:MM"

        Returns:
            是否在免打扰时段内
        """
        try:
            now = datetime.now().time()
            start_time = time.fromisoformat(start)
            end_time = time.fromisoformat(end)

            # 处理跨天情况（如 22:00 - 08:00）
            if start_time <= end_time:
                # 同一天内
                return start_time <= now <= end_time
            else:
                # 跨天：当前时间 >= 开始时间 OR <= 结束时间
                return now >= start_time or now <= end_time

        except Exception as e:
            logger.warning(f"[通知分发] 免打扰时段解析失败: {e}")
            return False
