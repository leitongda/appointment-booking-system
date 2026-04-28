"""
通知重试任务
自动重试失败的通知，使用指数退避策略
"""
import logging
from datetime import datetime

from sqlalchemy import select, and_, update

from app.celery_app import celery_app
from app.db.session import get_sync_db
from app.models.notification_log import NotificationLog
from app.models.tenant import Tenant
from app.middleware.tenant_context import set_tenant_context, clear_tenant_context
from app.modules.notification_logs.service import calculate_next_retry

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.notification_retry_task.retry_failed_notifications",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=600,
    soft_time_limit=480,
)
def retry_failed_notifications():
    """
    扫描失败通知并重试

    - 每 5 分钟执行
    - 查询 status='failed' AND retry_count < max_retries AND next_retry_at <= now()
    - 按指数退避重试：1min -> 5min -> 30min
    - 更新 retry_count, next_retry_at, status
    """
    logger.info("[定时任务] 开始执行：失败通知重试")

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
        logger.info("没有活跃租户，跳过通知重试")
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

                # 查询待重试的失败通知
                result = db.execute(
                    select(NotificationLog).where(
                        and_(
                            NotificationLog.tenant_id == tenant.id,
                            NotificationLog.status == "failed",
                            NotificationLog.retry_count < NotificationLog.max_retries,
                            NotificationLog.next_retry_at <= now,
                        )
                    )
                )
                failed_logs = result.scalars().all()

                if not failed_logs:
                    continue

                logger.info(f"租户 {tenant.name} 找到 {len(failed_logs)} 条待重试通知")

                for log in failed_logs:
                    total_retried += 1

                    try:
                        # 根据渠道重新发送
                        success = _retry_by_channel(db, log)

                        if success:
                            # 重试成功
                            db.execute(
                                update(NotificationLog)
                                .where(NotificationLog.id == log.id)
                                .values(
                                    status="sent",
                                    sent_at=now,
                                )
                            )
                            total_success += 1
                            logger.info(
                                f"通知重试成功: id={log.id}, channel={log.channel}, "
                                f"type={log.message_type}, recipient={log.recipient}"
                            )
                        else:
                            # 重试失败，更新重试计数和下次重试时间
                            new_retry_count = log.retry_count + 1
                            next_retry = calculate_next_retry(new_retry_count)

                            if next_retry:
                                # 还有重试机会
                                db.execute(
                                    update(NotificationLog)
                                    .where(NotificationLog.id == log.id)
                                    .values(
                                        retry_count=new_retry_count,
                                        next_retry_at=next_retry,
                                    )
                                )
                                total_failed += 1
                                logger.warning(
                                    f"通知重试失败: id={log.id}, channel={log.channel}, "
                                    f"retry_count={new_retry_count}, next_retry_at={next_retry}"
                                )
                            else:
                                # 超过最大重试次数，标记为永久失败
                                db.execute(
                                    update(NotificationLog)
                                    .where(NotificationLog.id == log.id)
                                    .values(status="permanently_failed")
                                )
                                total_permanent_failed += 1
                                logger.error(
                                    f"通知重试失败，已达最大次数: id={log.id}, "
                                    f"channel={log.channel}, retry_count={new_retry_count}"
                                )
                    except Exception as e:
                        logger.error(f"重试通知异常: id={log.id}, error={e}")
                        total_failed += 1

                db.commit()

        except Exception as e:
            logger.error(f"租户 {tenant.name} 通知重试任务执行失败: {e}")
        finally:
            # 清除租户上下文
            clear_tenant_context()

    logger.info(
        f"[定时任务] 通知重试完成，尝试重试 {total_retried} 条，"
        f"成功 {total_success} 条，失败 {total_failed} 条，永久失败 {total_permanent_failed} 条"
    )

    return {
        "retried": total_retried,
        "success": total_success,
        "permanent_failed": total_permanent_failed,
        "failed": total_failed,
    }


def _retry_by_channel(db, log: NotificationLog) -> bool:
    """
    根据渠道重新发送通知

    Args:
        db: 同步数据库会话
        log: 通知日志记录

    Returns:
        是否发送成功
    """
    channel = log.channel

    if channel == "in_app":
        # 站内信重发通常无意义，直接标记失败
        logger.debug(f"站内信不支持重试: id={log.id}")
        return False

    elif channel == "sms":
        return _retry_sms(db, log)

    elif channel == "email":
        return _retry_email(db, log)

    elif channel == "wechat":
        return _retry_wechat(db, log)

    else:
        logger.warning(f"不支持的通知渠道: {channel}")
        return False


def _retry_sms(db, log: NotificationLog) -> bool:
    """重试短信发送"""
    try:
        # 导入短信服务
        from app.infrastructure.sms.factory import get_sms_provider

        # 尝试读取模板代码（从 extra_data 或根据 message_type 推断）
        extra_data = log.extra_data or {}
        template_code = extra_data.get("template_code")
        template_params = extra_data.get("template_params", {})

        if template_code:
            # 使用模板发送
            provider = get_sms_provider()
            if hasattr(provider, "send_business_notification"):
                import asyncio
                loop = asyncio.get_event_loop()
                success, _ = loop.run_until_complete(
                    provider.send_business_notification(
                        phone=log.recipient,
                        template_code=template_code,
                        template_params=template_params,
                    )
                )
                return success
        else:
            # 降级：使用简单通知方式（如果支持）
            provider = get_sms_provider()
            if hasattr(provider, "send_notification"):
                return provider.send_notification(log.recipient, log.content or "")

        return False
    except Exception as e:
        logger.error(f"短信重试失败: id={log.id}, error={e}")
        return False


def _retry_email(db, log: NotificationLog) -> bool:
    """重试邮件发送"""
    try:
        # 邮件服务需要异步会话，在 Celery 同步环境中无法直接使用
        # 这里记录日志，建议用户通过手动重试或其他方式处理
        logger.warning(
            f"邮件渠道暂不支持自动重试（需要异步环境）: "
            f"id={log.id}, recipient={log.recipient}"
        )
        return False
    except Exception as e:
        logger.error(f"邮件重试失败: id={log.id}, error={e}")
        return False


def _retry_wechat(db, log: NotificationLog) -> bool:
    """重试微信订阅消息发送"""
    try:
        from app.infrastructure.wechat.token_manager import WechatTokenManager
        from app.models.settings import SystemSetting
        from sqlalchemy import text
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
            logger.warning(f"微信配置不完整，跳过: id={log.id}")
            return False

        # 获取模板ID（从 extra_data）
        extra_data = log.extra_data or {}
        template_id = extra_data.get("template_id")

        if not template_id:
            # 尝试从 system_settings 读取
            template_key = f"{log.message_type}_template_id"
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
            logger.warning(f"微信模板未配置，跳过: id={log.id}")
            return False

        # 获取 access_token
        access_token = WechatTokenManager.get_access_token_sync(app_id, app_secret)

        # 构建消息数据
        template_data = extra_data.get("template_data", {})
        page = extra_data.get("page", "")

        url = f"https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={access_token}"
        payload = {
            "touser": log.recipient,
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
                f"微信消息发送失败: id={log.id}, errcode={result.get('errcode')}, "
                f"errmsg={result.get('errmsg')}"
            )
            return False

    except Exception as e:
        logger.error(f"微信重试失败: id={log.id}, error={e}")
        return False
