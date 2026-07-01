"""业务模块回调注册表

业务模块在自身 ``__init__.py`` 被加载时注册自己的回调函数（依赖倒置），
引擎在审批完成时通过 ``execute`` 反向调用。引擎包零业务 service import。

接入示例（业务模块内）::

    # <biz_module>/callbacks.py
    async def handle_my_approval(action, instance, db): ...

    # <biz_module>/__init__.py
    from app.modules.approval_flows.callback_registry import callback_registry
    from <biz_module>.callbacks import handle_my_approval
    callback_registry.register("my_business_type", handle_my_approval)

实际接入的业务类型：``leave_request``、``extra_quota``，回调文件分别位于
``leave_requests/callbacks.py`` 与 ``schedules/callbacks_extra_quota.py``。
发起端通过业务 service 内的 ``_start_approval_if_configured()`` 调用
``ApprovalEngine.start_instance()``（函数内 lazy import，合法单向业务→引擎）。
"""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.approval_flows.types import BusinessCallback

logger = logging.getLogger(__name__)


class CallbackRegistry:
    """
    业务模块回调注册表。

    用法:
        # 在业务模块 __init__.py 中注册
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
        # 形参标注为 BusinessCallback（Protocol），仅用于静态类型提示；
        # 运行时任何符合签名的可调用对象都可注册，故用下界不做 isinstance 强校验。
        self._handlers: dict[str, BusinessCallback] = {}

    def register(self, business_type: str, handler: BusinessCallback):
        """注册业务回调处理器。

        Args:
            business_type: 业务类型标识（如 ``"leave_request"``、``"extra_quota"``）。
            handler: 符合 :class:`~app.modules.approval_flows.types.BusinessCallback`
                协议的 async 可调用对象。
        """
        self._handlers[business_type] = handler
        logger.info(f"注册审批回调: {business_type}")

    def unregister(self, business_type: str):
        """取消注册"""
        self._handlers.pop(business_type, None)

    async def execute(
        self,
        business_type: str,
        action: str,
        instance,
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
