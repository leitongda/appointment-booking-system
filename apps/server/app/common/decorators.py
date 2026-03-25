"""
装饰器模块

包含通用的装饰器函数，如租户一致性校验等。
"""
from functools import wraps
from typing import Callable, Optional

from fastapi import HTTPException


from app.middleware.tenant_context import get_current_tenant_id


def require_tenant_match(func: Callable) -> Callable:
    """
    确保请求租户与当前用户租户匹配的装饰器

    用于保护关键业务接口，防止跨租户数据访问。
    超级管理员可以跳过此检查。

    Args:
        func: 需要保护的函数

    Returns:
        包装后的函数

    Raises:
        HTTPException: 当租户不匹配时抛出 403 错误

    Example:
        @router.post("/appointments")
        @require_tenant_match
        async def create_appointment(
            data: AppointmentCreate,
            current_admin: dict = Depends(get_current_admin),
            db: AsyncSession = Depends(get_db),
        ):
            ...
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # 尝试从参数中获取 current_admin
        current_admin = kwargs.get("current_admin")

        # 如果没有 current_admin，直接执行原函数
        if not current_admin:
            return await func(*args, **kwargs)

        # 超管跳过检查
        if current_admin.get("is_super_admin"):
            return await func(*args, **kwargs)

        # 获取请求租户
        request_tenant_id = get_current_tenant_id()

        # 如果请求没有租户上下文，直接执行（由其他中间件处理）
        if not request_tenant_id:
            return await func(*args, **kwargs)

        # 获取用户租户
        user_tenant_id = current_admin.get("tenant_id")

        # 验证匹配
        if user_tenant_id and request_tenant_id != user_tenant_id:
            raise HTTPException(
                status_code=403,
                detail="无权访问该租户数据"
            )

        return await func(*args, **kwargs)

    return wrapper


def require_tenant_context(func: Callable) -> Callable:
    """
    确保请求有有效的租户上下文的装饰器

    用于必须识别租户的接口。

    Args:
        func: 需要保护的函数

    Returns:
        包装后的函数

    Raises:
        HTTPException: 当缺少租户上下文时抛出 400 错误

    Example:
        @router.post("/public/appointments")
        @require_tenant_context
        async def public_create_appointment(...):
            ...
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # 获取请求租户
        request_tenant_id = get_current_tenant_id()

        if not request_tenant_id:
            raise HTTPException(
                status_code=400,
                detail="缺少租户上下文，请通过 X-Tenant-ID 或 X-Tenant-Code 指定租户"
            )

        return await func(*args, **kwargs)

    return wrapper
