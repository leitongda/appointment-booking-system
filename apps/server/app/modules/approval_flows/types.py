"""审批引擎的对外契约与共享工具。

本模块是引擎包的"公共出口"之一，只依赖 typing / SQLAlchemy / app.models，
**不 import 任何业务 service**。业务模块通过实现 :class:`BusinessCallback` 协议
并在自身 ``__init__.py`` 中调用 ``callback_registry.register()`` 完成解耦，
从而避免引擎包反向依赖业务包（开闭原则 / 依赖倒置）。
"""
from typing import Any, Protocol, runtime_checkable

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval_flow import ApprovalRecord


@runtime_checkable
class BusinessCallback(Protocol):
    """业务回调协议。

    业务模块实现该协议的函数（或可调用对象）后注册到
    :data:`app.modules.approval_flows.callback_registry.callback_registry`，
    引擎在审批节点动作完成时回调，执行业务侧状态变更。

    Args:
        action: 节点动作事件，取值 ``"on_approved"`` / ``"on_rejected"``
            / ``"on_cancelled"``。
        instance: 对应的 :class:`~app.models.approval_flow.ApprovalInstance`，
            业务方据 ``instance.business_id`` 取自身业务模型。
        db: 当前异步数据库会话。

    回调函数应为 ``async``，返回值被忽略。异常会向上传播到引擎调用方。
    """

    async def __call__(self, action: str, instance: Any, db: AsyncSession) -> None:
        ...


async def last_action_record(
    db: AsyncSession, instance_id: str
) -> ApprovalRecord | None:
    """取审批实例最近一次关键动作（approve / reject / withdraw）记录。

    引擎层共享工具：仅读取 :class:`~app.models.approval_flow.ApprovalRecord`
    （属于 ``app.models.approval_flow``，引擎可直接依赖），供各业务回调复用。
    """
    result = await db.execute(
        select(ApprovalRecord)
        .where(
            and_(
                ApprovalRecord.instance_id == instance_id,
                ApprovalRecord.action.in_(["approve", "reject", "withdraw"]),
            )
        )
        .order_by(ApprovalRecord.created_at.desc())
    )
    return result.scalars().first()
