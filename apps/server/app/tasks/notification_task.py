"""
通知相关定时任务
- 预约提醒（就诊前发送微信消息/短信）
"""
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.orm import Session
import logging

from app.celery_app import celery_app
from app.db.session import get_sync_db
from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.user import User
from app.models.doctor import Doctor
from app.models.department import Department
from app.models.settings import SystemSetting as Settings
from app.core.config import settings as app_settings
from app.services.wechat_service import WechatTokenManager
import httpx

logger = logging.getLogger(__name__)


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
    发送预约提醒
    每30分钟执行一次
    
    规则：
    - 就诊时间在 N 小时内
    - 预约状态为"待就诊"
    - 用户有 openid
    - 尚未发送过提醒
    """
    logger.info("[定时任务] 开始执行：预约提醒")
    
    reminder_hours = app_settings.APPOINTMENT_REMINDER_HOURS
    sent_count = 0
    failed_count = 0
    
    with get_sync_db() as db:
        try:
            now = datetime.now()
            
            # 计算提醒时间范围
            # 例如：当前时间 + 24小时内的预约
            reminder_start = now
            reminder_end = now + timedelta(hours=reminder_hours)
            
            # 获取微信配置
            wechat_config = _get_wechat_config(db)
            app_id = wechat_config.get('app_id') or app_settings.WECHAT_APP_ID
            app_secret = wechat_config.get('app_secret') or app_settings.WECHAT_APP_SECRET
            template_id = _get_appointment_reminder_template_id(db)
            
            if not app_id or not app_secret:
                logger.warning("微信配置不完整，跳过预约提醒")
                return {"sent_count": 0, "failed_count": 0, "reason": "微信配置不完整"}
            
            if not template_id:
                logger.warning("预约提醒模板 ID 未配置，跳过")
                return {"sent_count": 0, "failed_count": 0, "reason": "模板未配置"}
            
            # 查找需要提醒的预约
            result = db.execute(
                select(Appointment, Schedule, User, Doctor)
                .join(Schedule, Appointment.schedule_id == Schedule.id)
                .join(User, Appointment.user_id == User.id)
                .join(Doctor, Schedule.doctor_id == Doctor.id)
                .where(
                    and_(
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
                logger.info("没有需要提醒的预约")
                return {"sent_count": 0, "failed_count": 0}
            
            # 获取 access_token
            try:
                access_token = WechatTokenManager.get_access_token_sync(
                    app_id, app_secret
                )
            except Exception as e:
                logger.error(f"获取微信 access_token 失败: {e}")
                return {"sent_count": 0, "failed_count": len(appointments_to_remind), "reason": str(e)}
            
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
                # 注意：微信订阅消息的数据格式
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
                
                if success:
                    # 标记已发送
                    appointment.reminder_sent = 1
                    appointment.reminder_sent_at = now
                    sent_count += 1
                    logger.info(f"预约提醒发送成功: appointment_id={appointment.id}")
                else:
                    failed_count += 1
                    logger.warning(f"预约提醒发送失败: appointment_id={appointment.id}")
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            logger.error(f"预约提醒任务执行失败: {e}")
            raise
    
    logger.info(f"[定时任务] 预约提醒完成，成功 {sent_count} 条，失败 {failed_count} 条")
    return {"sent_count": sent_count, "failed_count": failed_count}


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
            # 查询预约信息
            result = db.execute(
                select(Appointment, Schedule, User, Doctor)
                .join(Schedule, Appointment.schedule_id == Schedule.id)
                .join(User, Appointment.user_id == User.id)
                .join(Doctor, Schedule.doctor_id == Doctor.id)
                .where(Appointment.id == appointment_id)
            )
            
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
            
            if success:
                appointment.reminder_sent = 1
                appointment.reminder_sent_at = datetime.now()
                db.commit()
            
            return {"success": success, "appointment_id": appointment_id}
            
        except Exception as e:
            db.rollback()
            logger.error(f"发送预约提醒失败: {e}")
            return {"success": False, "reason": str(e)}

