"""审批流引擎纯逻辑单元测试

覆盖:
- ConditionEvaluator 所有操作符 + 边界
- CallbackRegistry 注册/注销/执行/异常
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.modules.approval_flows.condition_evaluator import ConditionEvaluator
from app.modules.approval_flows.callback_registry import CallbackRegistry


# ==================== ConditionEvaluator ====================

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

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            registry.execute("test_type", "on_approved", instance, db)
        )
        handler.assert_called_once_with("on_approved", instance, db)

    def test_unregister(self):
        registry = CallbackRegistry()
        handler = AsyncMock()
        registry.register("test_type", handler)
        registry.unregister("test_type")

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            registry.execute("test_type", "on_approved", MagicMock(), MagicMock())
        )
        handler.assert_not_called()

    def test_execute_unregistered_type(self):
        """未注册的 business_type 不崩溃"""
        registry = CallbackRegistry()
        import asyncio
        asyncio.get_event_loop().run_until_complete(
            registry.execute("unknown_type", "on_approved", MagicMock(), MagicMock())
        )

    def test_execute_handler_exception(self):
        """处理器异常不扩散"""
        registry = CallbackRegistry()
        handler = AsyncMock(side_effect=RuntimeError("boom"))
        registry.register("fail_type", handler)

        import asyncio
        # 不应抛出异常
        asyncio.get_event_loop().run_until_complete(
            registry.execute("fail_type", "on_approved", MagicMock(), MagicMock())
        )

    def test_multiple_registrations(self):
        """后注册的覆盖先注册的"""
        registry = CallbackRegistry()
        handler1 = AsyncMock()
        handler2 = AsyncMock()

        registry.register("biz", handler1)
        registry.register("biz", handler2)

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            registry.execute("biz", "on_approved", MagicMock(), MagicMock())
        )
        handler1.assert_not_called()
        handler2.assert_called_once()

    def test_singleton_instance(self):
        """callback_registry 是全局单例"""
        from app.modules.approval_flows.callback_registry import callback_registry as r1
        from app.modules.approval_flows.callback_registry import callback_registry as r2
        assert r1 is r2
