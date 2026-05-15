"""
统一消息中心投递重试任务

自动重试失败的 notification_deliveries，使用指数退避策略。
与 notification_retry_task.py 类似，但操作新表。
"""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import text

from app.celery_app import celery_app
from app.db.session import get_sync_db
from app.models.tenant import Tenant
from app.middleware.tenant_context import set_tenant_context, clear_tenant_context
from app.infrastructure.notifications.metrics import record_retry

logger = logging.getLogger(__name__)

# 指数退避配置（秒）
RETRY_INTERVALS = [60, 300, 1800, 7200, 18000]  # 1min, 5min, 30min, 2h, 5h
MAX_RETRIES = len(RETRY_INTERVALS)


def calculate_next_retry(retry_count: int) -> Optional[datetime]:
    """计算下次重试时间（指数退避）"""
    if retry_count >= MAX_RETRIES:
        return None
    from datetime import timedelta
    return datetime.utcnow() + timedelta(seconds=RETRY_INTERVALS[retry_count])


@celery_app.task(
    name="app.tasks.unified_message_retry_task.retry_failed_deliveries",
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
    扫描失败的投递记录并重试

    - 每 5 分钟执行
    - 查询 status='failed' AND retry_count < max_retries AND next_retry_at <= now()
    - 按指数退避重试：1min -> 5min -> 30min -> 2h -> 5h
    - 更新 retry_count, next_retry_at, status
    """
    logger.info("[定时任务] 开始执行：统一消息投递重试")

    total_retried = 0
    total_success = 0
    total_permanent_failed = 0
    total_failed = 0

    # 第一步：查询所有活跃租户
    with get_sync_db() as db:
        try:
            result = db.execute(
                select(Tenant).where(Tenant.status.in_([1, 3]))  # 正常或试用状态
            )
            tenants = result.scalars().all()
        except Exception as e:
            logger.error(f"查询租户列表失败: {e}")
            return {
                "retried": 0,
                "success": 0,
                "permanent_failed": 0,
                "failed": 0,
                "reason": "查询租户失败"
            }

    if not tenants:
        logger.info("没有活跃租户，跳过投递重试")
        return {"retried": 0, "success": 0, "permanent_failed": 0, "failed": 0}

    logger.info(f"找到 {len(tenants)} 个活跃租户")

    # 第二步：遍历每个租户
    for tenant in tenants:
        logger.debug(f"处理租户: {tenant.name}({tenant.tenant_code}), id={tenant.id}")

        # 设置当前租户上下文
        set_tenant_context(tenant.id, tenant.tenant_code)

        try:
            with get_sync_db() as db:
                now = datetime.utcnow()

                # 查询待重试的失败投递记录
                result = db.execute(
                    text("""
                        SELECT id, group_id, recipient_id, tenant_id,
                               channel, status, recipient_address,
                               error_message, retry_count, max_retries,
                               next_retry_at, extra_data
                        FROM notification_deliveries
                        WHERE tenant_id = :tenant_id
                          AND status = 'failed'
                          AND retry_count < max_retries
                          AND next_retry_at <= :now
                    """),
                    {"tenant_id": tenant.id, "now": now},
                )
                failed_deliveries = result.fetchall()

                if not failed_deliveries:
                    continue

                logger.info(f"租户 {tenant.name} 找到 {len(failed_deliveries)} 条待重试投递")

                for delivery in failed_deliveries:
                    total_retried += 1
                    delivery_id = delivery[0]
                    channel = delivery[4]
                    recipient_address = delivery[6]
                    retry_count = delivery[8]
                    extra_data = delivery[11] or {}

                    try:
                        # 根据渠道重新发送
                        success = _retry_delivery(db, channel, recipient_address, extra_data)
                        record_retry(channel, success)

                        if success:
                            # 重试成功
                            db.execute(
                                text("""
                                    UPDATE notification_deliveries
                                    SET status = 'sent', sent_at = :now, error_message = NULL
                                    WHERE id = :id
                                """),
                                {"id": delivery_id, "now": now},
                            )
                            total_success += 1
                            logger.info(
                                f"投递重试成功: id={delivery_id}, channel={channel}, "
                                f"recipient={recipient_address}"
                            )
                        else:
                            # 重试失败，更新重试计数和下次重试时间
                            new_retry_count = retry_count + 1
                            next_retry = calculate_next_retry(new_retry_count)

                            if next_retry:
                                # 还有重试机会
                                db.execute(
                                    text("""
                                        UPDATE notification_deliveries
                                        SET retry_count = :retry_count, next_retry_at = :next_retry_at
                                        WHERE id = :id
                                    """),
                                    {"id": delivery_id, "retry_count": new_retry_count, "next_retry_at": next_retry},
                                )
                                total_failed += 1
                                logger.warning(
                                    f"投递重试失败: id={delivery_id}, channel={channel}, "
                                    f"retry_count={new_retry_count}, next_retry_at={next_retry}"
                                )
                            else:
                                # 超过最大重试次数，标记为永久失败
                                db.execute(
                                    text("UPDATE notification_deliveries SET status = 'permanently_failed' WHERE id = :id"),
                                    {"id": delivery_id},
                                )
                                total_permanent_failed += 1
                                logger.error(
                                    f"投递重试失败，已达最大次数: id={delivery_id}, "
                                    f"channel={channel}, retry_count={new_retry_count}"
                                )
                    except Exception as e:
                        logger.error(f"重试投递异常: id={delivery_id}, error={e}")
                        total_failed += 1

                db.commit()

        except Exception as e:
            logger.error(f"租户 {tenant.name} 投递重试任务执行失败: {e}")
        finally:
            # 清除租户上下文
            clear_tenant_context()

    logger.info(
        f"[定时任务] 投递重试完成，尝试重试 {total_retried} 条，"
        f"成功 {total_success} 条，失败 {total_failed} 条，永久失败 {total_permanent_failed} 条"
    )

    return {
        "retried": total_retried,
        "success": total_success,
        "permanent_failed": total_permanent_failed,
        "failed": total_failed,
    }


def _retry_delivery(db, channel: str, recipient_address: str, extra_data: dict) -> bool:
    """
    根据渠道重新发送投递

    Args:
        db: 同步数据库会话
        channel: 渠道类型
        recipient_address: 接收地址
        extra_data: 额外数据

    Returns:
        是否发送成功
    """
    if channel == "in_app" or channel == "websocket":
        # 站内信和 WebSocket 重发通常无意义
        logger.debug(f"渠道 {channel} 不支持重试")
        return False

    elif channel == "sms":
        return _retry_sms(recipient_address, extra_data)

    elif channel == "email":
        return _retry_email(recipient_address, extra_data)

    elif channel == "wechat" or channel == "wechat_subscribe":
        return _retry_wechat(db, recipient_address, extra_data)

    else:
        logger.warning(f"不支持的通知渠道: {channel}")
        return False


def _retry_sms(phone: str, extra_data: dict) -> bool:
    """重试短信发送"""
    try:
        from app.infrastructure.sms.factory import get_sms_provider

        template_code = extra_data.get("template_code")
        template_params = extra_data.get("template_params", {})

        if template_code:
            provider = get_sms_provider()
            if hasattr(provider, "send_business_notification"):
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 如果事件循环已在运行，使用 new_loop
                        new_loop = asyncio.new_event_loop()
                        try:
                            success, _ = new_loop.run_until_complete(
                                provider.send_business_notification(
                                    phone=phone,
                                    template_code=template_code,
                                    template_params=template_params,
                                )
                            )
                            return success
                        finally:
                            new_loop.close()
                    else:
                        success, _ = loop.run_until_complete(
                            provider.send_business_notification(
                                phone=phone,
                                template_code=template_code,
                                template_params=template_params,
                            )
                        )
                        return success
                except RuntimeError:
                    # 回退方式
                    success, _ = asyncio.run(
                        provider.send_business_notification(
                            phone=phone,
                            template_code=template_code,
                            template_params=template_params,
                        )
                    )
                    return success

        return False
    except Exception as e:
        logger.error(f"短信重试失败: phone={phone}, error={e}")
        return False


def _retry_email(email: str, extra_data: dict) -> bool:
    """重试邮件发送（使用同步 SMTP）"""
    try:
        from app.utils.email_sync import get_email_config, send_email_sync
        from app.db.session import get_sync_db

        with get_sync_db() as db:
            config = get_email_config(db)
        if not config:
            logger.warning(f"邮件重试失败: 无法获取 SMTP 配置, email={email}")
            return False

        subject = extra_data.get("subject", "")
        content = extra_data.get("content", "")
        return send_email_sync(config, email, subject, content)
    except Exception as e:
        logger.error(f"邮件重试失败: email={email}, error={e}")
        return False


def _retry_wechat(db, openid: str, extra_data: dict) -> bool:
    """重试微信订阅消息发送"""
    try:
        from app.infrastructure.wechat.token_manager import WechatTokenManager
        from app.models.settings import SystemSetting
        from sqlalchemy import select, and_
        import httpx

        # 获取微信配置
        result = db.execute(
            select(SystemSetting).where(
                SystemSetting.category == 'wechat'
            )
        )
        settings_list = result.scalars().all()
        config = {}
        for s in settings_list:
            config[s.key] = s.value

        app_id = config.get('app_id')
        app_secret = config.get('app_secret')

        if not app_id or not app_secret:
            logger.warning(f"微信配置不完整，跳过: openid={openid}")
            return False

        # 获取模板ID
        template_id = extra_data.get("template_id")
        if not template_id:
            # 尝试从 system_settings 读取
            message_type = extra_data.get("message_type", "system")
            template_key = f"{message_type}_template_id"
            template_result = db.execute(
                select(SystemSetting).where(
                    and_(
                        SystemSetting.category == 'wechat',
                        SystemSetting.key == template_key
                    )
                )
            )
            template_setting = template_result.scalar_one_or_none()
            if template_setting:
                template_id = template_setting.value

        if not template_id:
            logger.warning(f"微信模板未配置，跳过: openid={openid}")
            return False

        # 获取 access_token
        access_token = WechatTokenManager.get_access_token_sync(app_id, app_secret)

        # 构建消息数据
        template_data = extra_data.get("template_data", {})
        page = extra_data.get("page", "")

        url = f"https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={access_token}"
        payload = {
            "touser": openid,
            "template_id": template_id,
            "data": template_data
        }
        if page:
            payload["page"] = page

        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload)
            result = response.json()

        if result.get("errcode", 0) == 0:
            return True
        else:
            logger.warning(
                f"微信消息发送失败: openid={openid}, errcode={result.get('errcode')}, "
                f"errmsg={result.get('errmsg')}"
            )
            return False

    except Exception as e:
        logger.error(f"微信重试失败: openid={openid}, error={e}")
        return False
