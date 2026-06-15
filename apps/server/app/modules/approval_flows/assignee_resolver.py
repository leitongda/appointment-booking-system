"""审批人解析器 - 根据节点配置解析具体审批人"""
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AssigneeResolver:
    """根据节点的 assignee_type + assignee_config 解析审批人列表"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve(
        self,
        node,  # ApprovalFlowNode
        instance,  # ApprovalInstance
    ) -> list[dict[str, str]]:
        """
        解析审批人列表。

        Returns:
            [{"id": "xxx", "name": "张三"}, ...]
        """
        assignee_type = node.assignee_type
        config = node.assignee_config or {}

        if assignee_type == "role":
            return await self._resolve_by_role(config, instance)
        elif assignee_type == "user":
            return self._resolve_by_user(config)
        elif assignee_type == "department":
            return await self._resolve_by_department(config, instance)
        elif assignee_type == "dynamic":
            return self._resolve_dynamic(config, instance)
        else:
            logger.warning(f"未知的审批人类型: {assignee_type}")
            return []

    async def _resolve_by_role(
        self,
        config: dict[str, Any],
        instance,
    ) -> list[dict[str, str]]:
        """按角色解析审批人 - 查找拥有指定角色的所有管理员"""
        role_codes = config.get("role_codes", [])
        if not role_codes:
            return []

        from app.models.admin import Admin, Role

        # 查找拥有指定角色的管理员
        stmt = (
            select(Admin.id, Admin.name)
            .join(Role, Admin.role_id == Role.id)
            .where(
                Admin.deleted_at.is_(None),
                Admin.is_active == True,
                Role.code.in_(role_codes),
            )
        )

        # 租户隔离
        if instance.tenant_id:
            stmt = stmt.where(Admin.tenant_id == instance.tenant_id)

        # 门店过滤
        if config.get("same_store") and instance.store_id:
            stmt = stmt.where(Admin.store_id == instance.store_id)

        result = await self.db.execute(stmt)
        rows = result.all()
        return [{"id": row.id, "name": row.name} for row in rows]

    def _resolve_by_user(self, config: dict[str, Any]) -> list[dict[str, str]]:
        """指定人员"""
        user_ids = config.get("user_ids", [])
        user_names = config.get("user_names", [])
        if not user_ids:
            return []

        result = []
        for i, uid in enumerate(user_ids):
            name = user_names[i] if i < len(user_names) else ""
            result.append({"id": uid, "name": name})
        return result

    async def _resolve_by_department(
        self,
        config: dict[str, Any],
        instance,
    ) -> list[dict[str, str]]:
        """按科室负责人解析"""
        # 从 form_data 中获取科室 ID
        dept_field = config.get("dept_field", "department_id")
        dept_id = instance.form_data.get(dept_field)
        if not dept_id:
            return []

        from app.models.department import Department

        stmt = select(Department).where(Department.id == dept_id)
        result = await self.db.execute(stmt)
        dept = result.scalar_one_or_none()

        if dept and dept.head_id:
            return [{"id": dept.head_id, "name": dept.head_name or ""}]
        return []

    def _resolve_dynamic(
        self,
        config: dict[str, Any],
        instance,
    ) -> list[dict[str, str]]:
        """从表单数据中动态获取审批人"""
        field_name = config.get("field_name", "approver_id")
        name_field = config.get("name_field", "approver_name")

        approver_id = instance.form_data.get(field_name)
        if not approver_id:
            return []

        approver_name = instance.form_data.get(name_field, "")
        return [{"id": str(approver_id), "name": str(approver_name)}]
