"""业务模块回调注册表

业务模块在启动时注册自己的回调函数，引擎在审批完成时调用。

当前状态: 已完整接入。leave_request 和 extra_quota 的回调处理器在
business_callbacks.py 中定义，通过 __init__.py 的 register_builtin_callbacks()
在模块加载时自动注册。发起端通过 _start_approval_if_configured() 调用
ApprovalEngine.start_instance()。
"""
import logging
from collections.abc import Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class CallbackRegistry:
    """
    业务模块回调注册表。

    用法:
        # 在业务模块中注册
        async def my_callback(action: str, instance: ApprovalInstance, db: AsyncSession):
            if action == "on_approved":
                ...
            elif action == "on_rejected":
                ...

        callback_registry.register("my_business_type", my_callback)

        # 引擎在审批完成时调用
        await callback_registry.execute("my_business_type", "on_approved", instance, db)
    """

    def __init__(self):
        self._handlers: dict[str, Callable] = {}

    def register(self, business_type: str, handler: Callable):
        """注册业务回调处理器"""
        self._handlers[business_type] = handler
        logger.info(f"注册审批回调: {business_type}")

    def unregister(self, business_type: str):
        """取消注册"""
        self._handlers.pop(business_type, None)

    async def execute(
        self,
        business_type: str,
        action: str,
        instance: Any,
        db: AsyncSession,
    ):
        """
        执行回调。

        Args:
            business_type: 业务类型
            action: "on_approved" / "on_rejected" / "on_cancelled"
            instance: ApprovalInstance 实例
            db: 数据库会话
        """
        handler = self._handlers.get(business_type)
        if not handler:
            logger.debug(f"未找到回调处理器: {business_type}")
            return

        await handler(action, instance, db)


# 全局单例
callback_registry = CallbackRegistry()
