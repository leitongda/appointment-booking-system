"""
邮件事件钩子异步任务

处理业务事件触发的邮件通知：
1. 根据 store_id + event_type 查询启用的邮件接收人
2. 查找对应的邮件模板并渲染
3. 通过 SMTP 发送邮件
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

from sqlalchemy import select

from app.celery_app import celery_app
from app.db.session import get_sync_db
from app.models.store_email_recipient import StoreEmailRecipient
from app.models.store import Store
from app.models.email_template import EmailTemplate
from app.models.notification_log import NotificationLog
from app.core.events import EVENT_TYPE_LABELS
from app.utils.email_sync import get_email_config, send_email_sync, render_email_template

logger = logging.getLogger(__name__)


_SIMPLE_SUBJECT_TEMPLATE = "[{{ store_name }}] {{ event_label }}通知"

_SIMPLE_CONTENT_TEMPLATE = """
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2 style="color: #1890ff;">{{ event_label }}通知</h2>
    <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
        <tr><td style="padding: 8px; color: #666;">门店</td><td style="padding: 8px;">{{ store_name }}</td></tr>
        <tr><td style="padding: 8px; color: #666;">预约编号</td><td style="padding: 8px;">{{ appointment_no }}</td></tr>
        <tr><td style="padding: 8px; color: #666;">患者</td><td style="padding: 8px;">{{ patient_name }}</td></tr>
        <tr><td style="padding: 8px; color: #666;">医生</td><td style="padding: 8px;">{{ doctor_name }}</td></tr>
        <tr><td style="padding: 8px; color: #666;">科室</td><td style="padding: 8px;">{{ department_name }}</td></tr>
        <tr><td style="padding: 8px; color: #666;">日期</td><td style="padding: 8px;">{{ appointment_date }}</td></tr>
        <tr><td style="padding: 8px; color: #666;">时段</td><td style="padding: 8px;">{{ appointment_time }}</td></tr>
    </table>
    <p style="color: #999; font-size: 12px;">此邮件由系统自动发送，请勿回复。</p>
</div>
"""


def _render_simple_template(event_type: str, context: Dict[str, Any]) -> tuple:
    """
    当没有匹配的邮件模板时，使用内置简单模板。

    Returns:
        (subject, content) 元组
    """
    event_label = EVENT_TYPE_LABELS.get(event_type, event_type)
    render_ctx = {**context, "event_label": event_label}
    subject = render_email_template(_SIMPLE_SUBJECT_TEMPLATE, render_ctx)
    content = render_email_template(_SIMPLE_CONTENT_TEMPLATE, render_ctx)
    return subject, content


@celery_app.task(
    name="app.tasks.email_hook_task.process_event_email",
    bind=True,
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=180,
    soft_time_limit=150,
)
def process_event_email(self, store_id: str, event_type: str, context_data: Dict[str, Any]):
    """
    处理业务事件邮件通知

    Args:
        store_id: 门店ID
        event_type: 事件类型
        context_data: 事件上下文（模板变量）
    """
    logger.info(f"[EmailHook] 开始处理: event={event_type}, store={store_id}")

    with get_sync_db() as db:
        try:
            # 1. 查询门店信息
            store_result = db.execute(
                select(Store).where(Store.id == store_id)
            )
            store = store_result.scalar_one_or_none()
            if not store:
                logger.warning(f"[EmailHook] 门店不存在: {store_id}")
                return {"sent": 0, "reason": "门店不存在"}

            # 补充门店名称到上下文
            context_data.setdefault("store_name", store.name)

            # 2. 查询订阅该事件的启用接收人
            recipients_result = db.execute(
                select(StoreEmailRecipient).where(
                    StoreEmailRecipient.store_id == store_id,
                    StoreEmailRecipient.status == 1,
                )
            )
            all_recipients = recipients_result.scalars().all()

            matched_recipients: List[StoreEmailRecipient] = []
            for r in all_recipients:
                if not r.event_types:
                    continue
                try:
                    subscribed = json.loads(r.event_types)
                    if event_type in subscribed:
                        matched_recipients.append(r)
                except (json.JSONDecodeError, TypeError):
                    continue

            if not matched_recipients:
                logger.info(f"[EmailHook] 无匹配接收人: event={event_type}, store={store_id}")
                return {"sent": 0, "reason": "无匹配接收人"}

            # 3. 查找匹配的邮件模板（优先租户模板，回退到平台模板）
            tenant_id = store.tenant_id
            template = None
            if tenant_id:
                template_result = db.execute(
                    select(EmailTemplate).where(
                        EmailTemplate.template_type == event_type,
                        EmailTemplate.status == 1,
                        EmailTemplate.tenant_id == tenant_id,
                    )
                )
                template = template_result.scalar_one_or_none()
            if not template:
                template_result = db.execute(
                    select(EmailTemplate).where(
                        EmailTemplate.template_type == event_type,
                        EmailTemplate.status == 1,
                        EmailTemplate.tenant_id.is_(None),
                    )
                )
                template = template_result.scalar_one_or_none()

            # 4. 渲染邮件内容
            if template:
                subject = render_email_template(template.subject_template, context_data)
                content = render_email_template(template.content_template, context_data)
            else:
                subject, content = _render_simple_template(event_type, context_data)

            # 5. 获取 SMTP 配置
            email_config = get_email_config(db)

            # 6. 逐个发送
            sent_count = 0
            failed_count = 0
            logs = []
            for recipient in matched_recipients:
                success = send_email_sync(email_config, recipient.email, subject, content)
                if success:
                    sent_count += 1
                    logger.info(f"[EmailHook] 发送成功: to={recipient.email}, event={event_type}")
                    try:
                        logs.append(NotificationLog(
                            tenant_id=store.tenant_id,
                            store_id=store_id,
                            channel="email",
                            message_type=event_type,
                            title=subject,
                            content=content,
                            status="sent",
                            recipient=recipient.email,
                            related_id=context_data.get("appointment_id"),
                            sent_at=datetime.utcnow(),
                        ))
                    except Exception as e:
                        logger.error(f"[EmailHook] 创建日志失败: {e}")
                else:
                    failed_count += 1
                    logger.warning(f"[EmailHook] 发送失败: to={recipient.email}, event={event_type}")
                    try:
                        logs.append(NotificationLog(
                            tenant_id=store.tenant_id,
                            store_id=store_id,
                            channel="email",
                            message_type=event_type,
                            title=subject,
                            content=content,
                            status="failed",
                            recipient=recipient.email,
                            related_id=context_data.get("appointment_id"),
                            error_message="SMTP发送失败",
                        ))
                    except Exception as e:
                        logger.error(f"[EmailHook] 创建失败日志失败: {e}")

            if logs:
                try:
                    db.add_all(logs)
                    db.commit()
                except Exception as e:
                    logger.error(f"[EmailHook] 批量保存日志失败: {e}")

            logger.info(
                f"[EmailHook] 处理完成: event={event_type}, store={store_id}, "
                f"sent={sent_count}, failed={failed_count}"
            )
            return {"sent": sent_count, "failed": failed_count}

        except Exception as e:
            logger.error(f"[EmailHook] 处理异常: event={event_type}, store={store_id}, error={e}")
            raise self.retry(exc=e)
