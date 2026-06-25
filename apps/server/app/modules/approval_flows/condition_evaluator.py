"""条件规则求值器"""
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ConditionEvaluator:
    """条件规则求值 - 根据 form_data 和条件规则决定分支路由"""

    OPERATORS = {
        "eq": lambda a, b: str(a) == str(b),
        "neq": lambda a, b: str(a) != str(b),
        "gt": lambda a, b: float(a) > float(b),
        "gte": lambda a, b: float(a) >= float(b),
        "lt": lambda a, b: float(a) < float(b),
        "lte": lambda a, b: float(a) <= float(b),
        "in": lambda a, b: a in (b if isinstance(b, list) else json.loads(b)),
        "not_in": lambda a, b: a not in (b if isinstance(b, list) else json.loads(b)),
        "contains": lambda a, b: str(b) in str(a),
        "exists": lambda a, b: (a is not None) == bool(b),
    }

    def _eval_single(self, cond: Any, form_data: dict[str, Any]) -> bool:
        """求值单个条件，返回是否匹配"""
        field_value = form_data.get(cond.field_name)
        if field_value is None:
            return False

        op = self.OPERATORS.get(cond.operator)
        if not op:
            logger.warning(f"未知的操作符: {cond.operator}")
            return False

        try:
            cond_value = cond.value
            if isinstance(cond_value, str):
                try:
                    cond_value = json.loads(cond_value)
                except (json.JSONDecodeError, TypeError):
                    pass
            return bool(op(field_value, cond_value))
        except (ValueError, TypeError) as e:
            logger.warning(f"条件求值失败: {cond.field_name} {cond.operator} {cond.value}: {e}")
            return False

    def evaluate_conditions(
        self,
        conditions: list,
        form_data: dict[str, Any],
    ) -> str | None:
        """
        求值条件列表，返回满足条件的 target_node_key。

        按 priority 排序，返回第一个匹配的。
        如果都不匹配，返回 None（走默认路径）。

        保持向后兼容：无 group_id 的条件按原始逻辑（单条件独立评估）处理。

        Args:
            conditions: ApprovalFlowCondition 列表
            form_data: 发起审批时的表单数据

        Returns:
            满足条件的 target_node_key，或 None
        """
        if not conditions:
            return None

        sorted_conds = sorted(conditions, key=lambda c: c.priority)
        for cond in sorted_conds:
            if self._eval_single(cond, form_data):
                logger.debug(
                    f"条件匹配: {cond.field_name} {cond.operator} {cond.value} -> {cond.target_node_key}"
                )
                return cond.target_node_key

        return None

    def evaluate_condition_groups(
        self,
        conditions: list,
        form_data: dict[str, Any],
    ) -> str | None:
        """
        求值条件组列表，返回满足条件的 target_node_key。

        语义：
        - 按 (target_node_key, group_id) 分组
        - 同组内条件 AND（全部满足才算该组匹配）
        - 不同组之间 OR（任一组匹配即返回 target_node_key）
        - 组间按 priority 最小值排序，优先级高的先评估

        向后兼容：
        - 无 group_id（None 或缺失）的条件视为独立组，单条件即匹配
        - 等价于原来的 evaluate_conditions 行为

        Args:
            conditions: ApprovalFlowCondition 列表
            form_data: 发起审批时的表单数据

        Returns:
            满足条件的 target_node_key，或 None
        """
        if not conditions:
            return None

        # 按 (target_node_key, group_id) 分组
        groups: dict[tuple[str, str | None], list] = {}
        for cond in conditions:
            group_id = getattr(cond, "group_id", None)
            key = (cond.target_node_key, group_id)
            groups.setdefault(key, []).append(cond)

        # 按组内最小 priority 排序
        sorted_groups = sorted(
            groups.items(),
            key=lambda item: min(c.priority for c in item[1]),
        )

        for (target_key, _group_id), group_conds in sorted_groups:
            if all(self._eval_single(c, form_data) for c in group_conds):
                logger.debug(
                    f"条件组匹配: target={target_key}, "
                    f"group_id={_group_id}, "
                    f"conditions={[c.field_name for c in group_conds]}"
                )
                return target_key

        return None
