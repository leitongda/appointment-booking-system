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
from app.models.settings import SystemSetting as Settings
from app.core.events import EVENT_TYPE_LABELS

logger = logging.getLogger(__name__)


def _get_email_config(db) -> dict:
    """从数据库获取 SMTP 邮件配置（同步版本）"""
    try:
        result = db.execute(
            select(Settings).where(Settings.category == "email")
        )
        settings_list = result.scalars().all()
        config = {}
        for s in settings_list:
            config[s.key] = s.value
        return config
    except Exception as e:
        logger.error(f"获取邮件配置失败: {e}")
        return {}


def _send_email_sync(config: dict, to_email: str, subject: str, content: str) -> bool:
    """同步发送邮件（Celery worker 环境）"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.utils import formataddr

    smtp_host = config.get("smtp_host", "")
    smtp_port = int(config.get("smtp_port", 465))
    smtp_user = config.get("smtp_user", "")
    smtp_password = config.get("smtp_password", "")
    smtp_ssl = config.get("smtp_ssl", "true").lower() in ("true", "1", "yes")
    sender_name = config.get("sender_name", "")
    sender_email = config.get("sender_email", smtp_user)

    if not smtp_host or not smtp_user or not smtp_password:
        logger.warning("[EmailHook] SMTP 配置不完整，跳过发送")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((sender_name, sender_email))
    msg["To"] = to_email
    msg.attach(MIMEText(content, "html", "utf-8"))

    try:
        if smtp_ssl:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
            server.starttls()

        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        logger.error(f"[EmailHook] 发送邮件失败: to={to_email}, error={e}")
        return False


def _render_simple_template(event_type: str, context: Dict[str, Any]) -> tuple:
    """
    当没有匹配的邮件模板时，使用内置简单模板。

    Returns:
        (subject, content) 元组
    """
    event_label = EVENT_TYPE_LABELS.get(event_type, event_type)
    store_name = context.get("store_name", "")
    patient_name = context.get("patient_name", "")
    doctor_name = context.get("doctor_name", "")
    department_name = context.get("department_name", "")
    appointment_date = context.get("appointment_date", "")
    appointment_time = context.get("appointment_time", "")
    appointment_no = context.get("appointment_no", "")

    subject = f"[{store_name}] {event_label}通知"
    content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #1890ff;">{event_label}通知</h2>
        <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
            <tr><td style="padding: 8px; color: #666;">门店</td><td style="padding: 8px;">{store_name}</td></tr>
            <tr><td style="padding: 8px; color: #666;">预约编号</td><td style="padding: 8px;">{appointment_no}</td></tr>
            <tr><td style="padding: 8px; color: #666;">患者</td><td style="padding: 8px;">{patient_name}</td></tr>
            <tr><td style="padding: 8px; color: #666;">医生</td><td style="padding: 8px;">{doctor_name}</td></tr>
            <tr><td style="padding: 8px; color: #666;">科室</td><td style="padding: 8px;">{department_name}</td></tr>
            <tr><td style="padding: 8px; color: #666;">日期</td><td style="padding: 8px;">{appointment_date}</td></tr>
            <tr><td style="padding: 8px; color: #666;">时段</td><td style="padding: 8px;">{appointment_time}</td></tr>
        </table>
        <p style="color: #999; font-size: 12px;">此邮件由系统自动发送，请勿回复。</p>
    </div>
    """
    return subject, content


@celery_app.task(
    name="app.tasks.email_hook_task.process_event_email",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
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

            # 3. 查找匹配的邮件模板
            template_result = db.execute(
                select(EmailTemplate).where(
                    EmailTemplate.template_type == event_type,
                    EmailTemplate.status == 1,
                )
            )
            template = template_result.scalar_one_or_none()

            # 4. 渲染邮件内容
            if template:
                subject = template.subject_template
                content = template.content_template
                for key, value in context_data.items():
                    placeholder = "{{" + key + "}}"
                    subject = subject.replace(placeholder, str(value))
                    content = content.replace(placeholder, str(value))
            else:
                subject, content = _render_simple_template(event_type, context_data)

            # 5. 获取 SMTP 配置
            email_config = _get_email_config(db)

            # 6. 逐个发送
            sent_count = 0
            failed_count = 0
            logs = []
            for recipient in matched_recipients:
                success = _send_email_sync(email_config, recipient.email, subject, content)
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
