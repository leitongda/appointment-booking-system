"""知识库可见性与权限级别判定

可见 = 自有 ∪ 租户公共 ∪ 被共享（按同事 / 按角色） ∪ 持 knowledge:manage 时租户内全部。
级别：owner（owner 本人或 manage）> edit（共享 edit）> read（共享 read / 租户公共）。
不可见 → 404（不泄露存在性）；可见但级别不足 → 403。
"""
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.role_permissions import check_permission_match
from app.enums.knowledge import (
    KnowledgeShareGrantee,
    KnowledgeSharePermission,
    KnowledgeVisibility,
)
from app.models.admin import Admin
from app.models.knowledge import KnowledgeBase, KnowledgeShare
from app.modules.knowledge.exceptions import KnowledgeForbidden, KnowledgeNotFound

_LEVEL_RANK = {"read": 0, "edit": 1, "owner": 2}
_UNSET = object()


class KnowledgeAccessService:
    def __init__(self, db: AsyncSession, admin: dict, tenant_id: str | None):
        self.db = db
        self.admin = admin
        self.admin_id: str | None = admin.get("id")
        self.tenant_id = tenant_id
        self._role_id = _UNSET

    @property
    def can_manage(self) -> bool:
        if self.admin.get("is_super_admin"):
            return True
        permissions = set(self.admin.get("permissions") or [])
        return "*" in permissions or check_permission_match("knowledge:manage", permissions)

    async def role_id(self) -> str | None:
        """当前管理员的角色 id（dict 里没有就查库），结果缓存"""
        if self._role_id is _UNSET:
            role_id = self.admin.get("role_id")
            if not role_id and self.admin_id:
                result = await self.db.execute(select(Admin.role_id).where(Admin.id == self.admin_id))
                role_id = result.scalar_one_or_none()
            self._role_id = role_id
        return self._role_id

    def _share_condition(self):
        """共享记录命中当前用户（按人或按角色）的条件；调用前须 await role_id()"""
        role_id = self._role_id if self._role_id is not _UNSET else None
        conditions = [
            and_(
                KnowledgeShare.grantee_type == KnowledgeShareGrantee.ADMIN.value,
                KnowledgeShare.grantee_id == self.admin_id,
            )
        ]
        if role_id:
            conditions.append(
                and_(
                    KnowledgeShare.grantee_type == KnowledgeShareGrantee.ROLE.value,
                    KnowledgeShare.grantee_id == role_id,
                )
            )
        return or_(*conditions)

    async def shared_kb_ids_subquery(self):
        await self.role_id()
        return select(KnowledgeShare.kb_id).where(self._share_condition())

    async def visible_kb_ids(self) -> set[str] | None:
        """返回可见知识库 id 集合；None 表示租户内全部可见（manage）"""
        if self.can_manage:
            return None
        stmt = select(KnowledgeBase.id).where(
            or_(
                KnowledgeBase.owner_admin_id == self.admin_id,
                KnowledgeBase.visibility == KnowledgeVisibility.TENANT.value,
                KnowledgeBase.id.in_(await self.shared_kb_ids_subquery()),
            )
        )
        if self.tenant_id:
            stmt = stmt.where(KnowledgeBase.tenant_id == self.tenant_id)
        result = await self.db.execute(stmt)
        return set(result.scalars().all())

    async def permission_for(self, kb: KnowledgeBase) -> str | None:
        """当前用户对知识库的级别：owner / edit / read / None（不可见）"""
        if self.tenant_id and kb.tenant_id != self.tenant_id:
            return None
        if self.can_manage or kb.owner_admin_id == self.admin_id:
            return "owner"

        await self.role_id()
        stmt = select(KnowledgeShare.permission).where(KnowledgeShare.kb_id == kb.id, self._share_condition())
        result = await self.db.execute(stmt)
        granted = set(result.scalars().all())
        if KnowledgeSharePermission.EDIT.value in granted:
            return "edit"
        if granted or kb.visibility == KnowledgeVisibility.TENANT.value:
            return "read"
        return None

    async def require(self, kb: KnowledgeBase | None, level: str) -> str:
        """校验级别；不可见抛 404，级别不足抛 403；返回实际级别"""
        if kb is None:
            raise KnowledgeNotFound("知识库不存在")
        permission = await self.permission_for(kb)
        if permission is None:
            raise KnowledgeNotFound("知识库不存在")
        if _LEVEL_RANK[permission] < _LEVEL_RANK[level]:
            raise KnowledgeForbidden("无权执行此操作")
        return permission
