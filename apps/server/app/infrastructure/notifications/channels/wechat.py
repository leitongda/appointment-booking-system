"""微信订阅消息渠道适配器"""
import logging
from datetime import datetime

from sqlalchemy import select

from app.infrastructure.notifications.channels.base import BaseNotificationChannel
from app.infrastructure.wechat.service import WechatService
from app.models.notification_log import NotificationLog
from app.models.user import User
from app.schemas.notification import NotificationContent, NotificationEvent

logger = logging.getLogger(__name__)


class WechatChannel(BaseNotificationChannel):
    """微信订阅消息渠道

    通过 WechatService 发送微信小程序订阅消息。
    """

    @property
    def channel_name(self) -> str:
        return "wechat"

    async def validate_recipient(self, event: NotificationEvent) -> tuple[bool, str | None]:
        """微信需要 openid"""
        if not event.recipient_openid:
            # 尝试从数据库获取 openid
            if event.recipient_type == "patient":
                result = await self.db.execute(
                    select(User.openid).where(User.id == event.recipient_id)
                )
                openid = await result.scalar_one_or_none()
                if not openid:
                    return False, "用户未绑定微信或缺少 openid"
                event.recipient_openid = openid
            else:
                return False, "缺少微信 openid"
        return True, None

    async def send(self, event: NotificationEvent, content: NotificationContent) -> bool:
        """发送微信订阅消息"""
        try:
            # 检查是否有微信模板配置
            template_id = await self._get_template_id(event.template_code, event.tenant_id)
            if not template_id:
                logger.warning(f"[微信] 未配置模板: {event.template_code}，跳过发送")
                return False

            # 获取模板映射配置
            template_mapping = await self._get_template_mapping(event.template_code, event.tenant_id)

            # 构建模板数据
            template_data = self._build_template_data(content, event.variables, template_mapping)

            # 发送订阅消息
            wechat_service = WechatService(self.db, store_id=event.store_id)
            success = await wechat_service.send_subscribe_message(
                openid=event.recipient_openid,
                template_id=template_id,
                data=template_data,
            )

            if success:
                # 记录通知日志
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
                    status="sent",
                    recipient=event.recipient_openid,
                    related_id=event.related_id,
                    sent_at=datetime.utcnow(),
                    primary_channel=dispatch_meta.get("primary_channel"),
                    fallback_reason=dispatch_meta.get("fallback_reason"),
                    channel_attempt_order=dispatch_meta.get("channel_attempt_order"),
                )
                self.db.add(log)

                logger.info(f"[微信] 发送成功: user={event.recipient_id}, template={event.template_code}")
            else:
                # 记录失败日志
                log = NotificationLog(
                    tenant_id=event.tenant_id,
                    store_id=event.store_id,
                    user_id=event.recipient_id,
                    user_type=event.recipient_type,
                    channel=self.channel_name,
                    message_type=event.message_type,
                    title=content.title,
                    status="failed",
                    recipient=event.recipient_openid,
                    related_id=event.related_id,
                    error_message="微信接口返回失败",
                )
                self.db.add(log)

            return success

        except Exception as e:
            logger.error(f"[微信] 发送失败: {e}", exc_info=True)

            # 记录失败日志
            try:
                log = NotificationLog(
                    tenant_id=event.tenant_id,
                    store_id=event.store_id,
                    user_id=event.recipient_id,
                    user_type=event.recipient_type,
                    channel=self.channel_name,
                    message_type=event.message_type,
                    title=content.title,
                    status="failed",
                    recipient=event.recipient_openid or "",
                    related_id=event.related_id,
                    error_message=str(e),
                )
                self.db.add(log)
            except Exception:
                pass

            return False

    async def _get_template_id(self, template_code: str, tenant_id: str) -> str | None:
        """获取微信模板 ID

        从 unified_templates 表读取微信模板配置。
        优先查找租户模板，其次查找全局模板。
        """
        from sqlalchemy import and_

        from app.models.unified_template import UnifiedTemplate

        # 先查租户模板
        stmt = select(UnifiedTemplate.wechat_template_id).where(
            and_(
                UnifiedTemplate.tenant_id == tenant_id,
                UnifiedTemplate.code == template_code,
                UnifiedTemplate.status == 1,
                UnifiedTemplate.wechat_template_id.isnot(None),
            )
        )
        result = await self.db.execute(stmt)
        template_id = result.scalar_one_or_none()
        if template_id:
            return template_id

        # 再查全局模板
        stmt = select(UnifiedTemplate.wechat_template_id).where(
            and_(
                UnifiedTemplate.tenant_id.is_(None),
                UnifiedTemplate.code == template_code,
                UnifiedTemplate.status == 1,
                UnifiedTemplate.wechat_template_id.isnot(None),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_template_mapping(self, template_code: str, tenant_id: str) -> dict | None:
        """获取微信模板字段映射

        从 unified_templates 表读取 wechat_template_mapping 配置。
        """
        from sqlalchemy import and_

        from app.models.unified_template import UnifiedTemplate

        # 先查租户模板
        stmt = select(UnifiedTemplate.wechat_template_mapping).where(
            and_(
                UnifiedTemplate.tenant_id == tenant_id,
                UnifiedTemplate.code == template_code,
                UnifiedTemplate.status == 1,
                UnifiedTemplate.wechat_template_mapping.isnot(None),
            )
        )
        result = await self.db.execute(stmt)
        mapping = result.scalar_one_or_none()
        if mapping:
            return mapping

        # 再查全局模板
        stmt = select(UnifiedTemplate.wechat_template_mapping).where(
            and_(
                UnifiedTemplate.tenant_id.is_(None),
                UnifiedTemplate.code == template_code,
                UnifiedTemplate.status == 1,
                UnifiedTemplate.wechat_template_mapping.isnot(None),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    def _build_template_data(
        self,
        content: NotificationContent,
        variables: dict,
        template_mapping: dict | None = None,
    ) -> dict:
        """构建微信模板数据

        微信订阅消息格式：
        {
            "thing1": {"value": "预约成功"},
            "thing2": {"value": "李医生"},
            "date3": {"value": "2024-01-01 09:00"}
        }

        Args:
            content: 通知内容
            variables: 模板变量
            template_mapping: 字段映射配置，格式如：
                {"thing1": "title", "thing2": "doctor_name", "date3": "time"}
                如果为 None，则直接使用 variables
        """
        if template_mapping:
            # 根据映射配置构建数据
            data = {}
            for wx_field, var_key in template_mapping.items():
                value = variables.get(var_key) or getattr(content, var_key, None) or ""
                data[wx_field] = {"value": str(value)}
            return data
        else:
            # 默认映射：直接使用 variables
            return {k: {"value": str(v)} for k, v in variables.items()}
