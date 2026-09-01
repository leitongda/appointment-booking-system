"""审批流引擎纯逻辑单元测试

覆盖:
- ConditionEvaluator 所有操作符 + 边界
- CallbackRegistry 注册/注销/执行/异常
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.modules.approval_flows.condition_evaluator import ConditionEvaluator
from app.modules.approval_flows.callback_registry import CallbackRegistry
from app.modules.approval_flows.service_definitions import FlowDefinitionService, _normalize_listener


# ==================== ConditionEvaluator ====================


@pytest.mark.unit
class TestApprovalListenerNormalization:
    """测试前端监听器 payload 到运行时契约的兼容转换"""

    def test_normalize_node_listener_action_config(self):
        listener = _normalize_listener({
            "event": "start",
            "actionType": "webhook",
            "actionConfig": {
                "url": "https://example.com/hook",
                "bodyTemplate": "{\"id\":\"{{instanceId}}\"}",
            },
        })

        assert listener["action"] == "webhook"
        assert listener["config"]["url"] == "https://example.com/hook"
        assert listener["config"]["body_template"] == "{\"id\":\"{{instanceId}}\"}"

    def test_normalize_global_listener_config(self):
        listener = _normalize_listener({
            "event": "process.end",
            "actionType": "callback",
            "config": {"callbackName": "on_approved"},
        })

        assert listener["action"] == "callback"
        assert listener["config"]["callback_action"] == "on_approved"


@pytest.mark.unit
@pytest.mark.asyncio
class TestFlowDefinitionGraphValidation:
    """测试流程定义图结构校验"""

    def _node(
        self,
        key: str,
        name: str,
        node_type: str,
        conditions: list | None = None,
        assignee_type: str | None = "user",
        assignee_config: dict | None = None,
    ):
        node = MagicMock()
        node.node_key = key
        node.node_name = name
        node.node_type = node_type
        node.conditions = conditions or []
        node.assignee_type = assignee_type
        node.assignee_config = assignee_config if assignee_config is not None else {"user_ids": ["u1"]}
        return node

    def _condition(self, target: str):
        condition = MagicMock()
        condition.target_node_key = target
        return condition

    async def test_validate_rejects_ambiguous_normal_node_edges(self):
        flow_def = MagicMock()
        flow_def.nodes = [
            self._node("start", "开始", "start"),
            self._node("approval_1", "部门审批", "approval"),
            self._node("approval_2", "总监审批", "approval"),
            self._node("end", "结束", "end"),
        ]
        flow_def.edges = [
            {"source": "start", "target": "approval_1"},
            {"source": "approval_1", "target": "approval_2"},
            {"source": "approval_1", "target": "end"},
            {"source": "approval_2", "target": "end"},
        ]

        service = FlowDefinitionService(AsyncMock())
        service.get_by_id = AsyncMock(return_value=flow_def)

        result = await service.validate("fd-1")

        assert result["valid"] is False
        assert any("存在多条出边" in error for error in result["errors"])

    async def test_validate_rejects_condition_targets_without_edges_and_duplicate_default(self):
        flow_def = MagicMock()
        flow_def.nodes = [
            self._node("start", "开始", "start"),
            self._node("cond_1", "条件判断", "condition", [self._condition("manager_approval")]),
            self._node("manager_approval", "经理审批", "approval"),
            self._node("normal_approval", "普通审批", "approval"),
            self._node("end", "结束", "end"),
        ]
        flow_def.edges = [
            {"source": "start", "target": "cond_1"},
            {"source": "cond_1", "target": "normal_approval", "sourceHandle": "default"},
            {"source": "cond_1", "target": "end", "sourceHandle": "default"},
            {"source": "manager_approval", "target": "end"},
            {"source": "normal_approval", "target": "end"},
        ]

        service = FlowDefinitionService(AsyncMock())
        service.get_by_id = AsyncMock(return_value=flow_def)

        result = await service.validate("fd-1")

        assert result["valid"] is False
        assert any("默认分支只能有一条" in error for error in result["errors"])
        assert any("条件目标缺少连线" in error for error in result["errors"])

@pytest.mark.unit
class TestConditionEvaluatorOperators:
    """测试条件求值器所有操作符"""

    def setup_method(self):
        self.evaluator = ConditionEvaluator()

    def _make_cond(self, field_name, operator, value, target="target_node", priority=1):
        cond = MagicMock()
        cond.field_name = field_name
        cond.operator = operator
        cond.value = value
        cond.target_node_key = target
        cond.priority = priority
        return cond

    def test_eq_match(self):
        cond = self._make_cond("type", "eq", "stop_clinic")
        result = self.evaluator.evaluate_conditions([cond], {"type": "stop_clinic"})
        assert result == "target_node"

    def test_eq_no_match(self):
        cond = self._make_cond("type", "eq", "stop_clinic")
        result = self.evaluator.evaluate_conditions([cond], {"type": "schedule_change"})
        assert result is None

    def test_neq(self):
        cond = self._make_cond("type", "neq", "stop_clinic")
        assert self.evaluator.evaluate_conditions([cond], {"type": "other"}) == "target_node"
        assert self.evaluator.evaluate_conditions([cond], {"type": "stop_clinic"}) is None

    def test_gt(self):
        cond = self._make_cond("amount", "gt", "100")
        assert self.evaluator.evaluate_conditions([cond], {"amount": 150}) == "target_node"
        assert self.evaluator.evaluate_conditions([cond], {"amount": 50}) is None
        assert self.evaluator.evaluate_conditions([cond], {"amount": 100}) is None

    def test_gte(self):
        cond = self._make_cond("amount", "gte", "100")
        assert self.evaluator.evaluate_conditions([cond], {"amount": 100}) == "target_node"
        assert self.evaluator.evaluate_conditions([cond], {"amount": 99}) is None

    def test_lt(self):
        cond = self._make_cond("amount", "lt", "100")
        assert self.evaluator.evaluate_conditions([cond], {"amount": 50}) == "target_node"
        assert self.evaluator.evaluate_conditions([cond], {"amount": 150}) is None

    def test_lte(self):
        cond = self._make_cond("amount", "lte", "100")
        assert self.evaluator.evaluate_conditions([cond], {"amount": 100}) == "target_node"
        assert self.evaluator.evaluate_conditions([cond], {"amount": 101}) is None

    def test_in_with_list(self):
        cond = self._make_cond("status", "in", ["pending", "draft"])
        assert self.evaluator.evaluate_conditions([cond], {"status": "pending"}) == "target_node"
        assert self.evaluator.evaluate_conditions([cond], {"status": "approved"}) is None

    def test_in_with_json_string(self):
        cond = self._make_cond("status", "in", '["pending", "draft"]')
        assert self.evaluator.evaluate_conditions([cond], {"status": "pending"}) == "target_node"

    def test_not_in(self):
        cond = self._make_cond("status", "not_in", ["cancelled", "rejected"])
        assert self.evaluator.evaluate_conditions([cond], {"status": "pending"}) == "target_node"
        assert self.evaluator.evaluate_conditions([cond], {"status": "cancelled"}) is None

    def test_contains(self):
        cond = self._make_cond("reason", "contains", "出差")
        assert self.evaluator.evaluate_conditions([cond], {"reason": "因出差需要调班"}) == "target_node"
        assert self.evaluator.evaluate_conditions([cond], {"reason": "个人原因"}) is None

    def test_exists_true(self):
        cond = self._make_cond("department_id", "exists", True)
        assert self.evaluator.evaluate_conditions([cond], {"department_id": "d1"}) == "target_node"
        assert self.evaluator.evaluate_conditions([cond], {"department_id": None}) is None

    def test_exists_false(self):
        cond = self._make_cond("department_id", "exists", False)
        # 注意: evaluator 在 field_value is None 时会 skip，所以 exists=false
        # 只能在字段存在但值为 falsy（如 0, ""）时匹配
        assert self.evaluator.evaluate_conditions([cond], {"department_id": ""}) is None
        assert self.evaluator.evaluate_conditions([cond], {"department_id": "d1"}) is None


@pytest.mark.unit
class TestConditionEvaluatorEdgeCases:
    """测试边界情况"""

    def setup_method(self):
        self.evaluator = ConditionEvaluator()

    def _make_cond(self, field_name, operator, value, target="t", priority=1):
        cond = MagicMock()
        cond.field_name = field_name
        cond.operator = operator
        cond.value = value
        cond.target_node_key = target
        cond.priority = priority
        return cond

    def test_empty_conditions(self):
        result = self.evaluator.evaluate_conditions([], {"type": "x"})
        assert result is None

    def test_field_not_in_form_data(self):
        cond = self._make_cond("missing_field", "eq", "value")
        result = self.evaluator.evaluate_conditions([cond], {"other": "value"})
        assert result is None

    def test_unknown_operator(self):
        cond = self._make_cond("type", "unknown_op", "value")
        result = self.evaluator.evaluate_conditions([cond], {"type": "value"})
        assert result is None

    def test_priority_ordering(self):
        """低 priority 数字 = 更高优先级，先匹配"""
        cond_low = self._make_cond("type", "eq", "a", target="low", priority=10)
        cond_high = self._make_cond("type", "eq", "a", target="high", priority=1)
        result = self.evaluator.evaluate_conditions([cond_low, cond_high], {"type": "a"})
        assert result == "high"

    def test_first_match_wins(self):
        """同优先级时，第一个匹配的胜出"""
        cond1 = self._make_cond("type", "eq", "a", target="first", priority=1)
        cond2 = self._make_cond("type", "eq", "a", target="second", priority=1)
        result = self.evaluator.evaluate_conditions([cond1, cond2], {"type": "a"})
        assert result == "first"

    def test_type_coercion_eq(self):
        """eq 操作符使用 str 比较，数字和字符串可比较"""
        cond = self._make_cond("count", "eq", "5")
        assert self.evaluator.evaluate_conditions([cond], {"count": 5}) is not None

    def test_type_error_in_comparison(self):
        """类型错误不崩溃，跳过该条件"""
        cond = self._make_cond("amount", "gt", "not_a_number")
        result = self.evaluator.evaluate_conditions([cond], {"amount": 100})
        assert result is None


# ==================== ConditionEvaluator (condition groups OR + AND) ====================

@pytest.mark.unit
class TestConditionEvaluatorGroups:
    """测试条件组求值：组内 AND，组间 OR"""

    def setup_method(self):
        self.evaluator = ConditionEvaluator()

    def _make_cond(self, field_name, operator, value, target="t", priority=1, group_id=None):
        cond = MagicMock()
        cond.field_name = field_name
        cond.operator = operator
        cond.value = value
        cond.target_node_key = target
        cond.priority = priority
        cond.group_id = group_id
        return cond

    def test_backward_compat_no_group_id(self):
        """无 group_id 时，行为等价于 evaluate_conditions（单条件独立匹配）"""
        cond1 = self._make_cond("type", "eq", "a", target="target_a", group_id=None)
        cond2 = self._make_cond("type", "eq", "b", target="target_b", group_id=None)
        assert self.evaluator.evaluate_condition_groups([cond1, cond2], {"type": "a"}) == "target_a"
        assert self.evaluator.evaluate_condition_groups([cond1, cond2], {"type": "b"}) == "target_b"
        assert self.evaluator.evaluate_condition_groups([cond1, cond2], {"type": "c"}) is None

    def test_same_group_and_logic(self):
        """同一 group_id 内的条件为 AND 关系"""
        cond1 = self._make_cond("amount", "gt", "100", target="t", group_id="g0")
        cond2 = self._make_cond("type", "eq", "special", target="t", group_id="g0")
        # 两个都满足
        assert self.evaluator.evaluate_condition_groups(
            [cond1, cond2], {"amount": 200, "type": "special"}
        ) == "t"
        # 只满足一个
        assert self.evaluator.evaluate_condition_groups(
            [cond1, cond2], {"amount": 200, "type": "normal"}
        ) is None
        assert self.evaluator.evaluate_condition_groups(
            [cond1, cond2], {"amount": 50, "type": "special"}
        ) is None

    def test_different_groups_or_logic(self):
        """不同 group_id 之间为 OR 关系"""
        cond_g0 = self._make_cond("amount", "gt", "1000", target="t", group_id="g0")
        cond_g1 = self._make_cond("type", "eq", "vip", target="t", group_id="g1")
        # 满足组0
        assert self.evaluator.evaluate_condition_groups(
            [cond_g0, cond_g1], {"amount": 2000, "type": "normal"}
        ) == "t"
        # 满足组1
        assert self.evaluator.evaluate_condition_groups(
            [cond_g0, cond_g1], {"amount": 500, "type": "vip"}
        ) == "t"
        # 都不满足
        assert self.evaluator.evaluate_condition_groups(
            [cond_g0, cond_g1], {"amount": 500, "type": "normal"}
        ) is None

    def test_mixed_and_or(self):
        """混合场景：两组条件，组内 AND，组间 OR"""
        # 组0: amount > 1000 AND type == "large"
        c0a = self._make_cond("amount", "gt", "1000", target="approval_a", group_id="g0")
        c0b = self._make_cond("type", "eq", "large", target="approval_a", group_id="g0")
        # 组1: amount <= 100 AND type == "small"
        c1a = self._make_cond("amount", "lte", "100", target="approval_a", group_id="g1")
        c1b = self._make_cond("type", "eq", "small", target="approval_a", group_id="g1")

        conds = [c0a, c0b, c1a, c1b]
        # 满足组0（大额大件）
        assert self.evaluator.evaluate_condition_groups(
            conds, {"amount": 5000, "type": "large"}
        ) == "approval_a"
        # 满足组1（小额小件）
        assert self.evaluator.evaluate_condition_groups(
            conds, {"amount": 50, "type": "small"}
        ) == "approval_a"
        # 中间值：不满足任一组
        assert self.evaluator.evaluate_condition_groups(
            conds, {"amount": 500, "type": "medium"}
        ) is None
        # 只满足部分条件（组0只满足amount）
        assert self.evaluator.evaluate_condition_groups(
            conds, {"amount": 2000, "type": "small"}
        ) is None

    def test_priority_ordering_among_groups(self):
        """不同优先级的组，高优先级先评估"""
        low = self._make_cond("type", "eq", "a", target="low", priority=10, group_id="g_low")
        high = self._make_cond("type", "eq", "a", target="high", priority=1, group_id="g_high")
        assert self.evaluator.evaluate_condition_groups([low, high], {"type": "a"}) == "high"

    def test_empty_conditions(self):
        assert self.evaluator.evaluate_condition_groups([], {"type": "x"}) is None

    def test_mixed_grouped_and_ungrouped(self):
        """混合有 group_id 和无 group_id 的条件"""
        ungrouped = self._make_cond("type", "eq", "a", target="t1", group_id=None)
        grouped = self._make_cond("amount", "gt", "100", target="t2", group_id="g0")
        # 匹配无分组条件
        assert self.evaluator.evaluate_condition_groups(
            [ungrouped, grouped], {"type": "a", "amount": 50}
        ) == "t1"
        # 匹配有分组条件
        assert self.evaluator.evaluate_condition_groups(
            [ungrouped, grouped], {"type": "b", "amount": 200}
        ) == "t2"


# ==================== CallbackRegistry ====================

@pytest.mark.unit
class TestCallbackRegistry:
    """测试回调注册表"""

    def test_register_and_execute(self):
        registry = CallbackRegistry()
        handler = AsyncMock()

        registry.register("test_type", handler)
        instance = MagicMock()
        db = MagicMock()

        asyncio.run(
            registry.execute("test_type", "on_approved", instance, db)
        )
        handler.assert_called_once_with("on_approved", instance, db)

    def test_unregister(self):
        registry = CallbackRegistry()
        handler = AsyncMock()
        registry.register("test_type", handler)
        registry.unregister("test_type")

        asyncio.run(
            registry.execute("test_type", "on_approved", MagicMock(), MagicMock())
        )
        handler.assert_not_called()

    def test_execute_unregistered_type(self):
        """未注册的 business_type 不崩溃"""
        registry = CallbackRegistry()
        asyncio.run(
            registry.execute("unknown_type", "on_approved", MagicMock(), MagicMock())
        )

    def test_execute_handler_exception(self):
        """处理器异常自然传播到调用方"""
        registry = CallbackRegistry()
        handler = AsyncMock(side_effect=RuntimeError("boom"))
        registry.register("fail_type", handler)

        with pytest.raises(RuntimeError):
            asyncio.run(
                registry.execute("fail_type", "on_approved", MagicMock(), MagicMock())
            )

    def test_multiple_registrations(self):
        """后注册的覆盖先注册的"""
        registry = CallbackRegistry()
        handler1 = AsyncMock()
        handler2 = AsyncMock()

        registry.register("biz", handler1)
        registry.register("biz", handler2)

        asyncio.run(
            registry.execute("biz", "on_approved", MagicMock(), MagicMock())
        )
        handler1.assert_not_called()
        handler2.assert_called_once()

    def test_singleton_instance(self):
        """callback_registry 是全局单例"""
        from app.modules.approval_flows.callback_registry import callback_registry as r1
        from app.modules.approval_flows.callback_registry import callback_registry as r2
        assert r1 is r2
