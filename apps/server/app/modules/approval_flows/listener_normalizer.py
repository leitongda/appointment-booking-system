"""审批流监听器配置归一化工具

提供监听器 ``config`` 字段的 camelCase -> snake_case 兼容映射，消除
``listener_service._normalize_config`` 与 ``service_definitions._normalize_listener``
之间的重复实现。

归一化规则（行为保持，与原实现一致）:
    bodyTemplate      -> body_template
    titleTemplate     -> title_template
    contentTemplate   -> content_template
    userIds           -> user_ids
    targetIds         -> user_ids      （与 userIds 合并到同一字段）
    callbackName      -> callback_action

填充语义: 仅当源键存在且目标键缺失时写入，不会覆盖显式提供的 snake_case 键，
也不会删除原始 camelCase 键（保持向后兼容的外部可观察行为）。
"""
from __future__ import annotations

from typing import Any

# camelCase 源键 -> snake_case 目标键（顺序即 user_ids/targetIds 合并的目标顺序）
_LISTENER_CONFIG_ALIASES: dict[str, str] = {
    "bodyTemplate": "body_template",
    "titleTemplate": "title_template",
    "contentTemplate": "content_template",
    "userIds": "user_ids",
    "targetIds": "user_ids",
    "callbackName": "callback_action",
}


def normalize_listener_config(config: dict[str, Any] | None) -> dict[str, Any]:
    """归一化监听器 ``config`` 字段，返回新的 dict（纯函数，无副作用）。

    - ``config`` 为 ``None`` 时返回空 dict。
    - 复制输入后再做别名填充，**不会**修改调用方传入的 dict。
    - 仅当 ``source`` 键存在且 ``target`` 键缺失时写入，不覆盖、不删除原始键。
    """
    normalized: dict[str, Any] = dict(config or {})
    for source, target in _LISTENER_CONFIG_ALIASES.items():
        if source in normalized and target not in normalized:
            normalized[target] = normalized[source]
    return normalized
