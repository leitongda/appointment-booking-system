"""审批流监听器触发服务

负责:
- 节点级监听器触发 (fire_node_listeners)
- 全局监听器触发 (fire_global_listeners)
- 动作分发: webhook / notification / sms / callback / integration_push
- Jinja2 沙箱模板渲染

监听器配置格式 (存储在 node.listeners / flow_def.global_listeners JSON 中):
[
    {
        "event": "node_enter",
        "action": "webhook",
        "config": {
            "url": "https://example.com/webhook",
            "headers": {"Authorization": "Bearer xxx"},
            "body_template": "{\"instanceId\": \"{{instanceId}}\"}"
        }
    },
    {
        "event": "node_leave",
        "action": "notification",
        "config": {
            "user_ids": ["user-1", "user-2"],
            "title_template": "审批通知: {{flowName}}",
            "content_template": "{{applicantName}} 的审批已通过 {{nodeName}}"
        }
    },
    {
        "event": "node_enter",
        "action": "integration_push",
        "config": {
            "provider": "dingtalk",
            "target": "work_message",
            "user_ids": ["admin-1", "admin-2"],
            "title_template": "审批待办: {{flowName}}",
            "content_template": "{{applicantName}} 提交的审批等待您处理"
        }
    }
]

支持的事件:
- node_enter / node_leave (节点级)
- instance_approved / instance_rejected / instance_cancelled (全局级)
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import httpx
import structlog
from jinja2 import Undefined
from jinja2.sandbox import SandboxedEnvironment
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval_flow import ApprovalFlowDefinition, ApprovalFlowNode, ApprovalInstance
from app.modules.approval_flows.callback_registry import callback_registry

logger = structlog.get_logger(__name__)

# Jinja2 沙箱环境，禁止访问 Python 对象属性（安全渲染用户模板）
# 使用默认的 Undefined（未定义变量渲染为空字符串）
_jinja_env = SandboxedEnvironment(autoescape=False, undefined=Undefined)


class ListenerService:
    """审批流监听器触发服务"""

    # Webhook 默认参数
    WEBHOOK_TIMEOUT_SECONDS = 10
    WEBHOOK_MAX_RETRIES = 3
    WEBHOOK_RETRY_DELAY_SECONDS = 1

    # ============================================================
    # 公开方法 — 节点级监听器
    # ============================================================

    async def fire_node_listeners(
        self,
        event: str,
        node: ApprovalFlowNode,
        instance: ApprovalInstance,
        db: AsyncSession,
    ) -> None:
        """触发节点级监听器。

        Args:
            event: 事件名 (node_enter / node_leave)
            node: 当前节点
            instance: 审批实例
            db: 数据库会话
        """
        listeners = node.listeners
        if not listeners or not isinstance(listeners, list):
            return

        matching = [l for l in listeners if l.get("event") == event]
        if not matching:
            return

        logger.info(
            "node_listener_fired",
            instance_id=instance.id,
            node_key=node.node_key,
            event=event,
            listener_count=len(matching),
        )

        for listener in matching:
            try:
                await self._execute_action(listener, instance, node, db)
            except Exception:
                logger.exception(
                    "node_listener_error",
                    instance_id=instance.id,
                    node_key=node.node_key,
                    event=event,
                    action=listener.get("action"),
                )

    # ============================================================
    # 公开方法 — 全局监听器
    # ============================================================

    async def fire_global_listeners(
        self,
        event: str,
        flow_def: ApprovalFlowDefinition,
        instance: ApprovalInstance,
        db: AsyncSession,
    ) -> None:
        """触发全局监听器。

        Args:
            event: 事件名 (instance_approved / instance_rejected / instance_cancelled)
            flow_def: 流程定义（含 global_listeners）
            instance: 审批实例
            db: 数据库会话
        """
        listeners = flow_def.global_listeners
        if not listeners or not isinstance(listeners, list):
            return

        matching = [l for l in listeners if l.get("event") == event]
        if not matching:
            return

        logger.info(
            "global_listener_fired",
            instance_id=instance.id,
            flow_def_id=flow_def.id,
            event=event,
            listener_count=len(matching),
        )

        for listener in matching:
            try:
                await self._execute_action(listener, instance, None, db)
            except Exception:
                logger.exception(
                    "global_listener_error",
                    instance_id=instance.id,
                    flow_def_id=flow_def.id,
                    event=event,
                    action=listener.get("action"),
                )

    # ============================================================
    # 内部方法 — 动作分发
    # ============================================================

    async def _execute_action(
        self,
        listener: dict[str, Any],
        instance: ApprovalInstance,
        node: ApprovalFlowNode | None,
        db: AsyncSession,
    ) -> None:
        """分发执行监听器动作。"""
        action = listener.get("action")
        config = listener.get("config", {})

        if action == "webhook":
            await self._fire_webhook(config, instance, node)
        elif action == "notification":
            await self._fire_notification(config, instance, node)
        elif action == "sms":
            await self._fire_sms(config, instance, node)
        elif action == "callback":
            await self._fire_callback(config, instance, db)
        elif action == "integration_push":
            await self._fire_integration_push(config, instance, node, db)
        else:
            logger.warning(
                "unknown_listener_action",
                action=action,
                instance_id=instance.id,
            )

    # ============================================================
    # 内部方法 — Webhook
    # ============================================================

    async def _fire_webhook(
        self,
        config: dict[str, Any],
        instance: ApprovalInstance,
        node: ApprovalFlowNode | None,
    ) -> None:
        """HTTP POST webhook，支持重试。失败记录日志，不抛异常。"""
        url = config.get("url")
        if not url:
            logger.warning("webhook_missing_url", instance_id=instance.id)
            return

        headers = config.get("headers") or {}
        headers.setdefault("Content-Type", "application/json")

        body_template = config.get("body_template", "")
        if body_template:
            body_str = self._render_template(body_template, instance, node)
        else:
            body_str = "{}"

        timeout = config.get("timeout", self.WEBHOOK_TIMEOUT_SECONDS)
        max_retries = config.get("max_retries", self.WEBHOOK_MAX_RETRIES)

        last_error: str | None = None
        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(url, content=body_str, headers=headers)
                    if response.status_code < 400:
                        logger.info(
                            "webhook_success",
                            instance_id=instance.id,
                            url=url,
                            status_code=response.status_code,
                            attempt=attempt,
                        )
                        return
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
            except httpx.TimeoutException:
                last_error = f"timeout after {timeout}s"
            except httpx.RequestError as e:
                last_error = f"request error: {e}"

            if attempt < max_retries:
                delay = config.get("retry_delay", self.WEBHOOK_RETRY_DELAY_SECONDS)
                await asyncio.sleep(delay)

        # 所有重试均失败 — 记录日志，不抛异常
        logger.error(
            "webhook_failed",
            instance_id=instance.id,
            url=url,
            attempts=max_retries,
            last_error=last_error,
        )

    # ============================================================
    # 内部方法 — 站内通知
    # ============================================================

    async def _fire_notification(
        self,
        config: dict[str, Any],
        instance: ApprovalInstance,
        node: ApprovalFlowNode | None,
    ) -> None:
        """发送站内通知。优先调用 notifications 模块，不可用时降级为 logging。"""
        user_ids = config.get("user_ids") or []
        if not user_ids:
            logger.warning("notification_missing_user_ids", instance_id=instance.id)
            return

        title_template = config.get("title_template", "审批通知")
        content_template = config.get("content_template", "")

        title = self._render_template(title_template, instance, node)
        content = self._render_template(content_template, instance, node)

        # 尝试调用 notifications 模块
        try:
            from app.modules.notifications.service import NotificationService

            for uid in user_ids:
                await NotificationService.create(
                    db=None,  # 类型提示，实际由调用方管理事务
                    tenant_id=instance.tenant_id,
                    user_id=uid,
                    title=title,
                    content=content,
                    message_type="approval",
                    related_id=instance.id,
                )
            logger.info(
                "notification_sent",
                instance_id=instance.id,
                user_count=len(user_ids),
                title=title,
            )
            return
        except ImportError:
            pass
        except Exception as e:
            logger.warning(
                "notification_module_error",
                instance_id=instance.id,
                error=str(e),
            )

        # 降级: 仅记录日志
        logger.info(
            "notification_fallback_log",
            instance_id=instance.id,
            user_ids=user_ids,
            title=title,
            content=content,
        )

    # ============================================================
    # 内部方法 — 短信
    # ============================================================

    async def _fire_sms(
        self,
        config: dict[str, Any],
        instance: ApprovalInstance,
        node: ApprovalFlowNode | None,
    ) -> None:
        """发送短信通知。优先调用 SMS 基础设施，不可用时降级为 logging。"""
        phones = config.get("phones") or []
        if not phones:
            logger.warning("sms_missing_phones", instance_id=instance.id)
            return

        content_template = config.get("content_template", "")
        content = self._render_template(content_template, instance, node)

        try:
            from app.infrastructure.sms.service import SmsService

            for phone in phones:
                await SmsService._send_business_sms(
                    tenant_id=instance.tenant_id,
                    phone=phone,
                    template_code="approval_notify",
                    template_params={"content": content},
                    message_type="approval",
                    title="审批通知",
                    content=content,
                    user_id=instance.applicant_id,
                    related_id=instance.id,
                )
            logger.info(
                "sms_sent",
                instance_id=instance.id,
                phone_count=len(phones),
            )
            return
        except ImportError:
            pass
        except Exception as e:
            logger.warning(
                "sms_module_error",
                instance_id=instance.id,
                error=str(e),
            )

        # 降级: 仅记录日志
        logger.info(
            "sms_fallback_log",
            instance_id=instance.id,
            phones=phones,
            content=content,
        )

    # ============================================================
    # 内部方法 — 业务回调
    # ============================================================

    async def _fire_callback(
        self,
        config: dict[str, Any],
        instance: ApprovalInstance,
        db: AsyncSession,
    ) -> None:
        """通过 callback_registry 触发业务回调。"""
        callback_action = config.get("callback_action", "on_approved")
        business_type = instance.business_type

        logger.info(
            "listener_callback_fired",
            instance_id=instance.id,
            business_type=business_type,
            callback_action=callback_action,
        )
        await callback_registry.execute(business_type, callback_action, instance, db)

    # ============================================================
    # 内部方法 — 第三方集成推送（钉钉/企业微信/飞书）
    # ============================================================

    async def _fire_integration_push(
        self,
        config: dict[str, Any],
        instance: ApprovalInstance,
        node: ApprovalFlowNode | None,
        db: AsyncSession,
    ) -> None:
        """通过第三方集成平台推送审批通知。

        支持两种推送目标：
        - work_message: 企业应用点对点消息（需指定 user_ids，查 IntegrationBinding 拿平台 userId）
        - robot: 群机器人消息（推送到指定群）

        config 示例:
            {
                "provider": "dingtalk",
                "target": "work_message",  # 或 "robot"
                "user_ids": ["admin-1"],   # target=work_message 时
                "title_template": "审批待办: {{flowName}}",
                "content_template": "{{applicantName}} 提交的审批等待您处理"
            }
        """
        provider_name = config.get("provider")
        target = config.get("target", "work_message")
        if not provider_name:
            logger.warning("integration_push_missing_provider", instance_id=instance.id)
            return

        try:
            from sqlalchemy import select

            from app.infrastructure.integrations import get_provider
            from app.models.integration import Integration, IntegrationBinding

            # 加载租户集成配置
            stmt = select(Integration).where(
                Integration.tenant_id == instance.tenant_id,
                Integration.provider == provider_name,
                Integration.status == 1,
            )
            result = await db.execute(stmt)
            integration = result.scalar_one_or_none()
            if not integration:
                logger.warning(
                    "integration_push_not_configured",
                    instance_id=instance.id,
                    provider=provider_name,
                )
                return

            impl = get_provider(provider_name)
            if not impl:
                logger.warning("integration_push_provider_missing", provider=provider_name)
                return

            title = self._render_template(
                config.get("title_template") or config.get("titleTemplate") or "审批通知",
                instance, node,
            )
            content = self._render_template(
                config.get("content_template") or config.get("contentTemplate") or "",
                instance, node,
            )

            if target == "robot":
                # 群机器人推送
                if not integration.webhook_url:
                    logger.warning("integration_push_no_webhook", instance_id=instance.id)
                    return
                from app.common.secret_refs import resolve_secret_ref

                secret = resolve_secret_ref(integration.webhook_secret_ref)
                markdown = f"## {title}\n\n{content}" if title else content
                await impl.send_robot_message(
                    webhook_url=integration.webhook_url,
                    secret=secret,
                    msg_type="markdown",
                    content=markdown,
                )
                logger.info(
                    "integration_push_robot_sent",
                    instance_id=instance.id,
                    provider=provider_name,
                )
                return

            # 点对点工作通知
            user_ids = config.get("user_ids") or []
            if not user_ids:
                logger.warning("integration_push_no_users", instance_id=instance.id)
                return

            # 批量查绑定关系，拿平台 userId
            stmt = select(IntegrationBinding).where(
                IntegrationBinding.tenant_id == instance.tenant_id,
                IntegrationBinding.provider == provider_name,
                IntegrationBinding.user_id.in_(user_ids),
            )
            result = await db.execute(stmt)
            bindings = result.scalars().all()
            if not bindings:
                logger.warning(
                    "integration_push_no_bindings",
                    instance_id=instance.id,
                    provider=provider_name,
                    user_count=len(user_ids),
                )
                return

            text = f"{title}\n{content}" if title and content else (content or title)
            success_count = 0
            for binding in bindings:
                ok = await impl.send_work_message(
                    integration=integration,
                    to_user_id=binding.external_id,
                    msg_type="text",
                    msg_content=text,
                )
                if ok:
                    success_count += 1

            logger.info(
                "integration_push_work_sent",
                instance_id=instance.id,
                provider=provider_name,
                total=len(bindings),
                success=success_count,
            )

        except Exception:
            logger.exception(
                "integration_push_error",
                instance_id=instance.id,
                provider=config.get("provider"),
            )

    def _render_template(
        self,
        template: str,
        instance: ApprovalInstance,
        node: ApprovalFlowNode | None,
    ) -> str:
        """Jinja2 沙箱渲染模板变量。

        可用变量:
            {{instanceId}}, {{flowName}}, {{nodeKey}}, {{nodeName}}
            {{applicantId}}, {{applicantName}}, {{action}}, {{timestamp}}
        """
        if not template:
            return ""

        context = {
            "instanceId": instance.id or "",
            "flowName": instance.title or "",
            "nodeKey": node.node_key if node else "",
            "nodeName": node.node_name if node else "",
            "applicantId": instance.applicant_id or "",
            "applicantName": instance.applicant_name or "",
            "action": instance.status or "",
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            tmpl = _jinja_env.from_string(template)
            return tmpl.render(**context)
        except Exception:
            logger.exception(
                "template_render_error",
                instance_id=instance.id,
                template=template[:200],
            )
            return template
