"""黑名单定时任务"""
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.blacklist import Blacklist
from app.models.user import User
from app.models.appointment import Appointment
from app.models.message import Message
from app.models.admin import Admin
from app.services.blacklist_service import BlacklistService
from app.services.settings_service import SettingsService
import uuid


async def _notify_admins(db: AsyncSession, title: str, content: str):
    """发送消息通知给所有管理员"""
    # 查询所有启用的管理员
    result = await db.execute(
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


async def auto_release_blacklist(db: AsyncSession) -> list:
    """
    自动解禁到期的黑名单
    建议每小时执行一次
    
    Returns:
        解禁的黑名单列表
    """
    service = BlacklistService(db)
    released = await service.auto_release_expired()
    
    # 发送站内消息通知管理员
    for item in released:
        user_info = item.get('userName') or item.get('userPhone') or item.get('keyword') or '未知用户'
        await _notify_admins(
            db,
            title='黑名单用户已自动解禁',
            content=f'用户 {user_info} 已于 {datetime.now().strftime("%Y-%m-%d %H:%M")} 自动解禁'
        )
    
    if released:
        await db.commit()
    
    return released


async def check_and_add_blacklist(db: AsyncSession, user_id: str) -> dict | None:
    """
    检查用户爽约次数并自动加入黑名单
    在预约状态变更为爽约时调用
    
    Args:
        db: 数据库会话
        user_id: 用户ID
    
    Returns:
        如果加入黑名单则返回黑名单记录，否则返回 None
    """
    # 获取系统配置
    settings_service = SettingsService(db)
    booking_settings = await settings_service.get_booking_settings()
    no_show_limit = booking_settings.get('noShowLimit', 3)
    blacklist_days = booking_settings.get('blacklistDays', 30)
    
    # 查询用户爽约次数
    no_show_count = await db.scalar(
        select(func.count(Appointment.id)).where(
            and_(
                Appointment.user_id == user_id,
                Appointment.status == 7  # 爽约状态
            )
        )
    )
    
    # 如果达到阈值，自动加入黑名单
    if no_show_count and no_show_count >= no_show_limit:
        blacklist_service = BlacklistService(db)
        result = await blacklist_service.auto_add_blacklist(
            user_id=user_id,
            no_show_count=no_show_count,
            blacklist_days=blacklist_days,
        )
        
        if result:
            # 发送站内消息通知管理员
            user = await db.get(User, user_id)
            user_info = user.nickname or user.phone if user else '未知用户'
            await _notify_admins(
                db,
                title='用户已自动加入黑名单',
                content=f'用户 {user_info} 因爽约 {no_show_count} 次，已自动加入黑名单，将于 {result.get("expireAt", "N/A")} 自动解禁'
            )
            await db.commit()
        
        return result
    
    return None
