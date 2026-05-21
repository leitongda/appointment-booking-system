"""业务模块回调注册表

业务模块在启动时注册自己的回调函数，引擎在审批完成时调用。
"""
import logging
from typing import Callable, Dict, Optional, Any
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
        self._handlers: Dict[str, Callable] = {}

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

        try:
            await handler(action, instance, db)
        except Exception as e:
            logger.error(f"执行回调失败: {business_type} {action}: {e}", exc_info=True)
            # 回调失败不阻塞主流程，仅记录日志


# 全局单例
callback_registry = CallbackRegistry()
