"""审批流定义服务"""
import logging
import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant_context import get_current_tenant_id
from app.models.approval_flow import (
    ApprovalFlowCondition,
    ApprovalFlowDefinition,
    ApprovalFlowNode,
)
from app.modules.approval_flows.schemas import (
    FlowDefinitionCreate,
    FlowDefinitionUpdate,
)
from app.modules.approval_flows.listener_normalizer import normalize_listener_config
from app.utils.audit import set_create_audit, set_update_audit

logger = logging.getLogger(__name__)


def _normalize_listener(listener: dict | None) -> dict:
    """Normalize legacy/front-end listener payloads to the runtime contract."""
    if not isinstance(listener, dict):
        return {}

    normalized = dict(listener)
    action = normalized.get("action") or normalized.get("actionType")
    config = normalized.get("config") or normalized.get("actionConfig") or {}
    # config 字段的 camelCase -> snake_case 归一化委托给共享纯函数，
    # 仅对 dict 类型生效（与原实现一致）。
    if isinstance(config, dict):
        config = normalize_listener_config(config)

    normalized["action"] = action
    normalized["config"] = config
    return normalized


def _normalize_listeners(listeners: list[dict] | None) -> list[dict] | None:
    if listeners is None:
        return None
    return [_normalize_listener(listener) for listener in listeners if isinstance(listener, dict)]


class FlowDefinitionService:
    """审批流定义 CRUD 服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        page: int = 1,
        page_size: int = 20,
        business_type: str | None = None,
        status: str | None = None,
        *,
        name: str | None = None,
    ) -> tuple[list[ApprovalFlowDefinition], int]:
        """获取流程定义列表"""
        stmt = select(ApprovalFlowDefinition)
        count_stmt = select(func.count(ApprovalFlowDefinition.id))

        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(ApprovalFlowDefinition.tenant_id == tenant_id)
            count_stmt = count_stmt.where(ApprovalFlowDefinition.tenant_id == tenant_id)

        if business_type:
            stmt = stmt.where(ApprovalFlowDefinition.business_type == business_type)
            count_stmt = count_stmt.where(ApprovalFlowDefinition.business_type == business_type)

        if status:
            stmt = stmt.where(ApprovalFlowDefinition.status == status)
            count_stmt = count_stmt.where(ApprovalFlowDefinition.status == status)

        if name:
            stmt = stmt.where(ApprovalFlowDefinition.name.ilike(f"%{name}%"))
            count_stmt = count_stmt.where(ApprovalFlowDefinition.name.ilike(f"%{name}%"))

        stmt = stmt.order_by(ApprovalFlowDefinition.updated_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        count_result = await self.db.execute(count_stmt)

        return list(result.scalars().all()), count_result.scalar() or 0

    async def get_by_id(self, flow_def_id: str) -> ApprovalFlowDefinition | None:
        """获取流程定义详情（含节点和条件）"""
        stmt = select(ApprovalFlowDefinition).where(ApprovalFlowDefinition.id == flow_def_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_business_type(self, business_type: str) -> ApprovalFlowDefinition | None:
        """按业务类型获取激活的流程定义"""
        tenant_id = get_current_tenant_id()
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

    async def get_by_name(self, name: str, business_type: str = "custom") -> ApprovalFlowDefinition | None:
        """按名称查找最新版本的流程定义"""
        tenant_id = get_current_tenant_id()
        stmt = select(ApprovalFlowDefinition).where(
            ApprovalFlowDefinition.name == name,
            ApprovalFlowDefinition.business_type == business_type,
        )
        if tenant_id:
            stmt = stmt.where(ApprovalFlowDefinition.tenant_id == tenant_id)
        stmt = stmt.order_by(ApprovalFlowDefinition.version.desc())
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def update_from_import(self, flow_def: ApprovalFlowDefinition, data: FlowDefinitionCreate, user_id: str) -> ApprovalFlowDefinition:
        """从导入数据更新已有流程定义（替换节点和条件）"""
        from app.models.approval_flow import ApprovalFlowCondition, ApprovalFlowNode

        # 删除旧节点（级联删除条件）
        for node in flow_def.nodes:
            await self.db.delete(node)
        await self.db.flush()

        # 更新基本信息
        flow_def.description = data.description
        flow_def.form_schema = data.form_schema
        flow_def.callback_config = data.callback_config
        flow_def.global_listeners = _normalize_listeners(data.global_listeners)
        flow_def.edges = data.edges
        set_update_audit(flow_def, user_id)

        # 创建新节点
        for node_data in data.nodes:
            node = ApprovalFlowNode(
                id=str(uuid.uuid4()),
                flow_def_id=flow_def.id,
                node_key=node_data.node_key,
                node_name=node_data.node_name,
                node_type=node_data.node_type,
                approval_mode=node_data.approval_mode,
                assignee_type=node_data.assignee_type,
                assignee_config=node_data.assignee_config,
                timeout_hours=node_data.timeout_hours,
                timeout_action=node_data.timeout_action,
                sort_order=node_data.sort_order,
                position_x=node_data.position_x,
                position_y=node_data.position_y,
                listeners=_normalize_listeners(node_data.listeners),
            )
            self.db.add(node)
            await self.db.flush()

            for cond_data in node_data.conditions:
                condition = ApprovalFlowCondition(
                    id=str(uuid.uuid4()),
                    node_id=node.id,
                    flow_def_id=flow_def.id,
                    target_node_key=cond_data.target_node_key,
                    field_name=cond_data.field_name,
                    operator=cond_data.operator,
                    value=cond_data.value,
                    priority=cond_data.priority,
                    group_id=cond_data.group_id,
                )
                self.db.add(condition)

        await self.db.flush()
        return flow_def

    async def create(self, data: FlowDefinitionCreate, user_id: str) -> ApprovalFlowDefinition:
        """创建流程定义"""
        tenant_id = get_current_tenant_id()

        # 计算版本号
        version = await self._next_version(data.business_type, tenant_id)

        flow_def = ApprovalFlowDefinition(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name=data.name,
            business_type=data.business_type,
            description=data.description,
            version=version,
            status="draft",
            form_schema=data.form_schema,
            callback_config=data.callback_config,
            store_id=data.store_id,
            global_listeners=_normalize_listeners(data.global_listeners),
        )
        flow_def.edges = data.edges
        set_create_audit(flow_def, user_id)
        self.db.add(flow_def)
        await self.db.flush()

        # 创建节点
        for node_data in data.nodes:
            node = ApprovalFlowNode(
                id=str(uuid.uuid4()),
                flow_def_id=flow_def.id,
                node_key=node_data.node_key,
                node_name=node_data.node_name,
                node_type=node_data.node_type,
                approval_mode=node_data.approval_mode,
                assignee_type=node_data.assignee_type,
                assignee_config=node_data.assignee_config,
                timeout_hours=node_data.timeout_hours,
                timeout_action=node_data.timeout_action,
                sort_order=node_data.sort_order,
                position_x=node_data.position_x,
                position_y=node_data.position_y,
                listeners=_normalize_listeners(node_data.listeners),
            )
            self.db.add(node)
            await self.db.flush()

            # 创建条件规则
            for cond_data in node_data.conditions:
                condition = ApprovalFlowCondition(
                    id=str(uuid.uuid4()),
                    node_id=node.id,
                    flow_def_id=flow_def.id,
                    target_node_key=cond_data.target_node_key,
                    field_name=cond_data.field_name,
                    operator=cond_data.operator,
                    value=cond_data.value,
                    priority=cond_data.priority,
                    group_id=cond_data.group_id,
                )
                self.db.add(condition)

        await self.db.flush()
        return flow_def

    async def update(self, flow_def_id: str, data: FlowDefinitionUpdate, user_id: str) -> ApprovalFlowDefinition | None:
        """更新流程定义"""
        flow_def = await self.get_by_id(flow_def_id)
        if not flow_def:
            return None

        if flow_def.status == "active":
            raise ValueError("激活状态的流程不能编辑，请先归档")

        if data.name is not None:
            flow_def.name = data.name
        if data.description is not None:
            flow_def.description = data.description
        if data.form_schema is not None:
            flow_def.form_schema = data.form_schema
        if data.callback_config is not None:
            flow_def.callback_config = data.callback_config
        if data.global_listeners is not None:
            flow_def.global_listeners = _normalize_listeners(data.global_listeners)

        # 更新节点（先删除旧的，再创建新的）
        if data.nodes is not None:
            # 删除旧节点（级联删除条件）
            for node in flow_def.nodes:
                await self.db.delete(node)
            await self.db.flush()

            # 创建新节点
            for node_data in data.nodes:
                node = ApprovalFlowNode(
                    id=str(uuid.uuid4()),
                    flow_def_id=flow_def.id,
                    node_key=node_data.node_key,
                    node_name=node_data.node_name,
                    node_type=node_data.node_type,
                    approval_mode=node_data.approval_mode,
                    assignee_type=node_data.assignee_type,
                    assignee_config=node_data.assignee_config,
                    timeout_hours=node_data.timeout_hours,
                    timeout_action=node_data.timeout_action,
                    sort_order=node_data.sort_order,
                    position_x=node_data.position_x,
                    position_y=node_data.position_y,
                    listeners=_normalize_listeners(node_data.listeners),
                )
                self.db.add(node)
                await self.db.flush()

                for cond_data in node_data.conditions:
                    condition = ApprovalFlowCondition(
                        id=str(uuid.uuid4()),
                        node_id=node.id,
                        flow_def_id=flow_def.id,
                        target_node_key=cond_data.target_node_key,
                        field_name=cond_data.field_name,
                        operator=cond_data.operator,
                        value=cond_data.value,
                        priority=cond_data.priority,
                        group_id=cond_data.group_id,
                    )
                    self.db.add(condition)

        if data.edges is not None:
            flow_def.edges = data.edges

        set_update_audit(flow_def, user_id)
        flow_def.version += 1
        await self.db.flush()
        return flow_def

    async def activate(self, flow_def_id: str, user_id: str) -> ApprovalFlowDefinition | None:
        """激活流程"""
        flow_def = await self.get_by_id(flow_def_id)
        if not flow_def:
            return None

        validation = await self.validate(flow_def_id)
        if not validation["valid"]:
            raise ValueError("流程校验失败: " + "；".join(validation["errors"]))

        # 归档同业务类型的其他激活流程
        tenant_id = get_current_tenant_id()
        stmt = select(ApprovalFlowDefinition).where(
            and_(
                ApprovalFlowDefinition.business_type == flow_def.business_type,
                ApprovalFlowDefinition.status == "active",
                ApprovalFlowDefinition.id != flow_def_id,
            )
        )
        if tenant_id:
            stmt = stmt.where(ApprovalFlowDefinition.tenant_id == tenant_id)

        result = await self.db.execute(stmt)
        for old_def in result.scalars().all():
            old_def.status = "archived"
            set_update_audit(old_def, user_id)

        flow_def.status = "active"
        flow_def.version = (flow_def.version or 0) + 1

        # 生成流程快照（节点+条件的完整 JSON）
        snapshot = {
            "nodes": [
                {
                    "node_key": n.node_key,
                    "node_name": n.node_name,
                    "node_type": n.node_type,
                    "approval_mode": n.approval_mode,
                    "assignee_type": n.assignee_type,
                    "assignee_config": n.assignee_config,
                    "timeout_hours": n.timeout_hours,
                    "timeout_action": n.timeout_action,
                    "sort_order": n.sort_order,
                    "conditions": [
                        {
                            "target_node_key": c.target_node_key,
                            "field_name": c.field_name,
                            "operator": c.operator,
                            "value": c.value,
                            "priority": c.priority,
                            "group_id": c.group_id,
                        }
                        for c in n.conditions
                    ],
                    "listeners": n.listeners,
                }
                for n in flow_def.nodes
            ]
        }
        snapshot["edges"] = flow_def.edges or []
        snapshot["global_listeners"] = flow_def.global_listeners
        flow_def.snapshot_json = snapshot

        set_update_audit(flow_def, user_id)
        await self.db.flush()
        return flow_def

    async def archive(self, flow_def_id: str, user_id: str) -> ApprovalFlowDefinition | None:
        """归档流程"""
        flow_def = await self.get_by_id(flow_def_id)
        if not flow_def:
            return None

        flow_def.status = "archived"
        set_update_audit(flow_def, user_id)
        await self.db.flush()
        return flow_def

    async def delete(self, flow_def_id: str, user_id: str) -> bool:
        """删除流程（仅草稿状态可删除）"""
        flow_def = await self.get_by_id(flow_def_id)
        if not flow_def:
            return False

        if flow_def.status != "draft":
            raise ValueError("仅草稿状态的流程可以删除")

        await self.db.delete(flow_def)
        await self.db.flush()
        return True

    async def batch_delete(self, flow_def_ids: list[str], user_id: str) -> dict:
        """批量删除流程定义（仅草稿状态可删除）

        逐条处理：未找到 / 非草稿状态的条目会被收集到 failed 中，
        不影响其他可删除条目。返回 {"deleted": [...], "failed": [...]}。
        """
        deleted: list[dict] = []
        failed: list[dict] = []

        for flow_def_id in flow_def_ids:
            flow_def = await self.get_by_id(flow_def_id)
            if not flow_def:
                failed.append({"id": flow_def_id, "error": "流程定义不存在"})
                continue

            if flow_def.status != "draft":
                failed.append({
                    "id": flow_def_id,
                    "name": flow_def.name,
                    "status": flow_def.status,
                    "error": "仅草稿状态的流程可以删除",
                })
                continue

            try:
                await self.db.delete(flow_def)
                await self.db.flush()
                deleted.append({"id": flow_def_id, "name": flow_def.name})
            except Exception as e:  # noqa: BLE001
                logger.exception("批量删除流程失败 id=%s", flow_def_id)
                failed.append({"id": flow_def_id, "name": flow_def.name, "error": str(e)})

        return {"deleted": deleted, "failed": failed}

    async def copy(self, flow_def_id: str, user_id: str) -> ApprovalFlowDefinition | None:
        """复制流程定义"""
        source = await self.get_by_id(flow_def_id)
        if not source:
            return None

        # 构建创建数据
        nodes_data = []
        for node in source.nodes:
            conditions = [
                {
                    "target_node_key": c.target_node_key,
                    "field_name": c.field_name,
                    "operator": c.operator,
                    "value": c.value,
                    "priority": c.priority,
                    "group_id": c.group_id,
                }
                for c in node.conditions
            ]
            nodes_data.append({
                "node_key": node.node_key,
                "node_name": node.node_name,
                "node_type": node.node_type,
                "approval_mode": node.approval_mode,
                "assignee_type": node.assignee_type,
                "assignee_config": node.assignee_config,
                "timeout_hours": node.timeout_hours,
                "timeout_action": node.timeout_action,
                "sort_order": node.sort_order,
                "position_x": node.position_x,
                "position_y": node.position_y,
                "listeners": node.listeners,
                "conditions": conditions,
            })

        create_data = FlowDefinitionCreate(
            name=f"{source.name} (副本)",
            business_type=source.business_type,
            description=source.description,
            form_schema=source.form_schema,
            callback_config=source.callback_config,
            store_id=source.store_id,
            global_listeners=source.global_listeners,
            nodes=nodes_data,
            edges=source.edges or [],
        )

        return await self.create(create_data, user_id)

    async def validate(self, flow_def_id: str) -> dict:
        """校验流程定义完整性"""
        flow_def = await self.get_by_id(flow_def_id)
        if not flow_def:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="流程定义不存在")

        errors: list[str] = []
        nodes = flow_def.nodes
        edges = flow_def.edges or []

        # 1. 检查开始节点数量
        start_nodes = [n for n in nodes if n.node_type == "start"]
        if len(start_nodes) == 0:
            errors.append("缺少开始节点")
        elif len(start_nodes) > 1:
            errors.append("只能有一个开始节点")

        # 2. 检查结束节点
        end_nodes = [n for n in nodes if n.node_type == "end"]
        if len(end_nodes) == 0:
            errors.append("缺少结束节点")

        # 3. 检查审批节点配置
        for node in nodes:
            if node.node_type == "approval":
                if not node.assignee_type:
                    errors.append(f"审批节点 [{node.node_name}] 未配置审批人类型")
                if not node.assignee_config:
                    errors.append(f"审批节点 [{node.node_name}] 未配置审批人")

        # 4. 检查条件节点
        for node in nodes:
            if node.node_type == "condition":
                if not node.conditions:
                    errors.append(f"条件节点 [{node.node_name}] 没有条件规则")

        # 5. 连通性检查 (BFS)
        node_keys = {n.node_key for n in nodes}
        outgoing: dict[str, list[dict]] = {n.node_key: [] for n in nodes}
        incoming: dict[str, list[dict]] = {n.node_key: [] for n in nodes}

        if nodes:
            edge_pairs: set[tuple[str, str, str | None]] = set()
            for e in edges:
                src = e.get("source", "")
                tgt = e.get("target", "")
                source_handle = e.get("sourceHandle") or e.get("source_handle")

                if not src:
                    errors.append("存在缺少源节点的连线")
                if not tgt:
                    errors.append("存在缺少目标节点的连线")
                node_keys = {n.node_key for n in nodes}
                if src not in node_keys:
                    errors.append(f"连线的源节点 [{src}] 不存在")
                if tgt not in node_keys:
                    errors.append(f"连线的目标节点 [{tgt}] 不存在")
                if src in outgoing:
                    outgoing[src].append(e)
                if tgt in incoming:
                    incoming[tgt].append(e)

                pair = (src, tgt, source_handle)
                if src and tgt and pair in edge_pairs:
                    errors.append(f"存在重复连线: {src} -> {tgt}")
                edge_pairs.add(pair)

            if not edges:
                errors.append("流程定义缺少连线")

            start_key = start_nodes[0].node_key if start_nodes else None
            if start_key:
                visited: set[str] = set()
                queue = [start_key]
                while queue:
                    curr = queue.pop(0)
                    if curr in visited:
                        continue
                    visited.add(curr)
                    for edge in outgoing.get(curr, []):
                        neighbor = edge.get("target", "")
                        if neighbor not in visited:
                            queue.append(neighbor)

                unreachable = node_keys - visited
                if unreachable:
                    errors.append(f"存在不可达节点: {', '.join(unreachable)}")

        # 6. 图结构约束
        for node in nodes:
            node_outgoing = outgoing.get(node.node_key, [])
            node_incoming = incoming.get(node.node_key, [])

            if node.node_type != "start" and not node_incoming:
                errors.append(f"节点 [{node.node_name}] 没有入边")

            if node.node_type == "end":
                if node_outgoing:
                    errors.append(f"结束节点 [{node.node_name}] 不允许有出边")
                continue

            if not node_outgoing:
                errors.append(f"节点 [{node.node_name}] 没有出边")

            if node.node_type == "condition":
                default_edges = [
                    e for e in node_outgoing
                    if (e.get("sourceHandle") or e.get("source_handle")) == "default"
                ]
                if len(default_edges) > 1:
                    errors.append(f"条件节点 [{node.node_name}] 默认分支只能有一条")

                condition_targets = {
                    condition.target_node_key
                    for condition in (node.conditions or [])
                    if condition.target_node_key
                }
                edge_targets = {e.get("target") for e in node_outgoing}
                missing_targets = condition_targets - edge_targets
                if missing_targets:
                    errors.append(
                        f"条件节点 [{node.node_name}] 的条件目标缺少连线: {', '.join(sorted(missing_targets))}"
                    )
            else:
                if len(node_outgoing) > 1:
                    errors.append(f"节点 [{node.node_name}] 存在多条出边，无法确定下一节点")

        return {"valid": len(errors) == 0, "errors": errors}

    async def _next_version(self, business_type: str, tenant_id: str | None) -> int:
        """获取下一个版本号"""
        stmt = select(func.max(ApprovalFlowDefinition.version)).where(
            ApprovalFlowDefinition.business_type == business_type
        )
        if tenant_id:
            stmt = stmt.where(ApprovalFlowDefinition.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        max_version = result.scalar() or 0
        return max_version + 1
