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

    def evaluate_conditions(
        self,
        conditions: list,
        form_data: dict[str, Any],
    ) -> str | None:
        """
        求值条件列表，返回满足条件的 target_node_key。

        按 priority 排序，返回第一个匹配的。
        如果都不匹配，返回 None（走默认路径）。

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
            field_value = form_data.get(cond.field_name)
            if field_value is None:
                continue

            op = self.OPERATORS.get(cond.operator)
            if not op:
                logger.warning(f"未知的操作符: {cond.operator}")
                continue

            try:
                # 解析条件值
                cond_value = cond.value
                if isinstance(cond_value, str):
                    try:
                        cond_value = json.loads(cond_value)
                    except (json.JSONDecodeError, TypeError):
                        pass

                if op(field_value, cond_value):
                    logger.debug(
                        f"条件匹配: {cond.field_name} {cond.operator} {cond.value} -> {cond.target_node_key}"
                    )
                    return cond.target_node_key
            except (ValueError, TypeError) as e:
                logger.warning(f"条件求值失败: {cond.field_name} {cond.operator} {cond.value}: {e}")
                continue

        return None
