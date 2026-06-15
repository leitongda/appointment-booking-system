"""同步账号查询辅助 -- 供 Celery 任务使用

所有查询采用 Account 表优先 + 旧表 fallback 策略：
1. 先查 Account 表
2. 找不到则查旧表（admins/doctors/users）
3. 返回统一格式的 dict

设计原则：
  - 导入放在函数内部，避免循环依赖
  - 使用同步 SQLAlchemy Session（Celery 上下文）
  - Account 查询用 try/except 包裹，表可能不存在或为空
"""

import logging

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
#  内部辅助：获取模型类（延迟导入，避免循环依赖）
# ------------------------------------------------------------------ #

def _get_account_model():
    from app.models.account import Account
    return Account


def _get_account_user_model():
    from app.models.account import AccountUser
    return AccountUser


def _get_account_admin_model():
    from app.models.account import AccountAdmin
    return AccountAdmin


def _get_account_doctor_model():
    from app.models.account import AccountDoctor
    return AccountDoctor


def _get_admin_model():
    from app.models.admin import Admin
    return Admin


def _get_doctor_model():
    from app.models.doctor import Doctor
    return Doctor


def _get_user_model():
    from app.models.user import User
    return User


# ------------------------------------------------------------------ #
#  公共 API
# ------------------------------------------------------------------ #

def get_account_phone(db: Session, user_id: str, user_type: str) -> str | None:
    """获取手机号

    查询顺序：Account -> 旧表 fallback
    """
    # 1. 尝试 Account 表
    try:
        Account = _get_account_model()
        account = db.get(Account, user_id)
        if account and account.phone:
            return account.phone
    except Exception:
        logger.debug("get_account_phone: Account 表查询异常，fallback 到旧表", exc_info=True)

    # 2. 旧表 fallback
    try:
        if user_type == "admin":
            Admin = _get_admin_model()
            row = db.get(Admin, user_id)
            return row.phone if row else None
        elif user_type == "doctor":
            Doctor = _get_doctor_model()
            row = db.get(Doctor, user_id)
            return row.phone if row else None
        elif user_type == "user":
            User = _get_user_model()
            row = db.get(User, user_id)
            return row.phone if row else None
    except Exception:
        logger.debug("get_account_phone: 旧表查询异常", exc_info=True)

    return None


def get_account_name(db: Session, user_id: str, user_type: str) -> str | None:
    """获取用户名/昵称

    查询顺序：Account -> 旧表 fallback
    """
    # 1. 尝试 Account 表
    try:
        Account = _get_account_model()
        account = db.get(Account, user_id)
        if account:
            # nickname 优先（用于显示），其次 name，最后 username
            return account.nickname or account.name or account.username
    except Exception:
        logger.debug("get_account_name: Account 表查询异常，fallback 到旧表", exc_info=True)

    # 2. 旧表 fallback
    try:
        if user_type == "admin":
            Admin = _get_admin_model()
            row = db.get(Admin, user_id)
            return row.name if row else None
        elif user_type == "doctor":
            Doctor = _get_doctor_model()
            row = db.get(Doctor, user_id)
            return row.name if row else None
        elif user_type == "user":
            User = _get_user_model()
            row = db.get(User, user_id)
            return row.nickname if row else None
    except Exception:
        logger.debug("get_account_name: 旧表查询异常", exc_info=True)

    return None


def get_account_openid(db: Session, user_id: str, user_type: str) -> str | None:
    """获取微信 openid

    查询顺序：AccountUser 扩展表 -> 旧 User 表 fallback
    注意：openid 只存在于 user 角色中。
    """
    # 1. 尝试 AccountUser 扩展表
    try:
        AccountUser = _get_account_user_model()
        ext = db.get(AccountUser, user_id)
        if ext and ext.openid:
            return ext.openid
    except Exception:
        logger.debug("get_account_openid: AccountUser 查询异常，fallback 到旧表", exc_info=True)

    # 2. 旧表 fallback（只有 user 有 openid）
    try:
        User = _get_user_model()
        row = db.get(User, user_id)
        return row.openid if row else None
    except Exception:
        logger.debug("get_account_openid: User 表查询异常", exc_info=True)

    return None


def get_user_info_for_reminder(db: Session, user_id: str) -> dict:
    """获取提醒所需的用户信息

    Returns:
        {"phone": Optional[str], "openid": Optional[str], "nickname": Optional[str]}
    """
    phone = None
    openid = None
    nickname = None

    # 1. 尝试 Account 表 + AccountUser 扩展表
    try:
        Account = _get_account_model()
        account = db.get(Account, user_id)
        if account:
            phone = account.phone
            nickname = account.nickname or account.name

            # 尝试从 AccountUser 获取 openid
            try:
                AccountUser = _get_account_user_model()
                ext = db.get(AccountUser, user_id)
                if ext:
                    openid = ext.openid
            except Exception:
                pass

            # 至少拿到了部分信息就直接返回
            if phone or openid or nickname:
                return {"phone": phone, "openid": openid, "nickname": nickname}
    except Exception:
        logger.debug("get_user_info_for_reminder: Account 表查询异常，fallback 到旧表", exc_info=True)

    # 2. 旧表 fallback
    try:
        User = _get_user_model()
        user = db.get(User, user_id)
        if user:
            return {
                "phone": phone or user.phone,
                "openid": openid or user.openid,
                "nickname": nickname or user.nickname,
            }
    except Exception:
        logger.debug("get_user_info_for_reminder: User 表查询异常", exc_info=True)

    return {"phone": phone, "openid": openid, "nickname": nickname}


def count_tenant_accounts(db: Session, tenant_id: str) -> dict:
    """统计租户下的各角色账号数量

    采用 Account 表优先 + 旧表 fallback 策略。

    Returns:
        {"admin_count": int, "doctor_count": int, "user_count": int}
    """
    result = {"admin_count": 0, "doctor_count": 0, "user_count": 0}

    # 1. 尝试从 Account 表统计
    try:
        Account = _get_account_model()
        AccountAdmin = _get_account_admin_model()
        AccountDoctor = _get_account_doctor_model()
        AccountUser = _get_account_user_model()

        admin_count = db.scalar(
            select(func.count(Account.id)).where(
                and_(
                    Account.tenant_id == tenant_id,
                    Account.id.in_(select(AccountAdmin.account_id)),
                    Account.status == 1,
                )
            )
        ) or 0

        doctor_count = db.scalar(
            select(func.count(Account.id)).where(
                and_(
                    Account.tenant_id == tenant_id,
                    Account.id.in_(select(AccountDoctor.account_id)),
                    Account.status == 1,
                )
            )
        ) or 0

        user_count = db.scalar(
            select(func.count(Account.id)).where(
                and_(
                    Account.tenant_id == tenant_id,
                    Account.id.in_(select(AccountUser.account_id)),
                    Account.status == 1,
                )
            )
        ) or 0

        # 如果 Account 表有数据，直接返回
        if admin_count > 0 or doctor_count > 0 or user_count > 0:
            result = {
                "admin_count": admin_count,
                "doctor_count": doctor_count,
                "user_count": user_count,
            }
            return result

    except Exception:
        logger.debug("count_tenant_accounts: Account 表查询异常，fallback 到旧表", exc_info=True)

    # 2. 旧表 fallback
    try:
        Admin = _get_admin_model()
        admin_count = db.scalar(
            select(func.count(Admin.id)).where(
                and_(Admin.tenant_id == tenant_id, Admin.status == 1)
            )
        ) or 0
        result["admin_count"] = admin_count
    except Exception:
        logger.debug("count_tenant_accounts: Admin 旧表查询异常", exc_info=True)

    try:
        Doctor = _get_doctor_model()
        from app.models.store import Store
        doctor_count = db.scalar(
            select(func.count(Doctor.id))
            .join(Store, Doctor.store_id == Store.id)
            .where(
                and_(
                    Store.tenant_id == tenant_id,
                    Doctor.status == 1,
                )
            )
        ) or 0
        result["doctor_count"] = doctor_count
    except Exception:
        logger.debug("count_tenant_accounts: Doctor 旧表查询异常", exc_info=True)

    try:
        User = _get_user_model()
        user_count = db.scalar(
            select(func.count(User.id)).where(
                and_(User.tenant_id == tenant_id, User.status == 1)
            )
        ) or 0
        result["user_count"] = user_count
    except Exception:
        logger.debug("count_tenant_accounts: User 旧表查询异常", exc_info=True)

    return result
