"""双写过渡期同步服务

在过渡期内，对旧表（admins / doctors / users）的写操作同步到新表
（accounts + account_admins / account_doctors / account_users）。

设计原则:
  - 旧表仍然是主表，新表是被动同步方
  - 同步操作在同一事务内完成
  - 同步失败仅记录日志，不影响主流程
  - 通过 ACCOUNT_DUAL_WRITE_ENABLED 开关控制
"""

import logging
import uuid
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.account import (
    Account,
    AccountAdmin,
    AccountDoctor,
    AccountUser,
    account_admin_stores,
)
from app.models.admin import Admin, Role, admin_stores
from app.models.doctor import Doctor
from app.models.user import User
from app.utils.audit import set_create_audit, set_update_audit

logger = logging.getLogger(__name__)


def _is_dual_write_enabled() -> bool:
    """检查双写开关是否开启"""
    return settings.ACCOUNT_DUAL_WRITE_ENABLED


async def _get_default_role_id(db: AsyncSession, role_type: str) -> Optional[str]:
    """查询某角色类型的默认 role_id"""
    result = await db.execute(
        select(Role.id).where(
            and_(
                Role.role_type == role_type,
                Role.is_default == True,
                Role.status == 1,
            )
        ).limit(1)
    )
    row = result.scalar_one_or_none()
    return row


class AccountSyncService:
    """双写过渡期同步服务

    过渡期结束后，直接读写新表，旧表可废弃。
    """

    # ------------------------------------------------------------------ #
    #  Admin 同步
    # ------------------------------------------------------------------ #

    @staticmethod
    async def sync_admin_to_account(
        db: AsyncSession,
        admin_id: str,
        operator_id: Optional[str] = None,
    ) -> None:
        """Admin 写操作后同步到 accounts + account_admins

        根据旧表 Admin 记录 upsert 新表：
          - accounts 主表：认证与基础信息
          - account_admins 扩展表：管理员特有字段
          - account_admin_stores 关联表：门店多对多

        使用 admin.id 作为 account.id，保持 ID 一致，方便后续切换。
        """
        if not _is_dual_write_enabled():
            return

        try:
            # 查询旧表记录
            admin = await db.get(Admin, admin_id)
            if not admin:
                logger.warning("双写同步: Admin(id=%s) 不存在，跳过", admin_id)
                return

            # --- upsert accounts 主表 ---
            account = await db.get(Account, admin_id)
            if account:
                # 更新已有记录
                account.phone = admin.phone
                account.username = admin.username
                account.password_hash = admin.password_hash
                account.name = admin.name
                account.avatar = admin.avatar
                account.gender = 0  # Admin 表无 gender 字段，默认未知
                account.status = admin.status
                account.tenant_id = admin.tenant_id
                account.last_login_at = admin.last_login_at
                account.last_login_ip = admin.last_login_ip
                account.nickname = admin.name  # Admin 用 name 作 nickname
                set_update_audit(account, operator_id)
            else:
                # 创建新记录（ID 与旧表一致）
                account = Account(
                    id=admin.id,
                    tenant_id=admin.tenant_id,
                    phone=admin.phone,
                    username=admin.username,
                    password_hash=admin.password_hash,
                    nickname=admin.name,
                    name=admin.name,
                    avatar=admin.avatar,
                    gender=0,
                    status=admin.status,
                    last_login_at=admin.last_login_at,
                    last_login_ip=admin.last_login_ip,
                )
                set_create_audit(account, operator_id)
                db.add(account)
            await db.flush()

            # --- upsert account_admins 扩展表 ---
            account_admin = await db.get(AccountAdmin, admin_id)
            if account_admin:
                account_admin.role_id = admin.role_id
                account_admin.current_store_id = admin.current_store_id
                account_admin.email = admin.email
                set_update_audit(account_admin, operator_id)
            else:
                account_admin = AccountAdmin(
                    account_id=admin.id,
                    role_id=admin.role_id,
                    current_store_id=admin.current_store_id,
                    email=admin.email,
                )
                set_create_audit(account_admin, operator_id)
                db.add(account_admin)
            await db.flush()

            # --- 同步门店关联 ---
            # 先查旧表的门店关联
            result = await db.execute(
                select(admin_stores).where(admin_stores.c.admin_id == admin_id)
            )
            old_store_rows = result.all()

            # 删除新表旧关联，再重新写入
            from sqlalchemy import delete as sa_delete
            await db.execute(
                sa_delete(account_admin_stores).where(
                    account_admin_stores.c.account_id == admin_id
                )
            )
            for row in old_store_rows:
                await db.execute(
                    account_admin_stores.insert().values(
                        account_id=admin_id,
                        store_id=row.store_id,
                        is_manager=row.is_manager,
                    )
                )
            await db.flush()

            logger.info("双写同步: Admin(id=%s) 同步到 accounts 成功", admin_id)

        except Exception:
            logger.exception("双写同步: Admin(id=%s) 同步失败", admin_id)

    @staticmethod
    async def delete_admin_from_account(
        db: AsyncSession,
        admin_id: str,
    ) -> None:
        """Admin 删除时同步删除新表记录"""
        if not _is_dual_write_enabled():
            return

        try:
            account = await db.get(Account, admin_id)
            if account:
                await db.delete(account)
                # account_admins 和 account_admin_stores 通过 CASCADE 自动删除
                await db.flush()
                logger.info("双写同步: Admin(id=%s) 从 accounts 删除成功", admin_id)
        except Exception:
            logger.exception("双写同步: Admin(id=%s) 删除同步失败", admin_id)

    @staticmethod
    async def update_admin_login_info(
        db: AsyncSession,
        admin_id: str,
        ip: str,
    ) -> None:
        """Admin 更新登录信息时同步到新表"""
        if not _is_dual_write_enabled():
            return

        try:
            account = await db.get(Account, admin_id)
            if account:
                from datetime import datetime
                account.last_login_at = datetime.now()
                account.last_login_ip = ip
                await db.flush()
        except Exception:
            logger.exception("双写同步: Admin(id=%s) 登录信息同步失败", admin_id)

    # ------------------------------------------------------------------ #
    #  Doctor 同步
    # ------------------------------------------------------------------ #

    @staticmethod
    async def sync_doctor_to_account(
        db: AsyncSession,
        doctor_id: str,
        operator_id: Optional[str] = None,
    ) -> None:
        """Doctor 写操作后同步到 accounts + account_doctors

        使用 doctor.id 作为 account.id，保持 ID 一致。
        """
        if not _is_dual_write_enabled():
            return

        try:
            # 查询旧表记录
            doctor = await db.get(Doctor, doctor_id)
            if not doctor:
                logger.warning("双写同步: Doctor(id=%s) 不存在，跳过", doctor_id)
                return

            # --- upsert accounts 主表 ---
            account = await db.get(Account, doctor_id)
            if account:
                account.phone = doctor.phone
                account.username = doctor.username
                account.password_hash = doctor.password_hash
                account.name = doctor.name
                account.avatar = doctor.avatar
                account.gender = doctor.gender if doctor.gender is not None else 0
                account.status = doctor.status
                account.tenant_id = doctor.tenant_id
                account.last_login_at = doctor.last_login_at
                account.last_login_ip = doctor.last_login_ip
                account.nickname = doctor.name
                set_update_audit(account, operator_id)
            else:
                account = Account(
                    id=doctor.id,
                    tenant_id=doctor.tenant_id,
                    phone=doctor.phone,
                    username=doctor.username,
                    password_hash=doctor.password_hash,
                    nickname=doctor.name,
                    name=doctor.name,
                    avatar=doctor.avatar,
                    gender=doctor.gender if doctor.gender is not None else 0,
                    status=doctor.status,
                    last_login_at=doctor.last_login_at,
                    last_login_ip=doctor.last_login_ip,
                )
                set_create_audit(account, operator_id)
                db.add(account)
            await db.flush()

            # --- upsert account_doctors 扩展表 ---
            default_role_id = await _get_default_role_id(db, "doctor")

            account_doctor = await db.get(AccountDoctor, doctor_id)
            if account_doctor:
                account_doctor.store_id = doctor.store_id
                account_doctor.department_id = doctor.department_id
                account_doctor.role_id = default_role_id
                account_doctor.banner = doctor.banner
                account_doctor.title = doctor.title
                account_doctor.years_of_experience = doctor.years_of_experience
                account_doctor.education = doctor.education
                account_doctor.graduate_school = doctor.graduate_school
                account_doctor.license_number = doctor.license_number
                account_doctor.license_image = doctor.license_image
                account_doctor.honors = doctor.honors
                account_doctor.schedule_desc = doctor.schedule_desc
                account_doctor.max_daily_appointments = doctor.max_daily_appointments
                account_doctor.online_consult_enabled = doctor.online_consult_enabled
                account_doctor.online_consult_fee = doctor.online_consult_fee
                account_doctor.page_style = doctor.page_style
                account_doctor.promo_video = doctor.promo_video
                account_doctor.tags = doctor.tags
                account_doctor.specialty = doctor.specialty
                account_doctor.introduction = doctor.introduction
                account_doctor.is_recommended = doctor.is_recommended
                account_doctor.sort_order = doctor.sort_order
                account_doctor.use_fee_template = doctor.use_fee_template
                account_doctor.deleted_at = doctor.deleted_at
                set_update_audit(account_doctor, operator_id)
            else:
                account_doctor = AccountDoctor(
                    account_id=doctor.id,
                    store_id=doctor.store_id,
                    department_id=doctor.department_id,
                    role_id=default_role_id,
                    banner=doctor.banner,
                    title=doctor.title,
                    years_of_experience=doctor.years_of_experience,
                    education=doctor.education,
                    graduate_school=doctor.graduate_school,
                    license_number=doctor.license_number,
                    license_image=doctor.license_image,
                    honors=doctor.honors,
                    schedule_desc=doctor.schedule_desc,
                    max_daily_appointments=doctor.max_daily_appointments,
                    online_consult_enabled=doctor.online_consult_enabled,
                    online_consult_fee=doctor.online_consult_fee,
                    page_style=doctor.page_style,
                    promo_video=doctor.promo_video,
                    tags=doctor.tags,
                    specialty=doctor.specialty,
                    introduction=doctor.introduction,
                    is_recommended=doctor.is_recommended,
                    sort_order=doctor.sort_order,
                    use_fee_template=doctor.use_fee_template,
                    deleted_at=doctor.deleted_at,
                )
                set_create_audit(account_doctor, operator_id)
                db.add(account_doctor)
            await db.flush()

            logger.info("双写同步: Doctor(id=%s) 同步到 accounts 成功", doctor_id)

        except Exception:
            logger.exception("双写同步: Doctor(id=%s) 同步失败", doctor_id)

    @staticmethod
    async def soft_delete_doctor_from_account(
        db: AsyncSession,
        doctor_id: str,
        operator_id: Optional[str] = None,
    ) -> None:
        """Doctor 软删除时同步到新表（设置 deleted_at + 禁用 status）"""
        if not _is_dual_write_enabled():
            return

        try:
            account = await db.get(Account, doctor_id)
            if account:
                account.status = 0
                set_update_audit(account, operator_id)

            account_doctor = await db.get(AccountDoctor, doctor_id)
            if account_doctor:
                from datetime import datetime
                account_doctor.deleted_at = datetime.now()
                set_update_audit(account_doctor, operator_id)

            await db.flush()
            logger.info("双写同步: Doctor(id=%s) 软删除同步成功", doctor_id)
        except Exception:
            logger.exception("双写同步: Doctor(id=%s) 软删除同步失败", doctor_id)

    # ------------------------------------------------------------------ #
    #  User 同步
    # ------------------------------------------------------------------ #

    @staticmethod
    async def sync_user_to_account(
        db: AsyncSession,
        user_id: str,
        operator_id: Optional[str] = None,
    ) -> None:
        """User 写操作后同步到 accounts + account_users

        使用 user.id 作为 account.id，保持 ID 一致。
        """
        if not _is_dual_write_enabled():
            return

        try:
            # 查询旧表记录
            user = await db.get(User, user_id)
            if not user:
                logger.warning("双写同步: User(id=%s) 不存在，跳过", user_id)
                return

            # --- upsert accounts 主表 ---
            account = await db.get(Account, user_id)
            if account:
                account.phone = user.phone
                account.username = user.phone  # 用户用手机号作登录账号
                account.password_hash = user.password_hash
                account.nickname = user.nickname
                account.name = user.nickname  # 用户暂无独立 name 字段
                account.avatar = user.avatar
                account.gender = user.gender if user.gender is not None else 0
                account.status = user.status
                account.tenant_id = user.tenant_id
                set_update_audit(account, operator_id)
            else:
                account = Account(
                    id=user.id,
                    tenant_id=user.tenant_id,
                    phone=user.phone,
                    username=user.phone,
                    password_hash=user.password_hash,
                    nickname=user.nickname,
                    name=user.nickname,
                    avatar=user.avatar,
                    gender=user.gender if user.gender is not None else 0,
                    status=user.status,
                )
                set_create_audit(account, operator_id)
                db.add(account)
            await db.flush()

            # --- upsert account_users 扩展表 ---
            default_role_id = await _get_default_role_id(db, "user")

            account_user = await db.get(AccountUser, user_id)
            if account_user:
                account_user.tenant_id = user.tenant_id
                account_user.role_id = default_role_id
                account_user.openid = user.openid
                account_user.unionid = user.unionid
                account_user.wechat_nickname = user.wechat_nickname
                account_user.wechat_avatar = user.wechat_avatar
                account_user.wechat_synced_at = user.wechat_synced_at
                account_user.points = user.points
                set_update_audit(account_user, operator_id)
            else:
                account_user = AccountUser(
                    account_id=user.id,
                    tenant_id=user.tenant_id,
                    role_id=default_role_id,
                    openid=user.openid,
                    unionid=user.unionid,
                    wechat_nickname=user.wechat_nickname,
                    wechat_avatar=user.wechat_avatar,
                    wechat_synced_at=user.wechat_synced_at,
                    points=user.points,
                )
                set_create_audit(account_user, operator_id)
                db.add(account_user)
            await db.flush()

            logger.info("双写同步: User(id=%s) 同步到 accounts 成功", user_id)

        except Exception:
            logger.exception("双写同步: User(id=%s) 同步失败", user_id)

    @staticmethod
    async def delete_user_from_account(
        db: AsyncSession,
        user_id: str,
    ) -> None:
        """User 删除时同步删除新表记录"""
        if not _is_dual_write_enabled():
            return

        try:
            account = await db.get(Account, user_id)
            if account:
                await db.delete(account)
                # account_users 通过 CASCADE 自动删除
                await db.flush()
                logger.info("双写同步: User(id=%s) 从 accounts 删除成功", user_id)
        except Exception:
            logger.exception("双写同步: User(id=%s) 删除同步失败", user_id)

    # ------------------------------------------------------------------ #
    #  通用字段更新
    # ------------------------------------------------------------------ #

    @staticmethod
    async def _update_account_field(
        db: AsyncSession,
        account_id: str,
        field: str,
        value,
    ) -> bool:
        """更新 Account 表的单个字段

        用于头像上传等需要更新 Account 表特定字段的场景。
        不受双写开关控制，始终执行。

        Args:
            db: 数据库会话
            account_id: 账号 ID
            field: 字段名
            value: 新值

        Returns:
            是否成功更新
        """
        try:
            account = await db.get(Account, account_id)
            if account and hasattr(account, field):
                setattr(account, field, value)
                await db.flush()
                return True
            return False
        except Exception:
            logger.exception(
                "更新 Account 字段失败: account_id=%s, field=%s",
                account_id, field,
            )
            return False
