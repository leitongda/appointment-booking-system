"""
黑名单相关定时任务
- 自动解禁到期的黑名单用户
- 自动标记爽约的预约
"""
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, update
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.celery_app import celery_app
from app.db.session import get_sync_db
from app.models.blacklist import Blacklist
from app.models.user import User
from app.models.appointment import Appointment
from app.models.message import Message
from app.models.admin import Admin
from app.models.settings import SystemSetting as Settings
from app.models.tenant import Tenant
from app.middleware.tenant_context import set_tenant_context, clear_tenant_context
from app.modules.appointments.common import APPOINTMENT_STATUS
import uuid

logger = logging.getLogger(__name__)


def _snake_to_camel(value: str) -> str:
    parts = value.split('_')
    return parts[0] + ''.join(part.capitalize() for part in parts[1:])


def _camel_to_snake(value: str) -> str:
    chars = []
    for ch in value:
        if ch.isupper():
            chars.append('_')
            chars.append(ch.lower())
        else:
            chars.append(ch)
    return ''.join(chars).lstrip('_')


async def auto_release_blacklist(db: AsyncSession) -> list[str]:
    """
    自动解禁到期的黑名单用户（异步版本，供 FastAPI 后台任务使用）
    
    Args:
        db: 异步数据库会话
    
    Returns:
        解禁的黑名单记录 ID 列表
    """
    now = datetime.now()
    released_ids = []
    
    try:
        # 查找已过期且状态为有效的黑名单记录
        result = await db.execute(
            select(Blacklist)
            .where(
                and_(
                    Blacklist.status == 1,
                    Blacklist.expire_at != None,
                    Blacklist.expire_at <= now
                )
            )
        )
        expired_records = result.scalars().all()
        
        for record in expired_records:
            # 更新状态为已解禁
            record.status = 0
            record.updated_at = now
            released_ids.append(record.id)
            
            # 获取用户信息用于日志
            user_info = "未知用户"
            if record.user_id:
                user_result = await db.execute(
                    select(User).where(User.id == record.user_id)
                )
                user = user_result.scalar_one_or_none()
                if user:
                    user_info = user.nickname or user.phone or "未知用户"
            elif record.keyword:
                user_info = record.keyword
            
            logger.info(f"已自动解禁黑名单用户: {user_info}")
        
        await db.commit()
        
    except Exception as e:
        await db.rollback()
        logger.error(f"黑名单自动解禁失败: {e}")
        raise
    
    return released_ids


def _get_setting_value(db: Session, category: str, key: str, default=None):
    """从数据库获取配置值"""
    candidate_keys = [key]
    camel_key = _snake_to_camel(key)
    snake_key = _camel_to_snake(key)
    if camel_key not in candidate_keys:
        candidate_keys.append(camel_key)
    if snake_key not in candidate_keys:
        candidate_keys.append(snake_key)

    try:
        for candidate_key in candidate_keys:
            result = db.execute(
                select(Settings).where(
                    and_(
                        Settings.category == category,
                        Settings.key == candidate_key
                    )
                )
            )
            setting = result.scalar_one_or_none()
            if setting:
                return setting.value
        return default
    except Exception:
        return default


def _notify_admins_sync(db: Session, title: str, content: str):
    """发送消息通知给所有管理员（同步版本）"""
    try:
        result = db.execute(
            select(Admin).where(Admin.status == 1)
        )
        admins = result.scalars().all()
        
        for admin in admins:
            message = Message(
                id=str(uuid.uuid4()),
                user_id=admin.id,
                user_type='admin',
                title=title,
                content=content,
                message_type='system',
                is_read=0,
            )
            db.add(message)
    except Exception as e:
        logger.error(f"发送管理员通知失败: {e}")


@celery_app.task(name="app.tasks.blacklist_task.auto_release_blacklist_task")
def auto_release_blacklist_task():
    """
    自动解禁到期的黑名单用户
    每小时执行一次
    """
    logger.info("[定时任务] 开始执行：黑名单自动解禁")
    released_count = 0
    
    with get_sync_db() as db:
        try:
            now = datetime.now()
            
            # 查找已过期且状态为有效的黑名单记录
            result = db.execute(
                select(Blacklist)
                .where(
                    and_(
                        Blacklist.status == 1,
                        Blacklist.expire_at != None,
                        Blacklist.expire_at <= now
                    )
                )
            )
            expired_records = result.scalars().all()
            
            for record in expired_records:
                # 更新状态为已解禁
                record.status = 0
                record.updated_at = now
                
                # 获取用户信息
                user_info = "未知用户"
                if record.user_id:
                    user = db.get(User, record.user_id)
                    if user:
                        user_info = user.nickname or user.phone or "未知用户"
                elif record.keyword:
                    user_info = record.keyword
                
                # 发送通知
                _notify_admins_sync(
                    db,
                    title='黑名单用户已自动解禁',
                    content=f'用户 {user_info} 已于 {now.strftime("%Y-%m-%d %H:%M")} 自动解禁'
                )
                
                released_count += 1
                logger.info(f"已解禁黑名单用户: {user_info}")
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            logger.error(f"黑名单自动解禁任务执行失败: {e}")
            raise
    
    logger.info(f"[定时任务] 黑名单自动解禁完成，共解禁 {released_count} 人")
    return {"released_count": released_count}


@celery_app.task(name="app.tasks.blacklist_task.mark_no_show_appointments_task")
def mark_no_show_appointments_task():
    """
    自动标记爽约的预约（多租户版本）
    每30分钟执行一次

    规则：
    - 遍历所有活跃租户
    - 预约日期已过
    - 预约状态为"待就诊"（status=1）
    - 超过就诊结束时间仍未签到
    """
    logger.info("[定时任务] 开始执行：爽约自动标记")
    total_marked_count = 0
    total_blacklisted_count = 0

    # 第一步：查询所有活跃租户
    with get_sync_db() as db:
        try:
            result = db.execute(
                select(Tenant).where(Tenant.status.in_([1, 3]))  # 正常或试用状态
            )
            tenants = result.scalars().all()
        except Exception as e:
            logger.error(f"查询租户列表失败: {e}")
            return {"marked_count": 0, "blacklisted_count": 0}

    if not tenants:
        logger.info("没有活跃租户，跳过爽约标记")
        return {"marked_count": 0, "blacklisted_count": 0}

    logger.info(f"找到 {len(tenants)} 个活跃租户")

    # 第二步：遍历每个租户，在其上下文中标记爽约
    for tenant in tenants:
        logger.info(f"开始处理租户: {tenant.name}({tenant.tenant_code}), id={tenant.id}")

        # 设置当前租户上下文
        set_tenant_context(tenant.id, tenant.tenant_code)

        try:
            with get_sync_db() as db:
                marked_count = 0
                blacklisted_count = 0
                now = datetime.now()
                today = now.date()
                current_time = now.time()

                # 获取配置
                no_show_limit = int(_get_setting_value(db, 'booking', 'no_show_limit', 3))
                blacklist_days = int(_get_setting_value(db, 'booking', 'blacklist_days', 30))

                # 查找需要标记为爽约的预约（添加 tenant_id 过滤）
                from app.models.schedule import Schedule

                result = db.execute(
                    select(Appointment, Schedule)
                    .join(Schedule, Appointment.schedule_id == Schedule.id)
                    .where(
                        and_(
                            Appointment.tenant_id == tenant.id,
                            Appointment.status == 1,  # 待就诊
                            # 日期已过，或当天已过结束时间
                            (
                                (Schedule.schedule_date < today) |
                                (
                                    (Schedule.schedule_date == today) &
                                    (Schedule.end_time < current_time)
                                )
                            )
                        )
                    )
                )

                appointments_to_mark = result.all()

                for appointment, schedule in appointments_to_mark:
                    # 标记为爽约
                    appointment.status = APPOINTMENT_STATUS["NO_SHOW"]
                    appointment.updated_at = now
                    marked_count += 1

                    # 检查是否需要加入黑名单
                    user_id = appointment.user_id

                    # 统计该用户的爽约次数
                    no_show_count = db.scalar(
                        select(func.count(Appointment.id)).where(
                            and_(
                                Appointment.tenant_id == tenant.id,
                                Appointment.user_id == user_id,
                                Appointment.status == APPOINTMENT_STATUS["NO_SHOW"]
                            )
                        )
                    )

                    # 达到阈值，自动加入黑名单
                    if no_show_count and no_show_count >= no_show_limit:
                        # 检查是否已在黑名单中
                        existing_blacklist = db.scalar(
                            select(Blacklist).where(
                                and_(
                                    Blacklist.tenant_id == tenant.id,
                                    Blacklist.user_id == user_id,
                                    Blacklist.status == 1
                                )
                            )
                        )

                        if not existing_blacklist:
                            expire_at = now + timedelta(days=blacklist_days)
                            blacklist = Blacklist(
                                id=str(uuid.uuid4()),
                                tenant_id=tenant.id,
                                user_id=user_id,
                                reason=f'自动加入：爽约 {no_show_count} 次',
                                no_show_count=no_show_count,
                                source=2,
                                expire_at=expire_at,
                                status=1,
                            )
                            db.add(blacklist)
                            blacklisted_count += 1

                            # 发送通知
                            user = db.get(User, user_id)
                            user_info = user.nickname or user.phone if user else '未知用户'
                            _notify_admins_sync(
                                db,
                                title='用户已自动加入黑名单',
                                content=f'用户 {user_info} 因爽约 {no_show_count} 次，'
                                       f'已自动加入黑名单，将于 {expire_at.strftime("%Y-%m-%d")} 自动解禁'
                            )
                            logger.info(f"用户 {user_info} 已加入黑名单")

                db.commit()
                total_marked_count += marked_count
                total_blacklisted_count += blacklisted_count

        except Exception as e:
            logger.error(f"租户 {tenant.name} 爽约自动标记任务执行失败: {e}")
        finally:
            # 清除租户上下文
            clear_tenant_context()

    logger.info(f"[定时任务] 爽约自动标记完成，共标记 {total_marked_count} 条，"
                f"新增黑名单 {total_blacklisted_count} 人")
    return {
        "marked_count": total_marked_count,
        "blacklisted_count": total_blacklisted_count
    }


@celery_app.task(name="app.tasks.blacklist_task.check_and_add_blacklist")
def check_and_add_blacklist(user_id: str):
    """
    检查用户爽约次数并自动加入黑名单（多租户版本）
    在预约状态变更为爽约时调用（手动触发）

    Args:
        user_id: 用户ID
    """
    logger.info(f"[任务] 检查用户黑名单状态: user_id={user_id}")

    # 从租户上下文获取租户ID
    from app.middleware.tenant_context import get_current_tenant_id
    tenant_id = get_current_tenant_id()

    if not tenant_id:
        logger.warning("无法获取租户上下文，跳过黑名单检查")
        return {"blacklisted": False, "user_id": user_id, "reason": "无租户上下文"}

    with get_sync_db() as db:
        try:
            # 获取配置
            no_show_limit = int(_get_setting_value(db, 'booking', 'no_show_limit', 3))
            blacklist_days = int(_get_setting_value(db, 'booking', 'blacklist_days', 30))

            # 统计爽约次数（添加租户过滤）
            no_show_count = db.scalar(
                select(func.count(Appointment.id)).where(
                    and_(
                        Appointment.tenant_id == tenant_id,
                        Appointment.user_id == user_id,
                        Appointment.status == APPOINTMENT_STATUS["NO_SHOW"]
                    )
                )
            )

            if no_show_count and no_show_count >= no_show_limit:
                # Blacklist 当前按 user_id 唯一匹配用户，用户记录自身已带租户归属
                existing = db.scalar(
                    select(Blacklist).where(
                        and_(
                            Blacklist.tenant_id == tenant_id,
                            Blacklist.user_id == user_id,
                            Blacklist.status == 1
                        )
                    )
                )

                if not existing:
                    now = datetime.now()
                    expire_at = now + timedelta(days=blacklist_days)

                    blacklist = Blacklist(
                        id=str(uuid.uuid4()),
                        tenant_id=tenant_id,
                        user_id=user_id,
                        reason=f'自动加入：爽约 {no_show_count} 次',
                        no_show_count=no_show_count,
                        source=2,
                        expire_at=expire_at,
                        status=1,
                    )
                    db.add(blacklist)

                    # 发送通知
                    user = db.get(User, user_id)
                    user_info = user.nickname or user.phone if user else '未知用户'
                    _notify_admins_sync(
                        db,
                        title='用户已自动加入黑名单',
                        content=f'用户 {user_info} 因爽约 {no_show_count} 次，'
                               f'已自动加入黑名单'
                    )

                    db.commit()
                    logger.info(f"用户 {user_id} 已加入黑名单")
                    return {"blacklisted": True, "user_id": user_id}

            return {"blacklisted": False, "user_id": user_id}

        except Exception as e:
            db.rollback()
            logger.error(f"检查黑名单任务失败: {e}")
            raise
