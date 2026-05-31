"""
通知相关定时任务
- 预约提醒（就诊前发送微信消息/短信/站内信）
- 三级提醒策略：24h(微信) / 2h(短信) / 30min(站内信+WebSocket)
- 并行化：按租户并行派发子任务
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from sqlalchemy import select, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, joinedload
import logging

from app.celery_app import celery_app
from app.db.session import get_sync_db
from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.user import User
from app.models.doctor import Doctor
from app.models.department import Department
from app.models.message import Message, MessageType
from app.models.notification_log import NotificationLog
from app.models.settings import SystemSetting as Settings
from app.models.tenant import Tenant
from app.core.config import settings as app_settings
from app.enums.general import ReminderLevel  # noqa: F401 — re-export
from app.infrastructure.wechat.service import WechatService
from app.infrastructure.wechat.token_manager import WechatTokenManager
from app.middleware.tenant_context import set_tenant_context, clear_tenant_context
from app.modules.settings.service import SettingsService
from app.common.sync_account_helper import (
    get_account_phone,
    get_account_openid,
    get_user_info_for_reminder,
)
from celery import group
import httpx
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class ReminderConfig:
    """提醒配置"""
    level: ReminderLevel
    hours_before: int
    minutes_before: int = 0
    channel: str = "wechat"
    requires_openid: bool = True
    requires_phone: bool = False


# 三级提醒配置
REMINDER_CONFIGS: Dict[ReminderLevel, ReminderConfig] = {
    ReminderLevel.LEVEL_24H: ReminderConfig(
        level=ReminderLevel.LEVEL_24H,
        hours_before=24,
        channel="wechat",
        requires_openid=True,
    ),
    ReminderLevel.LEVEL_2H: ReminderConfig(
        level=ReminderLevel.LEVEL_2H,
        hours_before=2,
        channel="sms",
        requires_openid=False,
        requires_phone=True,
    ),
    ReminderLevel.LEVEL_30MIN: ReminderConfig(
        level=ReminderLevel.LEVEL_30MIN,
        hours_before=0,
        minutes_before=30,
        channel="in_app",
        requires_openid=False,
        requires_phone=False,
    ),
}


def _get_wechat_config(db: Session) -> dict:
    """从数据库获取微信配置"""
    try:
        result = db.execute(
            select(Settings).where(Settings.category == 'wechat')
        )
        settings_list = result.scalars().all()
        config = {}
        for s in settings_list:
            config[s.key] = s.value
        return config
    except Exception as e:
        logger.error(f"获取微信配置失败: {e}")
        return {}


def _get_appointment_reminder_template_id(db: Session) -> str:
    """获取预约提醒消息模板 ID"""
    try:
        result = db.execute(
            select(Settings).where(
                and_(
                    Settings.category == 'wechat',
                    Settings.key == 'appointment_reminder_template_id'
                )
            )
        )
        setting = result.scalar_one_or_none()
        return setting.value if setting else ""
    except Exception:
        return ""


def _send_wechat_subscribe_message(
    access_token: str,
    openid: str,
    template_id: str,
    data: dict,
    page: str = None
) -> bool:
    """发送微信订阅消息（同步版本）"""
    url = f"https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={access_token}"

    payload = {
        "touser": openid,
        "template_id": template_id,
        "data": data
    }
    if page:
        payload["page"] = page

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload)
            result = response.json()

        if result.get("errcode", 0) != 0:
            logger.warning(f"发送微信消息失败: {result.get('errmsg')}")
            return False
        return True
    except Exception as e:
        logger.error(f"发送微信消息异常: {e}")
        return False


def _send_sms_reminder(
    db: Session,
    tenant_id: str,
    phone: str,
    patient_name: str,
    doctor_name: str,
    appointment_time: str,
    user_id: Optional[str] = None,
    store_id: Optional[str] = None,
    appointment_id: Optional[str] = None,
) -> bool:
    """发送短信提醒（同步版本）

    如果传入的 phone 为空，尝试从 Account 表获取手机号 fallback。
    """
    # Account 表优先获取手机号 fallback
    if not phone and user_id:
        phone = get_account_phone(db, user_id, "user") or ""

    if not phone:
        logger.warning(f"无法获取手机号，跳过短信发送: user_id={user_id}, appointment_id={appointment_id}")
        return False

    try:
        from app.infrastructure.sms.service import SmsService

        # 使用 run_coroutine_threadsafe 在同步上下文中运行异步方法
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success = loop.run_until_complete(
                SmsService.send_appointment_reminder(
                    tenant_id=tenant_id,
                    phone=phone,
                    variables={
                        "patient_name": patient_name,
                        "doctor": doctor_name,
                        "time": appointment_time,
                    },
                    user_id=user_id,
                    store_id=store_id,
                    appointment_id=appointment_id,
                )
            )
        finally:
            loop.close()

        return success
    except Exception as e:
        logger.error(f"发送短信提醒异常: {e}")
        return False


def _create_in_app_message(
    db: Session,
    tenant_id: str,
    user_id: str,
    title: str,
    content: str,
    message_type: str = MessageType.APPOINTMENT.value,
    related_id: Optional[str] = None,
    store_id: Optional[str] = None,
) -> bool:
    """创建站内信（同步版本）"""
    try:
        message = Message(
            tenant_id=tenant_id,
            store_id=store_id,
            user_id=user_id,
            user_type="patient",
            title=title,
            content=content,
            message_type=message_type,
            related_id=related_id,
            is_read=0,
        )
        db.add(message)
        db.flush()
        return True
    except Exception as e:
        logger.error(f"创建站内信失败: {e}")
        return False


def _send_websocket_notification(
    doctor_id: str,
    message_type: str,
    data: Dict[str, Any],
):
    """发送 WebSocket 通知（同步版本）"""
    try:
        from app.core.websocket import WSMessage

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            from app.core.websocket import ws_manager
            # 同步任务中不需要实际发送 WebSocket，因为这是给患者看的
            # WebSocket 主要用于医生端
            pass
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"发送 WebSocket 通知异常: {e}")


def _should_use_unified(tenant_id: str) -> bool:
    """检查租户是否启用了统一消息中心"""
    try:
        from app.db.session import async_session_maker
        from app.common.feature_flags import FeatureFlagService

        async def _check():
            async with async_session_maker() as session:
                return await FeatureFlagService.is_beta_enabled(
                    session, tenant_id, "beta_unified_message"
                )

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_check())
        finally:
            loop.close()
    except Exception:
        return False


def _send_via_unified(
    tenant_id: str,
    store_id: Optional[str],
    recipient_id: str,
    recipient_type: str,
    recipient_phone: Optional[str],
    recipient_openid: Optional[str],
    template_code: str,
    message_type: str,
    title: str,
    content: str,
    related_id: Optional[str] = None,
    channels: Optional[list] = None,
) -> bool:
    """通过 UnifiedMessageService 发送通知（同步桥接）"""
    try:
        from app.db.session import async_session_maker
        from app.modules.unified_message.service import UnifiedMessageService
        from app.modules.unified_message.schemas import NotificationEvent

        event = NotificationEvent(
            tenant_id=tenant_id,
            store_id=store_id,
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            recipient_phone=recipient_phone,
            recipient_openid=recipient_openid,
            template_code=template_code,
            variables={},
            message_type=message_type,
            related_id=related_id,
            title=title,
            content=content,
            channels=channels,
        )

        async def _send():
            async with async_session_maker() as session:
                service = UnifiedMessageService(session)
                result = await service.send(event)
                return result.success

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_send())
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"[统一消息] 发送失败: {e}", exc_info=True)
        return False


def _query_appointments_needing_reminder(
    db: Session,
    tenant_id: str,
    reminder_config: ReminderConfig,
) -> List[tuple]:
    """
    查询需要提醒的预约（优化版本：使用 joinedload 预加载）

    Returns:
        List[(Appointment, Schedule, User, Doctor)]
    """
    now = datetime.now()

    if reminder_config.minutes_before > 0:
        # 分钟级别提醒
        reminder_start = now
        reminder_end = now + timedelta(minutes=reminder_config.minutes_before)
    else:
        # 小时级别提醒
        reminder_start = now
        reminder_end = now + timedelta(hours=reminder_config.hours_before)

    # 确定查询字段
    if reminder_config.level == ReminderLevel.LEVEL_24H:
        reminder_field = Appointment.reminder_sent_24h
    elif reminder_config.level == ReminderLevel.LEVEL_2H:
        reminder_field = Appointment.reminder_sent_2h
    else:  # LEVEL_30MIN
        reminder_field = Appointment.reminder_sent_30min

    # 构建查询（使用 joinedload 预加载关联数据）
    query = (
        select(Appointment)
        .options(
            joinedload(Appointment.schedule),
            joinedload(Appointment.user),
            joinedload(Appointment.doctor),
        )
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(User, Appointment.user_id == User.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
        .where(
            and_(
                Appointment.tenant_id == tenant_id,
                Appointment.status == 1,  # 待就诊
                reminder_field == 0,  # 未发送该级别提醒
                # 就诊日期时间在提醒范围内
                Schedule.schedule_date >= reminder_start.date(),
                Schedule.schedule_date <= reminder_end.date()
            )
        )
    )

    # 执行查询
    result = db.execute(query)
    appointments = result.scalars().unique().all()

    # 过滤精确时间范围并构建元组列表
    qualified = []
    for apt in appointments:
        appointment_datetime = datetime.combine(
            apt.schedule.schedule_date,
            apt.schedule.start_time
        )

        # 精确时间检查
        if reminder_start <= appointment_datetime <= reminder_end:
            # 根据渠道要求过滤
            if reminder_config.requires_openid:
                # 先检查旧表 user.openid，如果为空则尝试 Account 表 fallback
                openid = apt.user.openid
                if not openid:
                    openid = get_account_openid(db, apt.user.id, "user")
                if not openid:
                    continue
            if reminder_config.requires_phone and not apt.patient_phone:
                continue
            qualified.append((apt, apt.schedule, apt.user, apt.doctor))

    return qualified


def _send_reminder_for_level(
    db: Session,
    tenant_id: str,
    tenant_name: str,
    reminder_config: ReminderConfig,
    wechat_access_token: Optional[str] = None,
    wechat_template_id: Optional[str] = None,
) -> Dict[str, int]:
    """
    为单个级别发送提醒

    Returns:
        {"sent": int, "failed": int}
    """
    sent_count = 0
    failed_count = 0
    now = datetime.now()

    # 查询需要提醒的预约
    appointments_to_remind = _query_appointments_needing_reminder(
        db, tenant_id, reminder_config
    )

    if not appointments_to_remind:
        logger.debug(f"租户 {tenant_name} 没有需要 {reminder_config.level.value} 级别提醒的预约")
        return {"sent": 0, "failed": 0}

    logger.info(
        f"租户 {tenant_name} {reminder_config.level.value} 级别提醒: "
        f"找到 {len(appointments_to_remind)} 个待提醒预约"
    )

    # 检查是否使用统一消息中心
    use_unified = _should_use_unified(tenant_id)

    for appointment, schedule, user, doctor in appointments_to_remind:
        success = False
        error_msg = None

        appointment_datetime = datetime.combine(
            schedule.schedule_date,
            schedule.start_time
        )
        time_str = appointment_datetime.strftime("%Y年%m月%d日 %H:%M")

        try:
            if use_unified:
                # 统一消息路径：通过 UnifiedMessageService 发送
                openid = user.openid or get_account_openid(db, user.id, "user")
                phone = appointment.patient_phone or get_account_phone(db, user.id, "user")
                title = f"预约提醒({reminder_config.level.value})"
                content = f"您预约的 {doctor.name or '医生'} 医生将于 {time_str} 就诊，请准时到达。"

                success = _send_via_unified(
                    tenant_id=tenant_id,
                    store_id=appointment.store_id,
                    recipient_id=user.id,
                    recipient_type="patient",
                    recipient_phone=phone,
                    recipient_openid=openid,
                    template_code=f"appointment_reminder_{reminder_config.level.value}",
                    message_type="appointment",
                    title=title,
                    content=content,
                    related_id=appointment.id,
                    channels=[reminder_config.channel],
                )
                if not success:
                    error_msg = f"统一消息发送失败({reminder_config.channel})"

            elif reminder_config.channel == "wechat":
                # 24h 级别：微信订阅消息
                if not wechat_access_token or not wechat_template_id:
                    error_msg = "微信配置不完整"
                else:
                    # 获取 openid：旧表优先，Account 表 fallback
                    openid = user.openid or get_account_openid(db, user.id, "user")
                    if not openid:
                        error_msg = "用户无 openid"
                        failed_count += 1
                        logger.warning(
                            f"发送 {reminder_config.level.value} 提醒失败: "
                            f"appointment_id={appointment.id}, error={error_msg}"
                        )
                        continue
                    message_data = {
                        "thing1": {"value": doctor.name[:20] if doctor.name else "医生"},
                        "time2": {"value": time_str},
                        "thing3": {"value": schedule.time_slot or ""},
                    }
                    success = _send_wechat_subscribe_message(
                        access_token=wechat_access_token,
                        openid=openid,
                        template_id=wechat_template_id,
                        data=message_data,
                        page=f"pages/appointment/detail?id={appointment.id}"
                    )
                    if not success:
                        error_msg = "微信推送失败"

            elif reminder_config.channel == "sms":
                # 2h 级别：短信
                success = _send_sms_reminder(
                    db=db,
                    tenant_id=tenant_id,
                    phone=appointment.patient_phone,
                    patient_name=appointment.patient_name or "",
                    doctor_name=doctor.name or "",
                    appointment_time=time_str,
                    user_id=user.id,
                    store_id=appointment.store_id,
                    appointment_id=appointment.id,
                )
                if not success:
                    error_msg = "短信发送失败"

            elif reminder_config.channel == "in_app":
                # 30min 级别：站内信
                title = "就诊提醒"
                content = (
                    f"您预约的 {doctor.name or '医生'} 医生 "
                    f"将于 {time_str} 就诊，请准时到达。"
                )
                success = _create_in_app_message(
                    db=db,
                    tenant_id=tenant_id,
                    user_id=user.id,
                    title=title,
                    content=content,
                    message_type=MessageType.APPOINTMENT.value,
                    related_id=appointment.id,
                    store_id=appointment.store_id,
                )
                if not success:
                    error_msg = "创建站内信失败"

            # 更新提醒状态
            if success:
                if reminder_config.level == ReminderLevel.LEVEL_24H:
                    appointment.reminder_sent_24h = 1
                    # 兼容旧字段
                    appointment.reminder_sent = 1
                    appointment.reminder_sent_at = now
                elif reminder_config.level == ReminderLevel.LEVEL_2H:
                    appointment.reminder_sent_2h = 1
                else:  # LEVEL_30MIN
                    appointment.reminder_sent_30min = 1

                sent_count += 1
                logger.info(
                    f"发送 {reminder_config.level.value} 提醒成功: "
                    f"appointment_id={appointment.id}, channel={reminder_config.channel}"
                )
            else:
                failed_count += 1
                logger.warning(
                    f"发送 {reminder_config.level.value} 提醒失败: "
                    f"appointment_id={appointment.id}, error={error_msg}"
                )

            # 记录 NotificationLog（统一消息路径已由 UnifiedMessageService 记录，跳过）
            if not use_unified:
                log = NotificationLog(
                    tenant_id=tenant_id,
                    store_id=appointment.store_id,
                    user_id=user.id,
                    user_type="patient",
                    channel=reminder_config.channel,
                    message_type=f"appointment_reminder_{reminder_config.level.value}",
                    title=f"预约提醒({reminder_config.level.value})",
                    content=f"就诊时间: {time_str}",
                    status="sent" if success else "failed",
                    recipient=user.openid or appointment.patient_phone or user.id,
                    related_id=appointment.id,
                    sent_at=now if success else None,
                    error_message=error_msg,
                )
                db.add(log)

        except Exception as e:
            failed_count += 1
            logger.error(
                f"处理 {reminder_config.level.value} 提醒异常: "
                f"appointment_id={appointment.id}, error={e}"
            )

    return {"sent": sent_count, "failed": failed_count}


@celery_app.task(
    name="app.tasks.notification_task.send_appointment_reminder_for_tenant",
    bind=True,
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=600,
    soft_time_limit=480,
)
def send_appointment_reminder_for_tenant(self, tenant_id: str, tenant_code: str):
    """
    处理单个租户的提醒发送（子任务）

    Args:
        tenant_id: 租户 ID
        tenant_code: 租户编码

    Returns:
        Dict with statistics
    """
    import time
    start_time = time.time()

    logger.info(f"[子任务] 开始处理租户提醒: tenant_id={tenant_id}, tenant_code={tenant_code}")

    # 设置租户上下文
    set_tenant_context(tenant_id, tenant_code)

    total_sent = 0
    total_failed = 0
    tenant_name = tenant_code

    try:
        with get_sync_db() as db:
            # 获取租户信息
            tenant = db.execute(
                select(Tenant).where(Tenant.id == tenant_id)
            ).scalar_one_or_none()
            if tenant:
                tenant_name = tenant.name

            # 获取微信配置（24h 级别需要）
            wechat_access_token = None
            wechat_template_id = None

            wechat_config = _get_wechat_config(db)
            app_id = wechat_config.get('app_id') or app_settings.WECHAT_APP_ID
            app_secret = wechat_config.get('app_secret') or app_settings.WECHAT_APP_SECRET

            if app_id and app_secret:
                try:
                    wechat_access_token = WechatTokenManager.get_access_token_sync(
                        app_id, app_secret
                    )
                    wechat_template_id = _get_appointment_reminder_template_id(db)
                except Exception as e:
                    logger.warning(f"获取微信配置失败: {e}")

            # 按优先级处理三个级别
            # 24h -> 2h -> 30min
            for level_config in [
                REMINDER_CONFIGS[ReminderLevel.LEVEL_24H],
                REMINDER_CONFIGS[ReminderLevel.LEVEL_2H],
                REMINDER_CONFIGS[ReminderLevel.LEVEL_30MIN],
            ]:
                try:
                    result = _send_reminder_for_level(
                        db=db,
                        tenant_id=tenant_id,
                        tenant_name=tenant_name,
                        reminder_config=level_config,
                        wechat_access_token=wechat_access_token,
                        wechat_template_id=wechat_template_id,
                    )
                    total_sent += result["sent"]
                    total_failed += result["failed"]
                except Exception as e:
                    logger.error(f"处理 {level_config.level.value} 级别提醒失败: {e}")
                    total_failed += 1

            db.commit()

    except Exception as e:
        logger.error(f"租户 {tenant_name} 提醒任务执行失败: {e}")
        # 重试
        try:
            raise self.retry(exc=e, countdown=60)
        except Exception:
            pass
    finally:
        # 清除租户上下文
        clear_tenant_context()

    elapsed_time = time.time() - start_time

    # 监控：执行时间超过 60 秒记录 WARNING
    if elapsed_time > 60:
        logger.warning(
            f"[子任务] 租户 {tenant_name} 提醒任务执行时间过长: "
            f"{elapsed_time:.2f}秒"
        )

    logger.info(
        f"[子任务] 租户 {tenant_name} 提醒完成: "
        f"成功 {total_sent} 条, 失败 {total_failed} 条, "
        f"耗时 {elapsed_time:.2f}秒"
    )

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "sent": total_sent,
        "failed": total_failed,
        "elapsed_time": elapsed_time,
    }


@celery_app.task(
    name="app.tasks.notification_task.send_appointment_reminder_scheduler",
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=600,
    soft_time_limit=480,
)
def send_appointment_reminder_scheduler():
    """
    预约提醒调度器（主任务）
    每10分钟执行一次

    功能：
    1. 扫描所有活跃租户
    2. 使用 Celery group 并行派发子任务
    3. 聚合结果并记录统计信息
    """
    import time
    start_time = time.time()

    logger.info("[调度器] 开始执行预约提醒调度")

    # 查询所有活跃租户
    with get_sync_db() as db:
        try:
            result = db.execute(
                select(Tenant).where(
                    and_(
                        Tenant.status.in_([1, 3]),  # 正常或试用状态
                        Tenant.deleted_at.is_(None),  # 未软删除
                    )
                )
            )
            tenants = result.scalars().all()
        except Exception as e:
            logger.error(f"查询租户列表失败: {e}")
            return {
                "sent_count": 0,
                "failed_count": 0,
                "tenant_count": 0,
                "reason": "查询租户失败"
            }

    if not tenants:
        logger.info("[调度器] 没有活跃租户，跳过预约提醒")
        return {
            "sent_count": 0,
            "failed_count": 0,
            "tenant_count": 0,
        }

    logger.info(f"[调度器] 找到 {len(tenants)} 个活跃租户，开始派发子任务")

    # 使用 Celery group 并行派发子任务（fire-and-forget）
    # 不在任务内调用 result.get()，避免阻塞 worker
    job = group(
        send_appointment_reminder_for_tenant.s(tenant.id, tenant.tenant_code)
        for tenant in tenants
    )
    job.apply_async(queue="notification")

    elapsed_time = time.time() - start_time
    logger.info(
        f"[调度器] 已派发 {len(tenants)} 个租户的提醒子任务, "
        f"耗时 {elapsed_time:.2f}秒"
    )

    return {
        "sent_count": 0,
        "failed_count": 0,
        "tenant_count": len(tenants),
        "elapsed_time": elapsed_time,
    }


# ==================== 兼容旧版任务 ====================

@celery_app.task(
    name="app.tasks.notification_task.send_appointment_reminder_task",
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=600,
    soft_time_limit=480,
)
def send_appointment_reminder_task():
    """
    发送预约提醒（兼容旧版）
    每30分钟执行一次

    注意：此任务已弃用，请使用 send_appointment_reminder_scheduler
    """
    logger.warning("[定时任务] 使用旧版预约提醒任务，建议迁移到 send_appointment_reminder_scheduler")

    # 从 SystemSetting 读取预约提醒提前时间，fallback 到配置文件默认值
    try:
        with get_sync_db() as db:
            result = db.execute(
                select(Settings).where(
                    text("category = 'booking' AND key = 'appointment_reminder_hours' AND (store_id IS NULL OR store_id = '')")
                )
            )
            setting = result.scalar_one_or_none()
            reminder_hours = int(setting.value) if setting and setting.value else app_settings.APPOINTMENT_REMINDER_HOURS
    except Exception as e:
        logger.warning(f"读取预约提醒配置失败，使用默认值: {e}")
        reminder_hours = app_settings.APPOINTMENT_REMINDER_HOURS
    total_sent_count = 0
    total_failed_count = 0

    with get_sync_db() as db:
        try:
            result = db.execute(
                select(Tenant).where(
                    and_(
                        Tenant.status.in_([1, 3]),
                        Tenant.deleted_at.is_(None),
                    )
                )
            )
            tenants = result.scalars().all()
        except Exception as e:
            logger.error(f"查询租户列表失败: {e}")
            return {"sent_count": 0, "failed_count": 0, "reason": "查询租户失败"}

    if not tenants:
        logger.info("没有活跃租户，跳过预约提醒")
        return {"sent_count": 0, "failed_count": 0}

    logger.info(f"找到 {len(tenants)} 个活跃租户")

    for tenant in tenants:
        set_tenant_context(tenant.id, tenant.tenant_code)

        try:
            with get_sync_db() as db:
                sent_count = 0
                failed_count = 0
                now = datetime.now()

                reminder_start = now
                reminder_end = now + timedelta(hours=reminder_hours)

                wechat_config = _get_wechat_config(db)
                app_id = wechat_config.get('app_id') or app_settings.WECHAT_APP_ID
                app_secret = wechat_config.get('app_secret') or app_settings.WECHAT_APP_SECRET
                template_id = _get_appointment_reminder_template_id(db)

                if not app_id or not app_secret or not template_id:
                    logger.warning(f"租户 {tenant.name} 微信配置不完整，跳过")
                    continue

                # 使用 24h 级别提醒配置
                result = _send_reminder_for_level(
                    db=db,
                    tenant_id=tenant.id,
                    tenant_name=tenant.name,
                    reminder_config=REMINDER_CONFIGS[ReminderLevel.LEVEL_24H],
                    wechat_access_token=WechatTokenManager.get_access_token_sync(app_id, app_secret),
                    wechat_template_id=template_id,
                )

                sent_count = result["sent"]
                failed_count = result["failed"]

                db.commit()
                total_sent_count += sent_count
                total_failed_count += failed_count

        except Exception as e:
            logger.error(f"租户 {tenant.name} 预约提醒任务执行失败: {e}")
        finally:
            clear_tenant_context()

    logger.info(f"[定时任务] 预约提醒完成，成功 {total_sent_count} 条，失败 {total_failed_count} 条")
    return {"sent_count": total_sent_count, "failed_count": total_failed_count}


@celery_app.task(
    name="app.tasks.notification_task.send_appointment_reminder",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=120,
    soft_time_limit=90,
)
def send_appointment_reminder(appointment_id: str):
    """
    发送单个预约提醒（手动触发）

    Args:
        appointment_id: 预约 ID
    """
    logger.info(f"[任务] 发送预约提醒: appointment_id={appointment_id}")

    with get_sync_db() as db:
        try:
            from app.middleware.tenant_context import get_current_tenant_id
            tenant_id = get_current_tenant_id()

            query = (
                select(Appointment)
                .options(
                    joinedload(Appointment.schedule),
                    joinedload(Appointment.user),
                    joinedload(Appointment.doctor),
                )
                .join(Schedule, Appointment.schedule_id == Schedule.id)
                .join(User, Appointment.user_id == User.id)
                .join(Doctor, Schedule.doctor_id == Doctor.id)
                .where(Appointment.id == appointment_id)
            )

            if tenant_id:
                query = query.where(Appointment.tenant_id == tenant_id)

            result = db.execute(query)
            appointment = result.scalar_one_or_none()

            if not appointment:
                logger.warning(f"预约不存在: {appointment_id}")
                return {"success": False, "reason": "预约不存在"}

            user = appointment.user
            doctor = appointment.doctor
            schedule = appointment.schedule

            if not user.openid:
                return {"success": False, "reason": "用户无 openid"}

            wechat_config = _get_wechat_config(db)
            app_id = wechat_config.get('app_id') or app_settings.WECHAT_APP_ID
            app_secret = wechat_config.get('app_secret') or app_settings.WECHAT_APP_SECRET
            template_id = _get_appointment_reminder_template_id(db)

            if not app_id or not app_secret or not template_id:
                return {"success": False, "reason": "配置不完整"}

            access_token = WechatTokenManager.get_access_token_sync(app_id, app_secret)

            appointment_datetime = datetime.combine(
                schedule.schedule_date,
                schedule.start_time
            )

            message_data = {
                "thing1": {"value": doctor.name[:20] if doctor.name else "医生"},
                "time2": {"value": appointment_datetime.strftime("%Y年%m月%d日 %H:%M")},
                "thing3": {"value": schedule.time_slot or ""},
            }

            success = _send_wechat_subscribe_message(
                access_token=access_token,
                openid=user.openid,
                template_id=template_id,
                data=message_data,
                page=f"pages/appointment/detail?id={appointment.id}"
            )

            try:
                if success:
                    appointment.reminder_sent = 1
                    appointment.reminder_sent_24h = 1  # 同时更新新字段
                    appointment.reminder_sent_at = datetime.now()
                    db.commit()

                    log = NotificationLog(
                        tenant_id=appointment.tenant_id,
                        store_id=appointment.store_id,
                        user_id=user.id,
                        user_type="patient",
                        channel="wechat",
                        message_type="appointment_reminder",
                        title="预约提醒",
                        status="sent",
                        recipient=user.openid,
                        related_id=appointment.id,
                        sent_at=datetime.now(),
                    )
                    db.add(log)
                    db.commit()
                else:
                    log = NotificationLog(
                        tenant_id=appointment.tenant_id,
                        store_id=appointment.store_id,
                        user_id=user.id,
                        user_type="patient",
                        channel="wechat",
                        message_type="appointment_reminder",
                        title="预约提醒",
                        status="failed",
                        recipient=user.openid,
                        related_id=appointment.id,
                        error_message="微信推送失败",
                    )
                    db.add(log)
                    db.commit()
            except Exception as e:
                logger.error(f"创建通知日志失败: {e}")

            return {"success": success, "appointment_id": appointment_id}

        except Exception as e:
            db.rollback()
            logger.error(f"发送预约提醒失败: {e}")
            return {"success": False, "reason": str(e)}
