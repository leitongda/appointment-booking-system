"""审批流引擎核心

负责:
- 发起审批 (start_instance)
- 审批通过 (approve)
- 审批拒绝 (reject)
- 转交 (delegate)
- 撤回 (withdraw)
- 节点推进 (_advance_to_next_node)
- 会签/或签判断 (_check_approval_complete)

增强:
- Redis 分布式锁保护并发审批
- ApprovalTask 任务管理（分离任务和审计语义）
- Celery 异步通知
- structlog 结构化日志
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models.approval_flow import (
    ApprovalFlowDefinition,
    ApprovalFlowNode,
    ApprovalFlowCondition,
    ApprovalInstance,
    ApprovalRecord,
    ApprovalTask,
)
from app.modules.approval_flows.assignee_resolver import AssigneeResolver
from app.modules.approval_flows.condition_evaluator import ConditionEvaluator
from app.modules.approval_flows.callback_registry import callback_registry
from app.middleware.tenant_context import get_current_tenant_id

logger = structlog.get_logger(__name__)


class FlowNotFoundError(Exception):
    """未找到激活的流程定义"""
    pass


class ApprovalEngine:
    """审批流引擎核心"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.assignee_resolver = AssigneeResolver(db)
        self.condition_evaluator = ConditionEvaluator()

    # ============================================================
    # 发起审批
    # ============================================================

    async def start_instance(
        self,
        business_type: str,
        business_id: str,
        form_data: Dict[str, Any],
        applicant_id: str,
        title: str,
        applicant_name: str = "",
        flow_def_id: Optional[str] = None,
        store_id: Optional[str] = None,
    ) -> ApprovalInstance:
        """发起审批：创建实例，推进到第一个审批节点。

        业务模块接入指南:
        1. 发起端: 在创建申请时调用本方法，捕获 FlowNotFoundError 作为无流程定义的 fallback
        2. 回调端: 通过 callback_registry.register(business_type, handler) 注册回调，
           处理 on_approved / on_rejected / on_cancelled 事件，执行业务逻辑
        3. 已接入的业务类型: leave_request, extra_quota (见 business_callbacks.py)
        """
        tenant_id = get_current_tenant_id()

        # 查找流程定义
        if flow_def_id:
            flow_def = await self._get_flow_def(flow_def_id)
        else:
            flow_def = await self._get_active_flow_def(business_type, tenant_id)

        if not flow_def:
            raise FlowNotFoundError(f"未找到业务类型 {business_type} 的激活流程定义")

        # 加载节点和条件
        nodes = await self._load_nodes(flow_def.id)
        if not nodes:
            raise ValueError("流程定义没有节点")

        # 找到 start 节点
        start_node = next((n for n in nodes if n.node_type == "start"), None)
        if not start_node:
            raise ValueError("流程定义缺少 start 节点")

        # 找到第一个审批节点
        first_approval_node = await self._find_next_node(
            start_node, nodes, form_data
        )
        if not first_approval_node:
            raise ValueError("start 节点后没有审批节点")

        # 创建实例
        instance = ApprovalInstance(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            flow_def_id=flow_def.id,
            business_type=business_type,
            business_id=business_id,
            title=title,
            form_data=form_data,
            status="pending",
            current_node_key=first_approval_node.node_key,
            applicant_id=applicant_id,
            applicant_name=applicant_name,
            store_id=store_id,
            created_by=applicant_id,
            updated_by=applicant_id,
        )
        self.db.add(instance)
        await self.db.flush()

        # 解析审批人并创建任务
        await self._create_tasks_for_node(first_approval_node, instance, tenant_id, store_id)

        # 检查自动审批
        auto_approved = await self._try_auto_approve(first_approval_node, instance, form_data)

        logger.info(
            "approval_started",
            business_type=business_type,
            business_id=business_id,
            instance_id=instance.id,
            flow_def_id=flow_def.id,
            first_node=first_approval_node.node_name,
        )
        return instance

    # ============================================================
    # 审批通过（Redis 锁保护）
    # ============================================================

    async def approve(
        self,
        instance_id: str,
        approver_id: str,
        approver_name: str = "",
        comment: Optional[str] = None,
    ) -> ApprovalInstance:
        """审批通过（带 Redis 分布式锁）"""
        from app.core.redis import RedisCache

        lock_name = f"approval:instance:{instance_id}"
        lock_value = await RedisCache.acquire_lock(lock_name, timeout=10, retry_times=3, retry_delay=0.1)
        if not lock_value:
            raise ValueError("操作过于频繁，请稍后重试")
        try:
            return await self._do_approve(instance_id, approver_id, approver_name, comment)
        finally:
            await RedisCache.release_lock(lock_name, lock_value)

    async def _do_approve(
        self,
        instance_id: str,
        approver_id: str,
        approver_name: str = "",
        comment: Optional[str] = None,
    ) -> ApprovalInstance:
        """审批通过（内部实现）"""
        instance = await self._get_instance(instance_id)
        self._validate_instance_pending(instance)

        current_node = await self._get_current_node(instance)
        if not current_node:
            raise ValueError("当前节点不存在")

        await self._validate_approver(instance, current_node, approver_id)

        # 查找并完成任务
        task = await self._find_pending_task(instance_id, current_node.node_key, approver_id)
        if not task:
            raise ValueError("当前用户没有待处理的审批任务")

        task.status = "completed"
        task.completed_at = datetime.utcnow()
        task.completed_by = approver_id

        # 创建审批记录（保留审计）
        record = ApprovalRecord(
            id=str(uuid.uuid4()),
            instance_id=instance.id,
            node_key=current_node.node_key,
            node_name=current_node.node_name,
            approver_id=approver_id,
            approver_name=approver_name,
            action="approve",
            comment=comment,
        )
        self.db.add(record)

        # 判断是否满足推进条件
        should_advance = await self._check_approval_complete(
            current_node, instance.id, current_node.node_key
        )

        if should_advance:
            await self._cancel_pending_tasks(instance.id, current_node.node_key)
            await self._advance(instance, current_node)

        instance.updated_by = approver_id
        await self.db.flush()

        logger.info(
            "approval_approved",
            instance_id=instance_id,
            approver_id=approver_id,
            node_key=current_node.node_key,
            should_advance=should_advance,
        )
        return instance

    # ============================================================
    # 审批拒绝（Redis 锁保护）
    # ============================================================

    async def reject(
        self,
        instance_id: str,
        approver_id: str,
        approver_name: str = "",
        comment: Optional[str] = None,
    ) -> ApprovalInstance:
        """审批拒绝（带 Redis 分布式锁）"""
        from app.core.redis import RedisCache

        lock_name = f"approval:instance:{instance_id}"
        lock_value = await RedisCache.acquire_lock(lock_name, timeout=10, retry_times=3, retry_delay=0.1)
        if not lock_value:
            raise ValueError("操作过于频繁，请稍后重试")
        try:
            return await self._do_reject(instance_id, approver_id, approver_name, comment)
        finally:
            await RedisCache.release_lock(lock_name, lock_value)

    async def _do_reject(
        self,
        instance_id: str,
        approver_id: str,
        approver_name: str = "",
        comment: Optional[str] = None,
    ) -> ApprovalInstance:
        """审批拒绝（内部实现）"""
        instance = await self._get_instance(instance_id)
        self._validate_instance_pending(instance)

        current_node = await self._get_current_node(instance)
        if not current_node:
            raise ValueError("当前节点不存在")

        await self._validate_approver(instance, current_node, approver_id)

        # 查找并完成任务
        task = await self._find_pending_task(instance_id, current_node.node_key, approver_id)
        if not task:
            raise ValueError("当前用户没有待处理的审批任务")

        task.status = "completed"
        task.completed_at = datetime.utcnow()
        task.completed_by = approver_id

        # 创建拒绝记录
        record = ApprovalRecord(
            id=str(uuid.uuid4()),
            instance_id=instance.id,
            node_key=current_node.node_key,
            node_name=current_node.node_name,
            approver_id=approver_id,
            approver_name=approver_name,
            action="reject",
            comment=comment,
        )
        self.db.add(record)

        # 取消所有 pending 任务
        await self._cancel_pending_tasks(instance.id)

        # 终止流程
        instance.status = "rejected"
        instance.rejected_at = datetime.utcnow()
        instance.completed_reason = "normal"
        instance.updated_by = approver_id

        await self.db.flush()

        # 执行回调
        logger.info(
            "callback_started",
            instance_id=instance.id,
            business_type=instance.business_type,
            callback="on_rejected",
        )
        try:
            await callback_registry.execute(
                instance.business_type, "on_rejected", instance, self.db
            )
        except Exception as e:
            logger.error(
                "callback_failed",
                instance_id=instance.id,
                business_type=instance.business_type,
                callback="on_rejected",
                error=str(e),
            )
            raise

        # 通知申请人
        await self._notify_applicant(instance, "rejected")

        logger.info("approval_rejected", instance_id=instance_id, approver_id=approver_id)
        return instance

    # ============================================================
    # 转交
    # ============================================================

    async def delegate(
        self,
        instance_id: str,
        approver_id: str,
        approver_name: str,
        target_user_id: str,
        target_user_name: str = "",
        comment: Optional[str] = None,
    ) -> ApprovalInstance:
        """转交给他人审批"""
        instance = await self._get_instance(instance_id)
        self._validate_instance_pending(instance)

        current_node = await self._get_current_node(instance)
        if not current_node:
            raise ValueError("当前节点不存在")

        await self._validate_approver(instance, current_node, approver_id)

        # 原任务标记为 transferred
        task = await self._find_pending_task(instance_id, current_node.node_key, approver_id)
        if task:
            task.status = "transferred"
            task.completed_at = datetime.utcnow()
            task.completed_by = approver_id

        # 创建新任务
        tenant_id = get_current_tenant_id()
        new_task = ApprovalTask(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            store_id=instance.store_id,
            instance_id=instance.id,
            node_key=current_node.node_key,
            node_name=current_node.node_name,
            task_type="approval",
            status="pending",
            assignee_id=target_user_id,
            assignee_name=target_user_name,
            assignee_snapshot={
                "id": target_user_id,
                "name": target_user_name,
                "delegated_from": approver_id,
                "delegated_from_name": approver_name,
            },
        )
        self.db.add(new_task)

        # 创建转交记录
        record = ApprovalRecord(
            id=str(uuid.uuid4()),
            instance_id=instance.id,
            node_key=current_node.node_key,
            node_name=current_node.node_name,
            approver_id=approver_id,
            approver_name=approver_name,
            action="delegate",
            comment=comment,
            delegate_to=target_user_id,
        )
        self.db.add(record)

        # 通知被转交人
        await self._notify_approver(target_user_id, instance, current_node.node_name)

        instance.updated_by = approver_id
        await self.db.flush()

        logger.info(
            "approval_delegated",
            instance_id=instance_id,
            from_user=approver_id,
            to_user=target_user_id,
        )
        return instance

    # ============================================================
    # 撤回
    # ============================================================

    async def withdraw(
        self,
        instance_id: str,
        user_id: str,
    ) -> ApprovalInstance:
        """撤回审批（仅发起人可操作）"""
        instance = await self._get_instance(instance_id)

        if instance.applicant_id != user_id:
            raise ValueError("仅发起人可以撤回")

        if instance.status != "pending":
            raise ValueError("当前状态不允许撤回")

        # 检查是否已有审批记录（有人审批过则不能撤回）
        stmt = select(ApprovalRecord).where(
            and_(
                ApprovalRecord.instance_id == instance_id,
                ApprovalRecord.action.in_(["approve", "reject"]),
            )
        )
        result = await self.db.execute(stmt)
        if result.scalars().first():
            raise ValueError("已有审批记录，无法撤回")

        # 取消所有 pending 任务
        await self._cancel_pending_tasks(instance.id)

        instance.status = "withdrawn"
        instance.cancelled_at = datetime.utcnow()
        instance.completed_reason = "normal"
        instance.updated_by = user_id

        await self.db.flush()

        # 执行回调
        logger.info(
            "callback_started",
            instance_id=instance.id,
            business_type=instance.business_type,
            callback="on_cancelled",
        )
        try:
            await callback_registry.execute(
                instance.business_type, "on_cancelled", instance, self.db
            )
        except Exception as e:
            logger.error(
                "callback_failed",
                instance_id=instance.id,
                business_type=instance.business_type,
                callback="on_cancelled",
                error=str(e),
            )
            raise

        logger.info("approval_withdrawn", instance_id=instance_id, user_id=user_id)
        return instance

    # ============================================================
    # 查询
    # ============================================================

    async def get_pending_approvers(self, instance_id: str) -> List[Dict[str, str]]:
        """获取当前待审批人列表（基于 ApprovalTask）"""
        instance = await self._get_instance(instance_id)
        if instance.status != "pending":
            return []

        current_node = await self._get_current_node(instance)
        if not current_node:
            return []

        # 查询 pending 任务
        stmt = select(ApprovalTask).where(
            and_(
                ApprovalTask.instance_id == instance_id,
                ApprovalTask.node_key == current_node.node_key,
                ApprovalTask.status == "pending",
                ApprovalTask.task_type == "approval",
            )
        )
        result = await self.db.execute(stmt)
        tasks = result.scalars().all()

        return [
            {"id": t.assignee_id, "name": t.assignee_name or ""}
            for t in tasks
        ]

    async def get_approval_progress(self, instance_id: str) -> Dict[str, Any]:
        """获取审批进度"""
        instance = await self._get_instance(instance_id)
        current_node = await self._get_current_node(instance)

        if not current_node or instance.status != "pending":
            return {"status": instance.status, "current_node": None, "progress": None}

        # 查询任务状态
        stmt = select(ApprovalTask).where(
            and_(
                ApprovalTask.instance_id == instance_id,
                ApprovalTask.node_key == current_node.node_key,
                ApprovalTask.task_type == "approval",
            )
        )
        result = await self.db.execute(stmt)
        tasks = result.scalars().all()

        completed_count = sum(1 for t in tasks if t.status == "completed")

        return {
            "status": instance.status,
            "current_node": current_node.node_name,
            "approval_mode": current_node.approval_mode,
            "total_approvers": len(tasks),
            "approved_count": completed_count,
            "approvers": [
                {
                    "id": t.assignee_id,
                    "name": t.assignee_name or "",
                    "approved": t.status == "completed",
                }
                for t in tasks
            ],
        }

    # ============================================================
    # 内部方法 - 任务管理
    # ============================================================

    async def _create_tasks_for_node(
        self,
        node: ApprovalFlowNode,
        instance: ApprovalInstance,
        tenant_id: Optional[str],
        store_id: Optional[str],
    ):
        """为审批节点创建任务"""
        approvers = await self.assignee_resolver.resolve(node, instance)

        logger.info(
            "assignee_resolved",
            instance_id=instance.id,
            node_key=node.node_key,
            assignee_type=node.assignee_type,
            approver_count=len(approvers),
            approver_ids=[a["id"] for a in approvers],
        )
        if not approvers:
            raise ValueError(f"节点 {node.node_name} 未解析到审批人")

        # 计算超时时间
        timeout_at = None
        if node.timeout_hours:
            timeout_at = datetime.utcnow() + timedelta(hours=node.timeout_hours)

        candidate_ids = [a["id"] for a in approvers]

        for approver in approvers:
            task = ApprovalTask(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                store_id=store_id,
                instance_id=instance.id,
                node_key=node.node_key,
                node_name=node.node_name,
                task_type="approval",
                status="pending",
                assignee_id=approver["id"],
                assignee_name=approver.get("name", ""),
                candidate_user_ids=candidate_ids,
                assignee_snapshot={
                    "id": approver["id"],
                    "name": approver.get("name", ""),
                    "resolved_by": node.assignee_type,
                    "config": node.assignee_config,
                },
                timeout_at=timeout_at,
            )
            self.db.add(task)

        # 通知所有审批人
        for approver in approvers:
            await self._notify_approver(approver["id"], instance, node.node_name)

        await self.db.flush()

    async def _find_pending_task(
        self, instance_id: str, node_key: str, assignee_id: str
    ) -> Optional[ApprovalTask]:
        """查找待处理任务"""
        stmt = select(ApprovalTask).where(
            and_(
                ApprovalTask.instance_id == instance_id,
                ApprovalTask.node_key == node_key,
                ApprovalTask.assignee_id == assignee_id,
                ApprovalTask.status == "pending",
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _cancel_pending_tasks(self, instance_id: str, node_key: Optional[str] = None):
        """取消待处理任务"""
        conditions = [
            ApprovalTask.instance_id == instance_id,
            ApprovalTask.status == "pending",
        ]
        if node_key:
            conditions.append(ApprovalTask.node_key == node_key)

        stmt = select(ApprovalTask).where(and_(*conditions))
        result = await self.db.execute(stmt)
        for task in result.scalars().all():
            task.status = "cancelled"
            task.completed_at = datetime.utcnow()

    async def _try_auto_approve(
        self,
        node: ApprovalFlowNode,
        instance: ApprovalInstance,
        form_data: Dict[str, Any],
    ) -> bool:
        """
        检查并执行自动审批。

        自动审批规则存储在 node.assignee_config.auto_approve_rules 中：
        {
            "auto_approve_rules": [
                {
                    "conditions": [
                        {"field": "quantity", "operator": "lte", "value": "5"}
                    ],
                    "comment": "加号数量 <= 5，自动通过"
                }
            ]
        }

        Returns:
            True if auto-approved, False otherwise
        """
        if not node.assignee_config:
            return False

        rules = node.assignee_config.get("auto_approve_rules")
        if not rules:
            return False

        for rule in rules:
            conditions = rule.get("conditions", [])
            if not conditions:
                continue

            # 检查所有条件是否满足（AND 关系）
            all_match = True
            for cond in conditions:
                field_name = cond.get("field")
                operator = cond.get("operator")
                value = cond.get("value")

                if not field_name or not operator:
                    continue

                field_value = form_data.get(field_name)
                if field_value is None:
                    all_match = False
                    break

                op_func = self.condition_evaluator.OPERATORS.get(operator)
                if not op_func:
                    all_match = False
                    break

                try:
                    # 解析条件值
                    cond_value = value
                    if isinstance(cond_value, str):
                        import json
                        try:
                            cond_value = json.loads(cond_value)
                        except (json.JSONDecodeError, TypeError):
                            pass

                    if not op_func(field_value, cond_value):
                        all_match = False
                        break
                except (ValueError, TypeError):
                    all_match = False
                    break

            if all_match:
                # 命中自动审批规则
                comment = rule.get("comment", "命中自动审批规则")

                logger.info(
                    "auto_approve_triggered",
                    instance_id=instance.id,
                    node_key=node.node_key,
                    rule_comment=comment,
                )

                # 标记所有 pending 任务为完成（actor_type=system）
                stmt = select(ApprovalTask).where(
                    and_(
                        ApprovalTask.instance_id == instance.id,
                        ApprovalTask.node_key == node.node_key,
                        ApprovalTask.status == "pending",
                    )
                )
                result = await self.db.execute(stmt)
                for task in result.scalars().all():
                    task.status = "completed"
                    task.completed_at = datetime.utcnow()
                    task.completed_by = "system"

                # 创建审批记录
                record = ApprovalRecord(
                    id=str(uuid.uuid4()),
                    instance_id=instance.id,
                    node_key=node.node_key,
                    node_name=node.node_name,
                    approver_id="system",
                    approver_name="系统自动审批",
                    action="approve",
                    comment=comment,
                )
                self.db.add(record)

                # 推进到下一个节点
                await self._cancel_pending_tasks(instance.id, node.node_key)
                await self._advance(instance, node)
                await self.db.flush()

                return True

        return False

    # ============================================================
    # 内部方法 - 节点推进
    # ============================================================

    async def _advance(self, instance: ApprovalInstance, current_node: ApprovalFlowNode):
        """推进到下一个节点"""
        logger.info(
            "node_leave",
            instance_id=instance.id,
            node_key=current_node.node_key,
            node_name=current_node.node_name,
        )

        nodes = await self._load_nodes(instance.flow_def_id)
        form_data = instance.form_data or {}

        next_node = await self._find_next_node(current_node, nodes, form_data)

        while next_node and next_node.node_type == "condition":
            next_node = await self._find_next_node(next_node, nodes, form_data)

        if not next_node or next_node.node_type == "end":
            await self._complete_as_approved(instance)

        elif next_node.node_type == "cc":
            # 抄送节点: 通知抄送人，继续推进
            await self._handle_cc_node(next_node, instance)
            # 继续推进
            next_next = await self._find_next_node(next_node, nodes, form_data)
            while next_next and next_next.node_type == "condition":
                next_next = await self._find_next_node(next_next, nodes, form_data)
            if next_next:
                if next_next.node_type == "end":
                    await self._complete_as_approved(instance)
                    return
                instance.current_node_key = next_next.node_key
                await self._create_tasks_for_node(
                    next_next, instance, instance.tenant_id, instance.store_id
                )
                # 检查自动审批
                await self._try_auto_approve(next_next, instance, form_data)
            else:
                await self._complete_as_approved(instance)

        else:
            # 推进到下一个审批节点
            logger.info(
                "node_enter",
                instance_id=instance.id,
                node_key=next_node.node_key,
                node_name=next_node.node_name,
                node_type=next_node.node_type,
            )
            instance.current_node_key = next_node.node_key
            await self._create_tasks_for_node(
                next_node, instance, instance.tenant_id, instance.store_id
            )
            # 检查自动审批
            await self._try_auto_approve(next_node, instance, form_data)

    async def _complete_as_approved(self, instance: ApprovalInstance):
        """标记流程通过并执行业务回调。"""
        instance.status = "approved"
        instance.approved_at = datetime.utcnow()
        instance.completed_reason = "normal"
        instance.current_node_key = None

        logger.info(
            "callback_started",
            instance_id=instance.id,
            business_type=instance.business_type,
            callback="on_approved",
        )
        try:
            await callback_registry.execute(
                instance.business_type, "on_approved", instance, self.db
            )
        except Exception as e:
            logger.error(
                "callback_failed",
                instance_id=instance.id,
                business_type=instance.business_type,
                callback="on_approved",
                error=str(e),
            )
            raise
        await self._notify_applicant(instance, "approved")
        logger.info("approval_completed", instance_id=instance.id)

    async def _find_next_node(
        self,
        current_node: ApprovalFlowNode,
        nodes: List[ApprovalFlowNode],
        form_data: Dict[str, Any],
    ) -> Optional[ApprovalFlowNode]:
        """找到下一个节点"""
        # 如果当前节点有条件规则，先求值
        if current_node.conditions:
            target_key = self.condition_evaluator.evaluate_conditions(
                current_node.conditions, form_data
            )
            if target_key:
                target = next((n for n in nodes if n.node_key == target_key), None)
                if target:
                    logger.info(
                        "condition_matched",
                        node_key=current_node.node_key,
                        target_node_key=target_key,
                        field_names=[c.field_name for c in current_node.conditions],
                    )
                    return target

        # 默认: 按 sort_order 找下一个节点
        sorted_nodes = sorted(nodes, key=lambda n: n.sort_order)
        current_idx = next(
            (i for i, n in enumerate(sorted_nodes) if n.id == current_node.id), -1
        )
        if current_idx >= 0 and current_idx + 1 < len(sorted_nodes):
            return sorted_nodes[current_idx + 1]

        return None

    async def _check_approval_complete(
        self,
        node: ApprovalFlowNode,
        instance_id: str,
        node_key: str,
    ) -> bool:
        """检查当前节点是否审批完成（基于 ApprovalTask）"""
        mode = node.approval_mode or "or"

        # 查询已完成的任务数
        completed_stmt = select(func.count(ApprovalTask.id)).where(
            and_(
                ApprovalTask.instance_id == instance_id,
                ApprovalTask.node_key == node_key,
                ApprovalTask.status == "completed",
                ApprovalTask.task_type == "approval",
            )
        )
        completed_count = (await self.db.execute(completed_stmt)).scalar() or 0

        if mode == "or":
            # 或签: 一人通过即完成
            return completed_count > 0

        elif mode == "and":
            # 会签: 所有人都通过
            total_stmt = select(func.count(ApprovalTask.id)).where(
                and_(
                    ApprovalTask.instance_id == instance_id,
                    ApprovalTask.node_key == node_key,
                    ApprovalTask.task_type == "approval",
                )
            )
            total_count = (await self.db.execute(total_stmt)).scalar() or 0
            return completed_count >= total_count

        elif mode == "sequential":
            # 依次审批: 当前人通过即推进
            return completed_count > 0

        return False

    async def _handle_cc_node(self, node: ApprovalFlowNode, instance: ApprovalInstance):
        """处理抄送节点"""
        approvers = await self.assignee_resolver.resolve(node, instance)
        for approver in approvers:
            await self._notify_cc(approver["id"], instance, node.node_name)

    async def _validate_approver(
        self,
        instance: ApprovalInstance,
        node: ApprovalFlowNode,
        approver_id: str,
    ):
        """校验审批人是否有待处理任务"""
        task = await self._find_pending_task(instance.id, node.node_key, approver_id)
        if task:
            return

        # 检查是否被转交（通过 ApprovalRecord 中的 delegate 记录）
        stmt = select(ApprovalRecord).where(
            and_(
                ApprovalRecord.instance_id == instance.id,
                ApprovalRecord.node_key == node.node_key,
                ApprovalRecord.action == "delegate",
                ApprovalRecord.delegate_to == approver_id,
            )
        )
        result = await self.db.execute(stmt)
        if not result.scalars().first():
            raise ValueError("当前用户不是该节点的审批人")

    def _validate_instance_pending(self, instance: ApprovalInstance):
        """校验实例状态"""
        if instance.status != "pending":
            raise ValueError(f"当前状态 {instance.status} 不允许审批")

    # ============================================================
    # 内部方法 - 数据库查询
    # ============================================================

    async def _get_instance(self, instance_id: str) -> ApprovalInstance:
        """获取审批实例"""
        stmt = select(ApprovalInstance).where(ApprovalInstance.id == instance_id)
        result = await self.db.execute(stmt)
        instance = result.scalar_one_or_none()
        if not instance:
            raise ValueError(f"审批实例不存在: {instance_id}")
        return instance

    async def _get_current_node(self, instance: ApprovalInstance) -> Optional[ApprovalFlowNode]:
        """获取当前节点"""
        if not instance.current_node_key:
            return None
        stmt = select(ApprovalFlowNode).where(
            and_(
                ApprovalFlowNode.flow_def_id == instance.flow_def_id,
                ApprovalFlowNode.node_key == instance.current_node_key,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_flow_def(self, flow_def_id: str) -> Optional[ApprovalFlowDefinition]:
        """获取流程定义"""
        stmt = select(ApprovalFlowDefinition).where(ApprovalFlowDefinition.id == flow_def_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_active_flow_def(
        self, business_type: str, tenant_id: Optional[str]
    ) -> Optional[ApprovalFlowDefinition]:
        """获取激活的流程定义"""
        stmt = select(ApprovalFlowDefinition).where(
            and_(
                ApprovalFlowDefinition.business_type == business_type,
                ApprovalFlowDefinition.status == "active",
            )
        )
        if tenant_id:
            stmt = stmt.where(ApprovalFlowDefinition.tenant_id == tenant_id)
        stmt = stmt.order_by(ApprovalFlowDefinition.version.desc())
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def _load_nodes(self, flow_def_id: str) -> List[ApprovalFlowNode]:
        """加载流程所有节点"""
        stmt = (
            select(ApprovalFlowNode)
            .where(ApprovalFlowNode.flow_def_id == flow_def_id)
            .order_by(ApprovalFlowNode.sort_order)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ============================================================
    # 内部方法 - 通知（Celery 异步）
    # ============================================================

    async def _notify_approver(self, approver_id: str, instance: ApprovalInstance, node_name: str):
        """通知审批人有待办（通过 Celery 异步）"""
        try:
            from app.tasks.approval_task import send_approval_notification
            send_approval_notification.delay(
                user_id=approver_id,
                message_type="approval_pending",
                data={
                    "instance_id": instance.id,
                    "title": instance.title,
                    "node_name": node_name,
                    "applicant_name": instance.applicant_name or "",
                    "business_type": instance.business_type,
                },
            )
        except Exception as e:
            logger.warning("notification_failed", error=str(e), user_id=approver_id)

    async def _notify_applicant(self, instance: ApprovalInstance, status: str):
        """通知申请人审批结果（通过 Celery 异步）"""
        try:
            from app.tasks.approval_task import send_approval_notification
            send_approval_notification.delay(
                user_id=instance.applicant_id,
                message_type=f"approval_{status}",
                data={
                    "instance_id": instance.id,
                    "title": instance.title,
                    "status": status,
                    "business_type": instance.business_type,
                },
            )
        except Exception as e:
            logger.warning("notification_failed", error=str(e), user_id=instance.applicant_id)

    async def _notify_cc(self, user_id: str, instance: ApprovalInstance, node_name: str):
        """通知抄送人（通过 Celery 异步）"""
        try:
            from app.tasks.approval_task import send_approval_notification
            send_approval_notification.delay(
                user_id=user_id,
                message_type="approval_pending",
                data={
                    "instance_id": instance.id,
                    "title": instance.title,
                    "node_name": node_name,
                    "is_cc": True,
                },
            )
        except Exception as e:
            logger.warning("cc_notification_failed", error=str(e), user_id=user_id)
