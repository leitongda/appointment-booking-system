"""审批实例服务"""
import logging
from typing import Optional, List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.approval_flow import ApprovalInstance, ApprovalRecord, ApprovalTask
from app.modules.approval_flows.engine import ApprovalEngine
from app.modules.approval_flows.schemas import ApprovalQuery
from app.middleware.tenant_context import get_current_tenant_id

logger = logging.getLogger(__name__)


class ApprovalInstanceService:
    """审批实例服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.engine = ApprovalEngine(db)

    async def get_list(
        self,
        query: ApprovalQuery,
        user_id: Optional[str] = None,
        view: str = "pending",
    ) -> Tuple[List[ApprovalInstance], int]:
        """获取审批实例列表"""
        stmt = select(ApprovalInstance)
        count_stmt = select(func.count(ApprovalInstance.id))

        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(ApprovalInstance.tenant_id == tenant_id)
            count_stmt = count_stmt.where(ApprovalInstance.tenant_id == tenant_id)

        if query.status:
            stmt = stmt.where(ApprovalInstance.status == query.status)
            count_stmt = count_stmt.where(ApprovalInstance.status == query.status)

        if query.business_type:
            stmt = stmt.where(ApprovalInstance.business_type == query.business_type)
            count_stmt = count_stmt.where(ApprovalInstance.business_type == query.business_type)

        if query.store_id:
            stmt = stmt.where(ApprovalInstance.store_id == query.store_id)
            count_stmt = count_stmt.where(ApprovalInstance.store_id == query.store_id)

        if view == "initiated" and user_id:
            # 我发起的
            stmt = stmt.where(ApprovalInstance.applicant_id == user_id)
            count_stmt = count_stmt.where(ApprovalInstance.applicant_id == user_id)
        elif view == "done" and user_id:
            # 我的已办: 我已有 approve/reject/delegate/comment 操作记录的实例
            done_subquery = select(ApprovalRecord.instance_id).where(
                and_(
                    ApprovalRecord.approver_id == user_id,
                    ApprovalRecord.action.in_(["approve", "reject", "delegate", "comment"]),
                )
            )
            stmt = stmt.where(ApprovalInstance.id.in_(done_subquery))
            count_stmt = count_stmt.where(ApprovalInstance.id.in_(done_subquery))
        elif user_id:
            # 我待办的: ApprovalTask 中 assignee_id = user_id 且 status = pending
            stmt = stmt.where(
                ApprovalInstance.status == "pending",
                ApprovalInstance.id.in_(
                    select(ApprovalTask.instance_id).where(
                        and_(
                            ApprovalTask.assignee_id == user_id,
                            ApprovalTask.status == "pending",
                        )
                    )
                ),
            )
            count_stmt = count_stmt.where(
                ApprovalInstance.status == "pending",
                ApprovalInstance.id.in_(
                    select(ApprovalTask.instance_id).where(
                        and_(
                            ApprovalTask.assignee_id == user_id,
                            ApprovalTask.status == "pending",
                        )
                    )
                ),
            )

        stmt = stmt.order_by(ApprovalInstance.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)

        result = await self.db.execute(stmt)
        count_result = await self.db.execute(count_stmt)

        return list(result.scalars().all()), count_result.scalar() or 0

    async def get_my_pending(
        self,
        user_id: str,
        query: ApprovalQuery,
    ) -> Tuple[List[ApprovalInstance], int]:
        """获取我的待办列表"""
        pending_subquery = (
            select(ApprovalTask.instance_id)
            .where(
                and_(
                    ApprovalTask.assignee_id == user_id,
                    ApprovalTask.status == "pending",
                )
            )
            .scalar_subquery()
        )
        stmt = select(ApprovalInstance).where(
            ApprovalInstance.status == "pending",
            ApprovalInstance.id.in_(pending_subquery),
        )
        count_stmt = select(func.count(ApprovalInstance.id)).where(
            ApprovalInstance.status == "pending",
            ApprovalInstance.id.in_(pending_subquery),
        )

        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(ApprovalInstance.tenant_id == tenant_id)
            count_stmt = count_stmt.where(ApprovalInstance.tenant_id == tenant_id)

        if query.business_type:
            stmt = stmt.where(ApprovalInstance.business_type == query.business_type)
            count_stmt = count_stmt.where(ApprovalInstance.business_type == query.business_type)

        stmt = stmt.order_by(ApprovalInstance.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)

        result = await self.db.execute(stmt)
        count_result = await self.db.execute(count_stmt)

        return list(result.scalars().all()), count_result.scalar() or 0

    async def get_by_id(self, instance_id: str) -> Optional[ApprovalInstance]:
        """获取实例详情"""
        stmt = select(ApprovalInstance).where(ApprovalInstance.id == instance_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_business(self, business_type: str, business_id: str) -> Optional[ApprovalInstance]:
        """按业务 ID 获取实例"""
        stmt = select(ApprovalInstance).where(
            and_(
                ApprovalInstance.business_type == business_type,
                ApprovalInstance.business_id == business_id,
            )
        )
        stmt = stmt.order_by(ApprovalInstance.created_at.desc())
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def approve(
        self,
        instance_id: str,
        approver_id: str,
        approver_name: str = "",
        comment: Optional[str] = None,
    ) -> ApprovalInstance:
        """审批通过"""
        return await self.engine.approve(instance_id, approver_id, approver_name, comment)

    async def reject(
        self,
        instance_id: str,
        approver_id: str,
        approver_name: str = "",
        comment: Optional[str] = None,
    ) -> ApprovalInstance:
        """审批拒绝"""
        return await self.engine.reject(instance_id, approver_id, approver_name, comment)

    async def delegate(
        self,
        instance_id: str,
        approver_id: str,
        approver_name: str,
        target_user_id: str,
        target_user_name: str = "",
        comment: Optional[str] = None,
    ) -> ApprovalInstance:
        """转交"""
        return await self.engine.delegate(
            instance_id, approver_id, approver_name,
            target_user_id, target_user_name, comment,
        )

    async def withdraw(self, instance_id: str, user_id: str) -> ApprovalInstance:
        """撤回"""
        return await self.engine.withdraw(instance_id, user_id)

    async def get_pending_count(self, user_id: str) -> int:
        """获取待办数量"""
        stmt = select(func.count(ApprovalInstance.id)).where(
            and_(
                ApprovalInstance.status == "pending",
                ApprovalInstance.id.in_(
                    select(ApprovalTask.instance_id).where(
                        and_(
                            ApprovalTask.assignee_id == user_id,
                            ApprovalTask.status == "pending",
                        )
                    )
                ),
            )
        )
        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(ApprovalInstance.tenant_id == tenant_id)

        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def get_progress(self, instance_id: str) -> dict:
        """获取审批进度"""
        return await self.engine.get_approval_progress(instance_id)
