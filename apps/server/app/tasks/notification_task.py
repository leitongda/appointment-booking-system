"""
通知相关定时任务
- 预约提醒（就诊前发送微信消息/短信）
- 通用微信订阅消息推送辅助函数
"""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
import logging

from app.celery_app import celery_app
from app.db.session import get_sync_db
from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.user import User
from app.models.doctor import Doctor
from app.models.department import Department
from app.models.notification_log import NotificationLog
from app.models.settings import SystemSetting as Settings
from app.models.tenant import Tenant
from app.core.config import settings as app_settings
from app.infrastructure.wechat.service import WechatService
from app.infrastructure.wechat.token_manager import WechatTokenManager
from app.middleware.tenant_context import set_tenant_context, clear_tenant_context
from app.modules.settings.service import SettingsService
import httpx

logger = logging.getLogger(__name__)


async def _send_wechat_notification(
    db: AsyncSession,
    tenant_id: str,
    openid: str,
    template_id_config_key: str,
    template_data: dict,
    message_type: str,
    title: str,
    user_id: Optional[str] = None,
    store_id: Optional[str] = None,
    related_id: Optional[str] = None,
    page: str = "",
    notification_log_context: Optional[dict] = None,
) -> bool:
    """通用微信订阅消息推送辅助函数。

    从 system_settings 读取 template_id，调用 WechatService 发送，
    并记录 NotificationLog。

    Args:
        db: 异步数据库会话
        tenant_id: 租户 ID
        openid: 用户 openid
        template_id_config_key: system_settings 中的配置键名（category="wechat"）
        template_data: 微信模板数据 dict
        message_type: 消息类型（如 "appointment_success"）
        title: 消息标题（写入 NotificationLog）
        user_id: 接收用户 ID
        store_id: 门店 ID
        related_id: 关联业务 ID（如预约 ID）
        page: 点击消息后跳转的小程序页面
        notification_log_context: 额外写入 NotificationLog.extra_data 的上下文

    Returns:
        是否发送成功
    """
    # 偏好检查：用户禁用 wechat 通道时跳过推送
    if user_id:
        try:
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
            type_col = _TYPE_FIELD_MAP.get(message_type)
            if type_col:
                pref_stmt = text(
                    f"SELECT wechat_enabled, {type_col} "
                    f"FROM notification_preferences "
                    f"WHERE user_id = :uid AND user_type = 'patient' "
                    f"LIMIT 1"
                )
                pref_result = await db.execute(pref_stmt, {"uid": user_id})
                pref_row = pref_result.first()
                if pref_row is not None and (not pref_row[0] or not pref_row[1]):
                    logger.debug(
                        "[微信推送] 用户 %s 已禁用 wechat/%s，跳过", user_id, message_type,
                    )
                    return False
        except Exception:
            pass

    # 读取 template_id
    settings_service = SettingsService(db)
    template_id = await settings_service.get_value(
        category="wechat",
        key=template_id_config_key,
        default="",
    )
    if not template_id:
        logger.debug(
            "[微信推送] 模板未配置，跳过: key=%s, tenant_id=%s",
            template_id_config_key,
            tenant_id,
        )
        return False

    success = False
    error_msg = None
    try:
        wechat_service = WechatService(db)
        success = await wechat_service.send_subscribe_message(
            openid=openid,
            template_id=template_id,
            data=template_data,
            page=page or None,
        )
        if not success:
            error_msg = "微信推送返回失败"
    except Exception as exc:
        success = False
        error_msg = str(exc)
        logger.warning(
            "[微信推送] 发送异常: type=%s, openid=%s, error=%s",
            message_type,
            openid,
            exc,
        )

    # 记录 NotificationLog
    try:
        log = NotificationLog(
            tenant_id=tenant_id,
            store_id=store_id,
            user_id=user_id,
            user_type="patient",
            channel="wechat",
            message_type=message_type,
            title=title,
            status="sent" if success else "failed",
            recipient=openid,
            related_id=related_id,
            sent_at=datetime.now() if success else None,
            error_message=error_msg,
            extra_data=notification_log_context,
        )
        db.add(log)
        await db.flush()
    except Exception as exc:
        logger.warning("[微信推送] 写入 NotificationLog 失败: %s", exc)

    return success


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


@celery_app.task(name="app.tasks.notification_task.send_appointment_reminder_task")
def send_appointment_reminder_task():
    """
    发送预约提醒（多租户版本）
    每30分钟执行一次

    规则：
    - 遍历所有活跃租户
    - 就诊时间在 N 小时内
    - 预约状态为"待就诊"
    - 用户有 openid
    - 尚未发送过提醒
    """
    logger.info("[定时任务] 开始执行：预约提醒")

    reminder_hours = app_settings.APPOINTMENT_REMINDER_HOURS
    total_sent_count = 0
    total_failed_count = 0

    # 第一步：查询所有活跃租户
    with get_sync_db() as db:
        try:
            result = db.execute(
                select(Tenant).where(Tenant.status.in_([1, 3]))  # 正常或试用状态
            )
            tenants = result.scalars().all()
        except Exception as e:
            logger.error(f"查询租户列表失败: {e}")
            return {"sent_count": 0, "failed_count": 0, "reason": "查询租户失败"}

    if not tenants:
        logger.info("没有活跃租户，跳过预约提醒")
        return {"sent_count": 0, "failed_count": 0}

    logger.info(f"找到 {len(tenants)} 个活跃租户")

    # 第二步：遍历每个租户，在其上下文中发送预约提醒
    for tenant in tenants:
        logger.info(f"开始处理租户: {tenant.name}({tenant.tenant_code}), id={tenant.id}")

        # 设置当前租户上下文
        set_tenant_context(tenant.id, tenant.tenant_code)

        try:
            with get_sync_db() as db:
                sent_count = 0
                failed_count = 0
                now = datetime.now()

                # 计算提醒时间范围
                reminder_start = now
                reminder_end = now + timedelta(hours=reminder_hours)

                # 获取微信配置
                wechat_config = _get_wechat_config(db)
                app_id = wechat_config.get('app_id') or app_settings.WECHAT_APP_ID
                app_secret = wechat_config.get('app_secret') or app_settings.WECHAT_APP_SECRET
                template_id = _get_appointment_reminder_template_id(db)

                if not app_id or not app_secret:
                    logger.warning(f"租户 {tenant.name} 微信配置不完整，跳过")
                    continue

                if not template_id:
                    logger.warning(f"租户 {tenant.name} 预约提醒模板 ID 未配置，跳过")
                    continue

                # 查找需要提醒的预约（添加 tenant_id 过滤）
                result = db.execute(
                    select(Appointment, Schedule, User, Doctor)
                    .join(Schedule, Appointment.schedule_id == Schedule.id)
                    .join(User, Appointment.user_id == User.id)
                    .join(Doctor, Schedule.doctor_id == Doctor.id)
                    .where(
                        and_(
                            Appointment.tenant_id == tenant.id,
                            Appointment.status == 1,  # 待就诊
                            Appointment.reminder_sent == 0,  # 未发送过提醒
                            # 就诊日期时间在提醒范围内
                            Schedule.schedule_date >= reminder_start.date(),
                            Schedule.schedule_date <= reminder_end.date()
                        )
                    )
                )

                appointments_to_remind = result.all()

                if not appointments_to_remind:
                    logger.info(f"租户 {tenant.name} 没有需要提醒的预约")
                    continue

                # 获取 access_token
                try:
                    access_token = WechatTokenManager.get_access_token_sync(
                        app_id, app_secret
                    )
                except Exception as e:
                    logger.error(f"租户 {tenant.name} 获取微信 access_token 失败: {e}")
                    total_failed_count += len(appointments_to_remind)
                    continue

                for appointment, schedule, user, doctor in appointments_to_remind:
                    # 检查用户是否有 openid
                    if not user.openid:
                        logger.debug(f"用户 {user.id} 没有 openid，跳过")
                        continue

                    # 检查就诊时间是否在范围内
                    appointment_datetime = datetime.combine(
                        schedule.schedule_date,
                        schedule.start_time
                    )

                    if appointment_datetime < reminder_start or appointment_datetime > reminder_end:
                        continue

                    # 构建消息数据
                    message_data = {
                        "thing1": {"value": doctor.name[:20] if doctor.name else "医生"},  # 医生姓名
                        "time2": {"value": appointment_datetime.strftime("%Y年%m月%d日 %H:%M")},  # 就诊时间
                        "thing3": {"value": schedule.time_slot or ""},  # 时段
                    }

                    # 发送消息
                    success = _send_wechat_subscribe_message(
                        access_token=access_token,
                        openid=user.openid,
                        template_id=template_id,
                        data=message_data,
                        page=f"pages/appointment/detail?id={appointment.id}"
                    )

                    try:
                        if success:
                            # 标记已发送
                            appointment.reminder_sent = 1
                            appointment.reminder_sent_at = now
                            sent_count += 1
                            logger.info(f"预约提醒发送成功: appointment_id={appointment.id}")

                            log = NotificationLog(
                                tenant_id=tenant.id,
                                store_id=appointment.store_id,
                                user_id=user.id,
                                user_type="patient",
                                channel="wechat",
                                message_type="appointment_reminder",
                                title="预约提醒",
                                status="sent",
                                recipient=user.openid,
                                related_id=appointment.id,
                                sent_at=now,
                            )
                            db.add(log)
                        else:
                            failed_count += 1
                            logger.warning(f"预约提醒发送失败: appointment_id={appointment.id}")

                            log = NotificationLog(
                                tenant_id=tenant.id,
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
                    except Exception as e:
                        logger.error(f"创建通知日志失败: {e}")

                db.commit()
                total_sent_count += sent_count
                total_failed_count += failed_count

        except Exception as e:
            logger.error(f"租户 {tenant.name} 预约提醒任务执行失败: {e}")
        finally:
            # 清除租户上下文
            clear_tenant_context()

    logger.info(f"[定时任务] 预约提醒完成，成功 {total_sent_count} 条，失败 {total_failed_count} 条")
    return {"sent_count": total_sent_count, "failed_count": total_failed_count}


@celery_app.task(name="app.tasks.notification_task.send_appointment_reminder")
def send_appointment_reminder(appointment_id: str):
    """
    发送单个预约提醒（手动触发）
    
    Args:
        appointment_id: 预约 ID
    """
    logger.info(f"[任务] 发送预约提醒: appointment_id={appointment_id}")
    
    with get_sync_db() as db:
        try:
            # 查询预约信息（添加租户隔离）
            from app.middleware.tenant_context import get_current_tenant_id
            tenant_id = get_current_tenant_id()

            query = (
                select(Appointment, Schedule, User, Doctor)
                .join(Schedule, Appointment.schedule_id == Schedule.id)
                .join(User, Appointment.user_id == User.id)
                .join(Doctor, Schedule.doctor_id == Doctor.id)
                .where(Appointment.id == appointment_id)
            )

            # 如果有租户上下文，添加租户过滤
            if tenant_id:
                query = query.where(Appointment.tenant_id == tenant_id)

            result = db.execute(query)
            
            row = result.first()
            if not row:
                logger.warning(f"预约不存在: {appointment_id}")
                return {"success": False, "reason": "预约不存在"}
            
            appointment, schedule, user, doctor = row
            
            if not user.openid:
                return {"success": False, "reason": "用户无 openid"}
            
            # 获取配置
            wechat_config = _get_wechat_config(db)
            app_id = wechat_config.get('app_id') or app_settings.WECHAT_APP_ID
            app_secret = wechat_config.get('app_secret') or app_settings.WECHAT_APP_SECRET
            template_id = _get_appointment_reminder_template_id(db)
            
            if not app_id or not app_secret or not template_id:
                return {"success": False, "reason": "配置不完整"}
            
            # 获取 token
            access_token = WechatTokenManager.get_access_token_sync(app_id, app_secret)
            
            # 构建消息
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

