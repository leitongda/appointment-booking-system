"""第三方平台组织架构同步服务。

从钉钉/企业微信/飞书拉取部门与成员，同步到本系统：
- 部门 → Department 表（按 name + tenant_id upsert）
- 成员 → Admin 表（按 phone upsert）+ IntegrationBinding（external_id 映射）

由于各平台 Provider 是异步实现，本服务通过 asyncio.run 在同步上下文调用。
"""
from __future__ import annotations

import asyncio
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.integrations import get_provider
from app.models.admin import Admin
from app.models.department import Department
from app.models.integration import Integration, IntegrationBinding

logger = structlog.get_logger(__name__)


class OrgSyncResult:
    """同步结果统计。"""

    def __init__(self, provider: str):
        self.provider = provider
        self.departments_total = 0
        self.departments_created = 0
        self.departments_updated = 0
        self.members_total = 0
        self.members_created = 0
        self.members_updated = 0
        self.bindings_created = 0
        self.errors: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "departments_total": self.departments_total,
            "departments_created": self.departments_created,
            "departments_updated": self.departments_updated,
            "members_total": self.members_total,
            "members_created": self.members_created,
            "members_updated": self.members_updated,
            "bindings_created": self.bindings_created,
            "errors": self.errors,
        }


def _load_integration(db: Session, tenant_id: str, provider: str) -> Integration | None:
    """加载租户集成配置。"""
    stmt = select(Integration).where(
        Integration.tenant_id == tenant_id,
        Integration.provider == provider,
        Integration.status == 1,
    )
    return db.execute(stmt).scalar_one_or_none()


def _upsert_department(
    db: Session,
    tenant_id: str,
    store_id: str | None,
    name: str,
    parent_id: str | None,
    external_dept_id: str,
    ext_dept_map: dict[str, str],
) -> tuple[Department, bool]:
    """upsert 部门（按 tenant_id + name 匹配）。

    返回 (department, created)。
    """
    stmt = select(Department).where(
        Department.tenant_id == tenant_id,
        Department.name == name,
    )
    dept = db.execute(stmt).scalar_one_or_none()
    if dept:
        ext_dept_map[external_dept_id] = dept.id
        return dept, False

    dept = Department(
        tenant_id=tenant_id,
        store_id=store_id,
        name=name,
        status=1,
    )
    db.add(dept)
    db.flush()
    ext_dept_map[external_dept_id] = dept.id
    return dept, True


def _upsert_member(
    db: Session,
    tenant_id: str,
    store_id: str | None,
    name: str,
    phone: str | None,
    email: str | None,
    external_id: str,
    union_id: str | None,
    provider: str,
) -> tuple[Admin, bool]:
    """upsert 成员（按 phone 匹配，无 phone 则按 external binding 查）。

    返回 (admin, created)。
    """
    created = False

    # 先按 phone 查
    admin = None
    if phone:
        stmt = select(Admin).where(
            Admin.tenant_id == tenant_id,
            Admin.phone == phone,
        )
        admin = db.execute(stmt).scalar_one_or_none()

    # 再按 external_id 查绑定
    if not admin:
        stmt = select(IntegrationBinding.user_id).where(
            IntegrationBinding.tenant_id == tenant_id,
            IntegrationBinding.provider == provider,
            IntegrationBinding.external_id == external_id,
        )
        uid = db.execute(stmt).scalar_one_or_none()
        if uid:
            admin = db.get(Admin, uid)

    if admin:
        # 更新信息
        if name and admin.name != name:
            admin.name = name
        if email and not admin.email:
            admin.email = email
        return admin, False

    # 不自动创建 Admin（需指定角色），仅记录待绑定
    # 实际场景：管理员应预先在系统创建，同步只做信息更新 + 绑定
    logger.info(
        "org_sync_member_not_found",
        provider=provider,
        external_id=external_id,
        name=name,
        phone=phone,
    )
    return None, False


def _upsert_binding(
    db: Session,
    tenant_id: str,
    admin_id: str,
    provider: str,
    external_id: str,
    union_id: str | None,
    name: str | None,
) -> bool:
    """upsert 绑定关系，返回是否新建。"""
    stmt = select(IntegrationBinding).where(
        IntegrationBinding.tenant_id == tenant_id,
        IntegrationBinding.provider == provider,
        IntegrationBinding.external_id == external_id,
    )
    binding = db.execute(stmt).scalar_one_or_none()
    if binding:
        if binding.user_id != admin_id:
            binding.user_id = admin_id
        if name and not binding.name:
            binding.name = name
        if union_id and not binding.union_id:
            binding.union_id = union_id
        return False

    binding = IntegrationBinding(
        tenant_id=tenant_id,
        user_id=admin_id,
        user_type="admin",
        provider=provider,
        external_id=external_id,
        union_id=union_id,
        name=name,
    )
    db.add(binding)
    return True


# ============================================================
# 同步主入口（同步函数，供 Celery / API 调用）
# ============================================================

def sync_organization(
    db: Session,
    tenant_id: str,
    provider: str,
    store_id: str | None = None,
) -> dict[str, Any]:
    """同步指定平台组织架构（部门 + 成员 + 绑定）。

    Args:
        db: 同步数据库会话
        tenant_id: 租户ID
        provider: 平台 dingtalk/wecom/feishu
        store_id: 关联门店ID（同步的部门挂到此门店）

    Returns:
        同步结果统计 dict
    """
    result = OrgSyncResult(provider)

    integration = _load_integration(db, tenant_id, provider)
    if not integration:
        result.errors.append(f"未配置 {provider} 集成或已禁用")
        return result.to_dict()

    impl = get_provider(provider)
    if not impl:
        result.errors.append(f"Provider {provider} 未注册")
        return result.to_dict()

    # 一次性把所有异步 API 调用放进单个事件循环，避免循环内反复 asyncio.run
    async def _fetch_all() -> tuple[list[dict], dict[str, list[dict]]]:
        departments = await impl.get_department_list(integration)
        members_by_dept: dict[str, list[dict]] = {}
        for dept in departments:
            ext_id = dept.get("dept_id")
            if not ext_id:
                continue
            try:
                members_by_dept[ext_id] = await impl.get_department_users(integration, ext_id)
            except Exception as e:
                logger.warning("org_sync_dept_users_failed", provider=provider, dept_id=ext_id, error=str(e))
                members_by_dept[ext_id] = []
        return departments, members_by_dept

    try:
        departments, members_by_dept = asyncio.run(_fetch_all())
    except Exception as e:
        logger.exception("org_sync_fetch_failed", provider=provider)
        result.errors.append(f"拉取组织数据失败: {e}")
        return result.to_dict()

    result.departments_total = len(departments)
    ext_dept_map: dict[str, str] = {}

    # 第一遍：创建部门（不处理 parent，因为可能顺序乱）
    for dept in departments:
        try:
            _, created = _upsert_department(
                db, tenant_id, store_id,
                name=dept.get("name") or dept.get("dept_id"),
                parent_id=None,
                external_dept_id=dept.get("dept_id"),
                ext_dept_map=ext_dept_map,
            )
            if created:
                result.departments_created += 1
            else:
                result.departments_updated += 1
        except Exception as e:
            result.errors.append(f"部门 {dept.get('name')} 同步失败: {e}")

    # 第二遍：建立父子关系
    for dept in departments:
        ext_id = dept.get("dept_id")
        parent_ext = dept.get("parent_id")
        if ext_id and parent_ext and ext_id in ext_dept_map and parent_ext in ext_dept_map:
            local_dept = db.get(Department, ext_dept_map[ext_id])
            if local_dept and not local_dept.parent_id:
                local_dept.parent_id = ext_dept_map[parent_ext]

    # 第三遍：同步成员（数据已在 _fetch_all 中拉取完毕，此处仅做 db 操作）
    for dept in departments:
        ext_dept_id = dept.get("dept_id")
        if not ext_dept_id:
            continue
        members = members_by_dept.get(ext_dept_id, [])
        result.members_total += len(members)
        for m in members:
            try:
                admin, created = _upsert_member(
                    db, tenant_id, store_id,
                    name=m.get("name"),
                    phone=m.get("phone"),
                    email=m.get("email"),
                    external_id=m.get("external_id"),
                    union_id=m.get("union_id"),
                    provider=provider,
                )
                if created:
                    result.members_created += 1
                elif admin:
                    result.members_updated += 1

                # 建立绑定（即使 admin 已存在也要确保绑定）
                if admin and m.get("external_id"):
                    is_new = _upsert_binding(
                        db, tenant_id, admin.id, provider,
                        m["external_id"], m.get("union_id"), m.get("name"),
                    )
                    if is_new:
                        result.bindings_created += 1
            except Exception as e:
                result.errors.append(f"成员 {m.get('name')} 同步失败: {e}")

    db.commit()
    logger.info("org_sync_completed", provider=provider, result=result.to_dict())
    return result.to_dict()
