"""
统一通知系统重试任务

自动重试 notification_deliveries 表中失败的通知，
使用指数退避策略（1min -> 5min -> 30min）。
"""

import asyncio
import logging
from datetime import datetime

from sqlalchemy import and_, select, update

from app.celery_app import celery_app
from app.db.session import get_sync_db
from app.modules.unified_message.models import NotificationDelivery

logger = logging.getLogger(__name__)

# 指数退避延迟（分钟）
RETRY_DELAYS = [1, 5, 30]


def calculate_next_retry(retry_count: int):
    """计算下次重试时间"""
    if retry_count >= len(RETRY_DELAYS):
        return None
    from datetime import timedelta
    return datetime.utcnow() + timedelta(minutes=RETRY_DELAYS[retry_count])


@celery_app.task(
    name="app.tasks.unified_notification_retry_task.retry_failed_deliveries",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=600,
    soft_time_limit=480,
)
def retry_failed_deliveries():
    """
    扫描失败的 notification_delivery 记录并重试。

    - 每 5 分钟执行
    - 查询 status='failed' AND retry_count < max_retries AND next_retry_at <= now()
    - 按渠道重试发送
    """
    logger.info("[定时任务] 开始执行：统一通知重试")

    total_retried = 0
    total_success = 0
    total_permanent_failed = 0

    with get_sync_db() as db:
        try:
            now = datetime.utcnow()

            # 查询待重试的投递记录
            result = db.execute(
                select(NotificationDelivery).where(
                    and_(
                        NotificationDelivery.status == "failed",
                        NotificationDelivery.retry_count < NotificationDelivery.max_retries,
                        NotificationDelivery.next_retry_at <= now,
                    )
                )
            )
            deliveries = result.scalars().all()

            if not deliveries:
                logger.info("没有待重试的通知")
                return {"retried": 0, "success": 0, "permanent_failed": 0}

            logger.info(f"找到 {len(deliveries)} 条待重试通知")

            for delivery in deliveries:
                total_retried += 1

                try:
                    success = _retry_delivery(delivery)

                    if success:
                        db.execute(
                            update(NotificationDelivery)
                            .where(NotificationDelivery.id == delivery.id)
                            .values(status="sent", sent_at=now)
                        )
                        total_success += 1
                        logger.info(
                            f"通知重试成功: id={delivery.id}, channel={delivery.channel}"
                        )
                    else:
                        new_retry_count = delivery.retry_count + 1
                        next_retry = calculate_next_retry(new_retry_count)

                        if next_retry:
                            db.execute(
                                update(NotificationDelivery)
                                .where(NotificationDelivery.id == delivery.id)
                                .values(
                                    retry_count=new_retry_count,
                                    next_retry_at=next_retry,
                                )
                            )
                            logger.warning(
                                f"通知重试失败: id={delivery.id}, retry_count={new_retry_count}"
                            )
                        else:
                            db.execute(
                                update(NotificationDelivery)
                                .where(NotificationDelivery.id == delivery.id)
                                .values(status="permanently_failed")
                            )
                            total_permanent_failed += 1
                            logger.error(
                                f"通知重试失败，已达最大次数: id={delivery.id}"
                            )
                except Exception as e:
                    logger.error(f"重试通知异常: id={delivery.id}, error={e}")

            db.commit()

        except Exception as e:
            logger.error(f"统一通知重试任务异常: {e}")
            db.rollback()

    result = {
        "retried": total_retried,
        "success": total_success,
        "permanent_failed": total_permanent_failed,
    }
    logger.info(f"[定时任务] 统一通知重试完成: {result}")
    return result


def _retry_delivery(delivery: NotificationDelivery) -> bool:
    """根据渠道重试发送"""
    channel = delivery.channel

    if channel == "sms":
        return _retry_sms(delivery)
    elif channel == "email":
        return _retry_email(delivery)
    elif channel == "wechat":
        return _retry_wechat(delivery)
    else:
        # in_app / websocket 不需要重试
        logger.debug(f"渠道 {channel} 不支持重试, id={delivery.id}")
        return False


def _retry_sms(delivery: NotificationDelivery) -> bool:
    """重试短信发送"""
    try:
        from app.infrastructure.sms.factory import get_sms_provider

        provider = get_sms_provider()
        content = delivery.content or ""
        recipient = delivery.recipient_address

        if not recipient:
            logger.warning(f"短信重试缺少手机号: id={delivery.id}")
            return False

        # 尝试发送
        if hasattr(provider, "send_business_notification"):
            result = asyncio.get_event_loop().run_until_complete(
                provider.send_business_notification(recipient, content)
            )
        else:
            result = asyncio.get_event_loop().run_until_complete(
                provider.send_notification(recipient, content)
            )

        return bool(result)
    except Exception as e:
        logger.error(f"短信重试异常: id={delivery.id}, error={e}")
        return False


def _retry_email(delivery: NotificationDelivery) -> bool:
    """重试邮件发送"""
    try:
        from app.utils.email_sync import send_email_sync

        recipient = delivery.recipient_address
        title = delivery.title or "通知"
        content = delivery.content or ""

        if not recipient:
            logger.warning(f"邮件重试缺少邮箱: id={delivery.id}")
            return False

        send_email_sync(recipient, title, content)
        return True
    except Exception as e:
        logger.error(f"邮件重试异常: id={delivery.id}, error={e}")
        return False


def _retry_wechat(delivery: NotificationDelivery) -> bool:
    """重试微信模板消息发送"""
    try:
        import json

        from app.infrastructure.wechat.token_manager import get_wechat_token

        extra_data = {}
        if delivery.extra_data:
            try:
                extra_data = json.loads(delivery.extra_data)
            except (json.JSONDecodeError, TypeError):
                pass

        template_id = extra_data.get("template_id")
        template_data = extra_data.get("template_data")
        page = extra_data.get("page", "")
        openid = delivery.recipient_address

        if not openid or not template_id or not template_data:
            logger.warning(f"微信重试缺少必要参数: id={delivery.id}")
            return False

        token = asyncio.get_event_loop().run_until_complete(get_wechat_token())

        import httpx

        url = f"https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={token}"
        payload = {
            "touser": openid,
            "template_id": template_id,
            "data": template_data,
        }
        if page:
            payload["page"] = page

        resp = httpx.post(url, json=payload, timeout=10)
        data = resp.json()

        if data.get("errcode") == 0:
            return True

        logger.warning(f"微信重试失败: id={delivery.id}, response={data}")
        return False
    except Exception as e:
        logger.error(f"微信重试异常: id={delivery.id}, error={e}")
        return False
