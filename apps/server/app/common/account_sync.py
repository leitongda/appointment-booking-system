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
from dataclasses import dataclass, field

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


async def _get_default_role_id(
    db: AsyncSession,
    role_type: str,
    tenant_id: str | None = None,
) -> str | None:
    """查询某角色类型的默认 role_id（租户优先，平台兜底）"""
    if tenant_id:
        tenant_result = await db.execute(
            select(Role.id).where(
                and_(
                    Role.role_type == role_type,
                    Role.is_default == True,
                    Role.status == 1,
                    Role.tenant_id == tenant_id,
                )
            ).limit(1)
        )
        tenant_role_id = tenant_result.scalar_one_or_none()
        if tenant_role_id:
            return tenant_role_id

    platform_result = await db.execute(
        select(Role.id).where(
            and_(
                Role.role_type == role_type,
                Role.is_default == True,
                Role.status == 1,
                Role.tenant_id.is_(None),
            )
        ).limit(1)
    )
    return platform_result.scalar_one_or_none()


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
        operator_id: str | None = None,
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
                account.email = admin.email
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
                    email=admin.email,
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
        operator_id: str | None = None,
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
            default_role_id = await _get_default_role_id(db, "doctor", doctor.tenant_id)

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
        operator_id: str | None = None,
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
        operator_id: str | None = None,
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
                account.email = user.email
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
                    email=user.email,
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
            default_role_id = await _get_default_role_id(db, "user", user.tenant_id)

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


# ------------------------------------------------------------------ #
#  数据一致性校验
# ------------------------------------------------------------------ #

# 需要对比的 accounts 主表核心字段（旧表字段名 -> 新表字段名相同）
_ACCOUNT_COMMON_FIELDS = (
    "phone", "email", "username", "password_hash",
    "name", "avatar", "status", "tenant_id",
)


@dataclass
class SyncDiff:
    """单条记录的字段级差异"""
    record_id: str
    record_type: str  # "admin" | "doctor" | "user"
    field_diffs: list[tuple[str, object, object]] = field(default_factory=list)
    # (field_name, old_table_value, new_table_value)


@dataclass
class ConsistencyReport:
    """一致性校验报告"""
    missing_in_new: list[tuple[str, str]] = field(default_factory=list)
    # (record_type, record_id) — 旧表有、新表无
    extra_in_new: list[tuple[str, str]] = field(default_factory=list)
    # (record_type, record_id) — 新表有、旧表无（可能已手动迁移）
    field_diffs: list[SyncDiff] = field(default_factory=list)
    # 字段级差异

    @property
    def total_issues(self) -> int:
        return len(self.missing_in_new) + len(self.extra_in_new) + len(self.field_diffs)

    @property
    def is_consistent(self) -> bool:
        return self.total_issues == 0


async def check_admin_consistency(
    db: AsyncSession,
    report: ConsistencyReport,
) -> None:
    """校验 Admin <-> AccountAdmin 数据一致性"""

    # 旧表所有 admin ID
    old_ids_result = await db.execute(select(Admin.id))
    old_ids = {row[0] for row in old_ids_result.all()}

    # 新表中 account_admins 的 account_id
    new_ids_result = await db.execute(select(AccountAdmin.account_id))
    new_ids = {row[0] for row in new_ids_result.all()}

    # 旧有新无
    for rid in old_ids - new_ids:
        report.missing_in_new.append(("admin", str(rid)))

    # 新有旧无
    for rid in new_ids - old_ids:
        report.extra_in_new.append(("admin", str(rid)))

    # 共有记录：逐字段对比
    common_ids = old_ids & new_ids
    if not common_ids:
        return

    for batch_start in range(0, len(common_ids), 500):
        batch = list(common_ids)[batch_start: batch_start + 500]
        old_result = await db.execute(select(Admin).where(Admin.id.in_(batch)))
        old_map = {str(r.id): r for r in old_result.scalars().all()}

        new_result = await db.execute(
            select(Account).where(Account.id.in_(batch))
        )
        new_map = {str(r.id): r for r in new_result.scalars().all()}

        for rid in batch:
            old = old_map.get(rid)
            new = new_map.get(rid)
            if not old or not new:
                continue

            diffs = []
            for f in _ACCOUNT_COMMON_FIELDS:
                old_val = getattr(old, f, None)
                new_val = getattr(new, f, None)
                if old_val != new_val:
                    diffs.append((f, old_val, new_val))

            if diffs:
                report.field_diffs.append(
                    SyncDiff(record_id=rid, record_type="admin", field_diffs=diffs)
                )


async def check_doctor_consistency(
    db: AsyncSession,
    report: ConsistencyReport,
) -> None:
    """校验 Doctor <-> AccountDoctor 数据一致性"""

    old_ids_result = await db.execute(select(Doctor.id))
    old_ids = {row[0] for row in old_ids_result.all()}

    new_ids_result = await db.execute(select(AccountDoctor.account_id))
    new_ids = {row[0] for row in new_ids_result.all()}

    for rid in old_ids - new_ids:
        report.missing_in_new.append(("doctor", str(rid)))

    for rid in new_ids - old_ids:
        report.extra_in_new.append(("doctor", str(rid)))

    common_ids = old_ids & new_ids
    if not common_ids:
        return

    for batch_start in range(0, len(common_ids), 500):
        batch = list(common_ids)[batch_start: batch_start + 500]
        old_result = await db.execute(select(Doctor).where(Doctor.id.in_(batch)))
        old_map = {str(r.id): r for r in old_result.scalars().all()}

        new_result = await db.execute(
            select(Account).where(Account.id.in_(batch))
        )
        new_map = {str(r.id): r for r in new_result.scalars().all()}

        for rid in batch:
            old = old_map.get(rid)
            new = new_map.get(rid)
            if not old or not new:
                continue

            diffs = []
            for f in _ACCOUNT_COMMON_FIELDS:
                old_val = getattr(old, f, None)
                new_val = getattr(new, f, None)
                # Doctor 的 gender 可能为 None，默认 0
                if f == "gender":
                    old_val = old_val if old_val is not None else 0
                    new_val = new_val if new_val is not None else 0
                if old_val != new_val:
                    diffs.append((f, old_val, new_val))

            if diffs:
                report.field_diffs.append(
                    SyncDiff(record_id=rid, record_type="doctor", field_diffs=diffs)
                )


async def check_user_consistency(
    db: AsyncSession,
    report: ConsistencyReport,
) -> None:
    """校验 User <-> AccountUser 数据一致性"""

    old_ids_result = await db.execute(select(User.id))
    old_ids = {row[0] for row in old_ids_result.all()}

    new_ids_result = await db.execute(select(AccountUser.account_id))
    new_ids = {row[0] for row in new_ids_result.all()}

    for rid in old_ids - new_ids:
        report.missing_in_new.append(("user", str(rid)))

    for rid in new_ids - old_ids:
        report.extra_in_new.append(("user", str(rid)))

    common_ids = old_ids & new_ids
    if not common_ids:
        return

    for batch_start in range(0, len(common_ids), 500):
        batch = list(common_ids)[batch_start: batch_start + 500]
        old_result = await db.execute(select(User).where(User.id.in_(batch)))
        old_map = {str(r.id): r for r in old_result.scalars().all()}

        new_result = await db.execute(
            select(Account).where(Account.id.in_(batch))
        )
        new_map = {str(r.id): r for r in new_result.scalars().all()}

        for rid in batch:
            old = old_map.get(rid)
            new = new_map.get(rid)
            if not old or not new:
                continue

            diffs = []
            # User 特殊字段映射
            user_field_map = {
                "phone": "phone",
                "email": "email",
                "nickname": "nickname",
                "avatar": "avatar",
                "status": "status",
                "tenant_id": "tenant_id",
            }
            for old_field, new_field in user_field_map.items():
                old_val = getattr(old, old_field, None)
                new_val = getattr(new, new_field, None)
                # User 的 gender
                if old_field == "nickname":
                    # Account.name 对应 User.nickname
                    new_val = getattr(new, "name", None)
                if old_val != new_val:
                    diffs.append((old_field, old_val, new_val))

            if diffs:
                report.field_diffs.append(
                    SyncDiff(record_id=rid, record_type="user", field_diffs=diffs)
                )


async def check_account_sync_consistency(
    db: AsyncSession,
) -> ConsistencyReport:
    """全量校验旧表与新表的数据一致性

    对比 admins/doctors/users 与 accounts + 扩展表的：
      1. 记录覆盖完整性（旧表有但新表无 / 新表多出）
      2. 核心字段值一致性

    Returns:
        ConsistencyReport 校验报告
    """
    report = ConsistencyReport()

    await check_admin_consistency(db, report)
    await check_doctor_consistency(db, report)
    await check_user_consistency(db, report)

    logger.info(
        "数据一致性校验完成: missing=%d, extra=%d, field_diffs=%d, total_issues=%d",
        len(report.missing_in_new),
        len(report.extra_in_new),
        len(report.field_diffs),
        report.total_issues,
    )

    return report
