"""审批流引擎核心路径单元测试

覆盖:
- start_instance: 创建实例和任务 / 无流程定义抛异常
- _do_approve: 或签推进 / 会签等待
- _do_reject: 拒绝状态变更
- _do_delegate: 转交创建新任务
- _do_withdraw: 申请人撤回 / 非申请人撤回异常
- _advance: 推进到结束节点完成 / 跳过条件节点
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.modules.approval_flows.engine import ApprovalEngine, FlowNotFoundError


# ============================================================
# Helpers
# ============================================================

def _make_snapshot_node(
    node_key: str,
    node_name: str = "审批节点",
    node_type: str = "approval",
    approval_mode: str = "or",
    assignee_type: str = "user",
    assignee_config: dict | None = None,
    sort_order: int = 0,
    conditions: list | None = None,
):
    """构造快照节点 JSON dict（与 _build_nodes_from_snapshot 兼容）"""
    return {
        "node_key": node_key,
        "node_name": node_name,
        "node_type": node_type,
        "approval_mode": approval_mode,
        "assignee_type": assignee_type,
        "assignee_config": assignee_config or {},
        "sort_order": sort_order,
        "conditions": conditions or [],
    }


def _make_flow_def(flow_def_id: str = "fd-1", snapshot: dict | None = None):
    """构造流程定义 mock"""
    fd = MagicMock()
    fd.id = flow_def_id
    fd.snapshot_json = snapshot
    return fd


def _make_instance(
    instance_id: str = "inst-1",
    flow_def_id: str = "fd-1",
    applicant_id: str = "user-1",
    status: str = "pending",
    current_node_key: str = "approval_1",
    business_type: str = "leave_request",
    business_id: str = "biz-1",
    store_id: str = "store-1",
):
    """构造审批实例 mock"""
    inst = MagicMock()
    inst.id = instance_id
    inst.flow_def_id = flow_def_id
    inst.applicant_id = applicant_id
    inst.applicant_name = "测试用户"
    inst.status = status
    inst.current_node_key = current_node_key
    inst.business_type = business_type
    inst.business_id = business_id
    inst.title = "测试审批"
    inst.form_data = {}
    inst.store_id = store_id
    inst.tenant_id = "tenant-1"
    inst.completed_reason = None
    inst.approved_at = None
    inst.rejected_at = None
    inst.cancelled_at = None
    inst.updated_by = None
    inst.current_node_key = current_node_key
    return inst


def _make_task(
    task_id: str = "task-1",
    instance_id: str = "inst-1",
    node_key: str = "approval_1",
    assignee_id: str = "user-1",
    status: str = "pending",
):
    """构造审批任务 mock"""
    task = MagicMock()
    task.id = task_id
    task.instance_id = instance_id
    task.node_key = node_key
    task.node_name = "审批节点"
    task.assignee_id = assignee_id
    task.assignee_name = "审批人"
    task.status = status
    task.completed_at = None
    task.completed_by = None
    task.task_type = "approval"
    return task


def _make_db_session():
    """构造异步数据库 session mock，支持链式调用"""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


def _build_snapshot_with_nodes(nodes: list[dict]) -> dict:
    """构建包含节点列表的快照"""
    return {"nodes": nodes}


# ============================================================
# start_instance
# ============================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestStartInstance:
    """测试发起审批"""

    @patch("app.modules.approval_flows.engine.get_current_tenant_id", return_value="tenant-1")
    async def test_start_instance_creates_instance_and_tasks(self, mock_tenant):
        """发起审批，验证创建了 instance 和 tasks"""
        db = _make_db_session()

        # 快照: start -> approval_1
        snapshot = _build_snapshot_with_nodes([
            _make_snapshot_node("start", "开始", "start", sort_order=0),
            _make_snapshot_node("approval_1", "部门审批", "approval", "or", sort_order=1),
        ])
        flow_def = _make_flow_def(snapshot=snapshot)

        # _get_active_flow_def: scalars().first()
        list_result = MagicMock()
        list_result.scalars.return_value.first.return_value = flow_def

        # _load_nodes: scalar_one_or_none() 返回带 snapshot 的 flow_def
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none.return_value = flow_def

        db.execute.side_effect = [
            list_result,      # _get_active_flow_def
            scalar_result,    # _load_nodes
        ]

        engine = ApprovalEngine(db)

        # mock assignee_resolver.resolve
        engine.assignee_resolver = MagicMock()
        engine.assignee_resolver.resolve = AsyncMock(
            return_value=[{"id": "approver-1", "name": "审批人A"}]
        )

        instance = await engine.start_instance(
            business_type="leave_request",
            business_id="biz-1",
            form_data={"days": 3},
            applicant_id="user-1",
            title="请假申请",
            applicant_name="测试用户",
        )

        # 验证 db.add 被调用（创建 instance + tasks）
        assert db.add.called
        # 验证 flush 被调用
        assert db.flush.called

    @patch("app.modules.approval_flows.engine.get_current_tenant_id", return_value="tenant-1")
    async def test_start_instance_no_active_flow_raises(self, mock_tenant):
        """无激活流程定义时抛出 FlowNotFoundError"""
        db = _make_db_session()

        # mock 查询返回 None
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        db.execute.return_value = mock_result

        engine = ApprovalEngine(db)

        with pytest.raises(FlowNotFoundError, match="未找到业务类型"):
            await engine.start_instance(
                business_type="unknown_type",
                business_id="biz-1",
                form_data={},
                applicant_id="user-1",
                title="测试",
            )


# ============================================================
# _do_approve
# ============================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestDoApprove:
    """测试审批通过"""

    @patch("app.modules.approval_flows.engine.get_current_tenant_id", return_value="tenant-1")
    async def test_approve_or_mode_advances(self, mock_tenant):
        """或签模式，一人通过即推进"""
        db = _make_db_session()

        snapshot = _build_snapshot_with_nodes([
            _make_snapshot_node("start", "开始", "start", sort_order=0),
            _make_snapshot_node("approval_1", "部门审批", "approval", "or", sort_order=1),
            _make_snapshot_node("approval_2", "总监审批", "approval", "or", sort_order=2),
            _make_snapshot_node("end", "结束", "end", sort_order=3),
        ])

        instance = _make_instance()
        task = _make_task(assignee_id="approver-1")

        flow_def = _make_flow_def(snapshot=snapshot)
        flow_def_result = MagicMock()
        flow_def_result.scalar_one_or_none.return_value = flow_def

        # 依次返回: _get_instance, _get_current_node(fallback flow_def查询), _validate_approver(通过_pending_task找到),
        # _find_pending_task, _check_approval_complete(completed count), _check_approval_complete(total count),
        # _cancel_pending_tasks, _load_nodes(fallback), _advance的_find_next_node
        instance_result = MagicMock()
        instance_result.scalar_one_or_none.return_value = instance

        task_result = MagicMock()
        task_result.scalar_one_or_none.return_value = task

        # _check_approval_complete: or 模式，completed_count > 0 即推进
        completed_count_result = MagicMock()
        completed_count_result.scalar.return_value = 1

        # _cancel_pending_tasks 查询
        cancel_result = MagicMock()
        cancel_result.scalars.return_value.all.return_value = []

        # _load_nodes 查询（fallback 到 DB）
        nodes_result = MagicMock()
        nodes_result.scalars.return_value.all.return_value = [
            MagicMock(id="start", node_key="start", node_name="开始", node_type="start",
                      sort_order=0, conditions=[], approval_mode=None),
            MagicMock(id="approval_1", node_key="approval_1", node_name="部门审批",
                      node_type="approval", sort_order=1, conditions=[], approval_mode="or"),
            MagicMock(id="approval_2", node_key="approval_2", node_name="总监审批",
                      node_type="approval", sort_order=2, conditions=[], approval_mode="or",
                      assignee_type="user", assignee_config={}, timeout_hours=None),
            MagicMock(id="end", node_key="end", node_name="结束", node_type="end", sort_order=3, conditions=[]),
        ]

        db.execute.side_effect = [
            instance_result,          # _get_instance
            flow_def_result,          # _get_current_node (flow_def query)
            task_result,              # _find_pending_task
            task_result,              # _validate_approver -> _find_pending_task (找到任务,不抛异常)
            completed_count_result,   # _check_approval_complete (completed count)
            cancel_result,            # _cancel_pending_tasks
            flow_def_result,          # _advance -> _load_nodes (flow_def)
            nodes_result,             # _advance -> _load_nodes (fallback nodes)
        ]

        engine = ApprovalEngine(db)
        engine.assignee_resolver = MagicMock()
        engine.assignee_resolver.resolve = AsyncMock(
            return_value=[{"id": "approver-2", "name": "总监"}]
        )

        result = await engine._do_approve("inst-1", "approver-1", "审批人A")

        # 验证任务状态变为 completed
        assert task.status == "completed"
        # 验证创建了审批记录
        assert db.add.called
        # 验证实例被更新
        assert result.updated_by == "approver-1"

    @patch("app.modules.approval_flows.engine.get_current_tenant_id", return_value="tenant-1")
    async def test_approve_and_mode_waits_all(self, mock_tenant):
        """会签模式，部分通过不推进"""
        db = _make_db_session()

        instance = _make_instance()
        task = _make_task(assignee_id="approver-1")

        instance_result = MagicMock()
        instance_result.scalar_one_or_none.return_value = instance

        flow_def = MagicMock()
        flow_def.snapshot_json = _build_snapshot_with_nodes([
            _make_snapshot_node("approval_1", "部门审批", "approval", "and", sort_order=1),
        ])
        flow_def_result = MagicMock()
        flow_def_result.scalar_one_or_none.return_value = flow_def

        task_result = MagicMock()
        task_result.scalar_one_or_none.return_value = task

        # _check_approval_complete: and 模式，completed=1, total=2，不推进
        completed_count_result = MagicMock()
        completed_count_result.scalar.return_value = 1
        total_count_result = MagicMock()
        total_count_result.scalar.return_value = 2

        db.execute.side_effect = [
            instance_result,          # _get_instance
            flow_def_result,          # _get_current_node
            task_result,              # _validate_approver -> _find_pending_task
            task_result,              # _find_pending_task
            completed_count_result,   # _check_approval_complete (completed)
            total_count_result,       # _check_approval_complete (total)
        ]

        engine = ApprovalEngine(db)
        result = await engine._do_approve("inst-1", "approver-1", "审批人A")

        # 任务完成但实例不推进（current_node_key 不变）
        assert task.status == "completed"
        assert instance.current_node_key == "approval_1"


# ============================================================
# _do_reject
# ============================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestDoReject:
    """测试审批拒绝"""

    @patch.object(ApprovalEngine, "_fire_global_listeners", new_callable=AsyncMock)
    @patch.object(ApprovalEngine, "_get_flow_def", new_callable=AsyncMock, return_value=None)
    @patch("app.modules.approval_flows.engine.get_current_tenant_id", return_value="tenant-1")
    async def test_reject_sets_status(self, mock_tenant, _mock_flow_def, _mock_listener):
        """拒绝后状态变更为 rejected"""
        db = _make_db_session()

        instance = _make_instance()
        task = _make_task(assignee_id="approver-1")

        instance_result = MagicMock()
        instance_result.scalar_one_or_none.return_value = instance

        flow_def = MagicMock()
        flow_def.snapshot_json = _build_snapshot_with_nodes([
            _make_snapshot_node("approval_1", "部门审批", "approval", "or"),
        ])
        flow_def_result = MagicMock()
        flow_def_result.scalar_one_or_none.return_value = flow_def

        task_result = MagicMock()
        task_result.scalar_one_or_none.return_value = task

        # _cancel_pending_tasks 查询
        cancel_result = MagicMock()
        cancel_result.scalars.return_value.all.return_value = []

        db.execute.side_effect = [
            instance_result,   # _get_instance
            flow_def_result,   # _get_current_node
            task_result,       # _validate_approver -> _find_pending_task
            task_result,       # _find_pending_task
            cancel_result,     # _cancel_pending_tasks
        ]

        engine = ApprovalEngine(db)
        engine._notify_applicant = AsyncMock()

        result = await engine._do_reject("inst-1", "approver-1", "审批人A", "不符合条件")

        assert result.status == "rejected"
        assert result.completed_reason == "normal"
        assert result.rejected_at is not None
        assert task.status == "completed"


# ============================================================
# _do_delegate
# ============================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestDoDelegate:
    """测试转交"""

    @patch("app.modules.approval_flows.engine.get_current_tenant_id", return_value="tenant-1")
    async def test_delegate_creates_new_task(self, mock_tenant):
        """转交后创建新任务，旧任务标记 transferred"""
        db = _make_db_session()

        instance = _make_instance()
        task = _make_task(assignee_id="approver-1")

        instance_result = MagicMock()
        instance_result.scalar_one_or_none.return_value = instance

        flow_def = MagicMock()
        flow_def.snapshot_json = _build_snapshot_with_nodes([
            _make_snapshot_node("approval_1", "部门审批", "approval", "or"),
        ])
        flow_def_result = MagicMock()
        flow_def_result.scalar_one_or_none.return_value = flow_def

        task_result = MagicMock()
        task_result.scalar_one_or_none.return_value = task

        db.execute.side_effect = [
            instance_result,   # _get_instance
            flow_def_result,   # _get_current_node
            task_result,       # _validate_approver -> _find_pending_task
            task_result,       # _find_pending_task
        ]

        engine = ApprovalEngine(db)
        engine._notify_approver = AsyncMock()

        result = await engine._do_delegate(
            "inst-1", "approver-1", "审批人A",
            "approver-2", "审批人B", "转交给B处理"
        )

        # 旧任务标记为 transferred
        assert task.status == "transferred"
        assert task.completed_by == "approver-1"

        # 验证创建了新任务（db.add 被调用，至少包含新任务和记录）
        assert db.add.called
        add_calls = db.add.call_args_list
        # 至少调用 2 次: 新任务 + 转交记录
        assert len(add_calls) >= 2

        # 验证新任务的 assignee_id 是目标人
        new_task_obj = add_calls[0][0][0]
        assert new_task_obj.assignee_id == "approver-2"
        assert new_task_obj.status == "pending"


# ============================================================
# _do_withdraw
# ============================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestDoWithdraw:
    """测试撤回"""

    @patch.object(ApprovalEngine, "_fire_global_listeners", new_callable=AsyncMock)
    @patch.object(ApprovalEngine, "_get_flow_def", new_callable=AsyncMock, return_value=None)
    @patch("app.modules.approval_flows.engine.get_current_tenant_id", return_value="tenant-1")
    async def test_withdraw_by_applicant(self, mock_tenant, _mock_flow_def, _mock_listener):
        """申请人撤回成功"""
        db = _make_db_session()

        instance = _make_instance(applicant_id="user-1", status="pending")

        instance_result = MagicMock()
        instance_result.scalar_one_or_none.return_value = instance

        # _do_withdraw 内部查询是否有审批记录
        record_result = MagicMock()
        record_result.scalars.return_value.first.return_value = None

        # _cancel_pending_tasks 查询
        cancel_result = MagicMock()
        cancel_result.scalars.return_value.all.return_value = []

        db.execute.side_effect = [
            instance_result,   # _get_instance
            record_result,     # 检查审批记录
            cancel_result,     # _cancel_pending_tasks
        ]

        engine = ApprovalEngine(db)
        engine._notify_applicant = AsyncMock()

        result = await engine._do_withdraw("inst-1", "user-1")

        assert result.status == "withdrawn"
        assert result.cancelled_at is not None
        assert result.completed_reason == "normal"

    @patch("app.modules.approval_flows.engine.get_current_tenant_id", return_value="tenant-1")
    async def test_withdraw_by_non_applicant_raises(self, mock_tenant):
        """非申请人撤回抛 ValueError"""
        db = _make_db_session()

        instance = _make_instance(applicant_id="user-1", status="pending")

        instance_result = MagicMock()
        instance_result.scalar_one_or_none.return_value = instance

        db.execute.side_effect = [instance_result]

        engine = ApprovalEngine(db)

        with pytest.raises(ValueError, match="仅发起人可以撤回"):
            await engine._do_withdraw("inst-1", "user-999")


# ============================================================
# _advance
# ============================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestAdvance:
    """测试节点推进"""

    @patch("app.modules.approval_flows.engine.get_current_tenant_id", return_value="tenant-1")
    async def test_advance_to_end_completes(self, mock_tenant):
        """推进到结束节点，流程完成"""
        db = _make_db_session()

        snapshot = _build_snapshot_with_nodes([
            _make_snapshot_node("approval_1", "部门审批", "approval", "or", sort_order=1),
            _make_snapshot_node("end", "结束", "end", sort_order=2),
        ])

        instance = _make_instance(current_node_key="approval_1")
        instance.form_data = {}

        flow_def = _make_flow_def(snapshot=snapshot)
        flow_def_result = MagicMock()
        flow_def_result.scalar_one_or_none.return_value = flow_def

        # _load_nodes 查询
        db.execute.return_value = flow_def_result

        engine = ApprovalEngine(db)
        engine._notify_applicant = AsyncMock()

        current_node = MagicMock()
        current_node.node_key = "approval_1"
        current_node.node_name = "部门审批"
        current_node.node_type = "approval"
        current_node.id = "approval_1"
        current_node.sort_order = 1
        current_node.conditions = []

        await engine._advance(instance, current_node)

        assert instance.status == "approved"
        assert instance.current_node_key is None
        assert instance.approved_at is not None
        assert instance.completed_reason == "normal"

    @patch("app.modules.approval_flows.engine.get_current_tenant_id", return_value="tenant-1")
    async def test_advance_skips_condition_nodes(self, mock_tenant):
        """推进时跳过条件节点"""
        db = _make_db_session()

        snapshot = _build_snapshot_with_nodes([
            _make_snapshot_node("approval_1", "部门审批", "approval", "or", sort_order=1),
            _make_snapshot_node("cond_1", "条件判断", "condition", sort_order=2),
            _make_snapshot_node("approval_2", "总监审批", "approval", "or",
                                sort_order=3, assignee_type="user",
                                assignee_config={}),
            _make_snapshot_node("end", "结束", "end", sort_order=4),
        ])

        instance = _make_instance(current_node_key="approval_1")
        instance.form_data = {"type": "normal"}

        flow_def = _make_flow_def(snapshot=snapshot)

        # _load_nodes 只需返回一次（快照模式）
        flow_def_result = MagicMock()
        flow_def_result.scalar_one_or_none.return_value = flow_def

        db.execute.return_value = flow_def_result

        engine = ApprovalEngine(db)
        engine.assignee_resolver = MagicMock()
        engine.assignee_resolver.resolve = AsyncMock(
            return_value=[{"id": "approver-2", "name": "总监"}]
        )

        current_node = MagicMock()
        current_node.node_key = "approval_1"
        current_node.node_name = "部门审批"
        current_node.node_type = "approval"
        current_node.id = "approval_1"
        current_node.sort_order = 1
        current_node.conditions = []

        await engine._advance(instance, current_node)

        # 推进到 approval_2（跳过了 condition 节点）
        assert instance.current_node_key == "approval_2"
        assert instance.status == "pending"
