"""租户相关依赖

提供租户校验、上下文管理、状态检查、用量限制等依赖函数。
"""
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional

from app.db.session import get_db
from app.models.tenant import Tenant
from app.middleware.tenant_context import (
    get_current_tenant_id,
    get_current_tenant_code,
)

# 重新导出认证依赖，因为租户依赖依赖它们
from app.common.auth_deps import get_current_admin


async def get_current_tenant(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[dict]:
    """获取当前租户信息

    从请求上下文中获取租户信息（由 TenantContextMiddleware 设置）。
    如果租户不存在或未识别，返回 None。

    返回值包含：
    - id: 租户ID
    - tenant_code: 租户编码
    - name: 租户名称
    - status: 租户状态
    - subscription_plan_id: 当前订阅计划ID
    - is_subscription_active: 订阅是否有效
    """
    # 从上下文获取租户ID或编码
    tenant_id = get_current_tenant_id()
    tenant_code = get_current_tenant_code()

    # 也检查请求状态（中间件设置的）
    if not tenant_id and hasattr(request.state, 'tenant_id'):
        tenant_id = request.state.tenant_id
    if not tenant_code and hasattr(request.state, 'tenant_code'):
        tenant_code = request.state.tenant_code

    if not tenant_id and not tenant_code:
        return None

    # 从数据库获取租户信息
    query = select(Tenant).options(
        selectinload(Tenant.subscription_plan)
    )

    if tenant_id:
        query = query.where(Tenant.id == tenant_id)
    else:
        query = query.where(Tenant.tenant_code == tenant_code)

    result = await db.execute(query)
    tenant = result.scalar_one_or_none()

    if not tenant:
        return None

    # 检查租户状态
    if tenant.status == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="租户已被禁用"
        )

    return {
        "id": tenant.id,
        "tenant_code": tenant.tenant_code,
        "name": tenant.name,
        "status": tenant.status,
        "subscription_plan_id": tenant.subscription_plan_id,
        "subscription_start_at": tenant.subscription_start_at,
        "subscription_end_at": tenant.subscription_end_at,
        "is_subscription_active": tenant.is_subscription_active,
        "max_stores": tenant.get_effective_max_stores(),
        "max_admins": tenant.get_effective_max_admins(),
        "max_doctors": tenant.get_effective_max_doctors(),
        "max_appointments_per_month": tenant.get_effective_max_appointments(),
    }


async def get_current_tenant_or_404(
    tenant: Optional[dict] = Depends(get_current_tenant)
) -> dict:
    """获取当前租户，如果不存在则返回404

    用于必须识别租户的接口。
    """
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="租户不存在或未识别"
        )
    return tenant


async def get_platform_admin(
    current_admin: dict = Depends(get_current_admin)
) -> dict:
    """获取平台管理员（仅平台管理员可访问）

    平台管理员是 tenant_id 为 NULL 的管理员。
    """
    if not current_admin.get("is_super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="此操作仅限平台管理员"
        )
    return current_admin


def get_tenant_filter(current_admin: dict = Depends(get_current_admin)) -> Optional[str]:
    """获取租户过滤条件

    用于数据查询时自动添加租户过滤。

    Returns:
        - None: 平台管理员，不过滤，可查看所有租户数据
        - str: 租户ID，只能查看本租户数据
    """
    if current_admin.get("is_super_admin"):
        # 平台管理员可以查看所有租户数据
        return None

    # 租户管理员只能查看本租户数据
    return current_admin.get("tenant_id")


async def check_tenant_access(
    current_admin: dict,
    target_tenant_id: Optional[str],
    db: AsyncSession
) -> bool:
    """检查当前管理员是否有权访问目标租户

    平台管理员可以访问任何租户
    租户管理员只能访问自己的租户
    """
    if current_admin.get("is_super_admin"):
        return True

    if not target_tenant_id:
        return False

    admin_tenant_id = current_admin.get("tenant_id")
    return admin_tenant_id == target_tenant_id


async def get_tenant_from_admin(
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
) -> Optional[dict]:
    """从当前管理员获取租户信息

    如果管理员关联了租户，返回租户详情（含订阅计划状态）。
    平台管理员（tenant_id 为 NULL）返回 None。

    注意：tenant_id 直接从 admin 记录获取（P0 多租户修复后所有管理员均已关联 tenant_id），
    不再通过门店反查推断。
    """
    if current_admin.get("is_super_admin"):
        return None

    tenant_id = current_admin.get("tenant_id")
    if not tenant_id:
        return None

    # 获取租户详情
    result = await db.execute(
        select(Tenant).options(
            selectinload(Tenant.subscription_plan)
        ).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        return None

    return {
        "id": tenant.id,
        "tenant_code": tenant.tenant_code,
        "name": tenant.name,
        "status": tenant.status,
        "subscription_plan_id": tenant.subscription_plan_id,
        "is_subscription_active": tenant.is_subscription_active,
    }


def require_tenant_admin() -> callable:
    """创建租户管理员权限检查依赖

    确保当前用户是某个租户的管理员（非平台管理员）。
    """
    async def check_tenant_admin(
        current_admin: dict = Depends(get_current_admin),
        tenant: Optional[dict] = Depends(get_tenant_from_admin)
    ) -> dict:
        if current_admin.get("is_super_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="此接口仅限租户管理员访问"
            )

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="未关联租户"
            )

        return current_admin

    return check_tenant_admin


def require_platform_admin() -> callable:
    """创建平台管理员权限检查依赖

    确保当前用户是平台管理员。
    """
    async def check_platform_admin(
        current_admin: dict = Depends(get_current_admin)
    ) -> dict:
        if not current_admin.get("is_super_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="此接口仅限平台管理员访问"
            )
        return current_admin

    return check_platform_admin


def check_tenant_role_access(current_admin: dict, required_role: str = None) -> None:
    """检查租户角色权限

    用于验证管理员是否有权访问当前租户数据。

    Args:
        current_admin: 当前管理员信息
        required_role: 可选的角色要求（如 "TENANT_ADMIN", "STORE_ADMIN"）

    Raises:
        HTTPException: 如果权限不足
    """
    # 平台管理员可以访问所有租户
    if current_admin.get("is_platform_admin") or current_admin.get("is_super_admin"):
        return

    # 获取当前租户上下文
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="需要租户上下文"
        )

    # 租户管理员只能访问本租户
    admin_tenant_id = current_admin.get("tenant_id")
    if admin_tenant_id and admin_tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问该租户数据"
        )

    # 如果指定了角色要求，检查角色
    if required_role:
        role_code = current_admin.get("role_code", "")
        role_name = current_admin.get("role_name", "")

        # 角色匹配检查
        role_match = (
            role_code == required_role or
            role_name == required_role or
            # 租户管理员拥有门店管理员权限
            (required_role == "STORE_ADMIN" and role_code in ["TENANT_ADMIN", "SUPER_ADMIN"]) or
            # 超级管理员拥有所有权限
            role_code in ["SUPER_ADMIN", "PLATFORM_ADMIN"]
        )

        if not role_match:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要 {required_role} 角色"
            )


async def validate_tenant_consistency(
    db: AsyncSession,
    data: dict,
    tenant_id: str,
    related_fields: dict = None
) -> None:
    """验证关联数据的租户一致性

    在创建或更新数据时，验证所有关联数据都属于同一租户。

    Args:
        db: 数据库会话
        data: 要验证的数据字典
        tenant_id: 目标租户ID
        related_fields: 需要验证的关联字段配置
            {
                "store_id": Store,  # 字段名: 模型类
                "doctor_id": Doctor,
            }

    Raises:
        HTTPException: 如果关联数据不属于目标租户
    """
    if not related_fields:
        return

    for field_name, model_class in related_fields.items():
        field_value = data.get(field_name)
        if not field_value:
            continue

        # 查询关联数据的租户ID
        result = await db.execute(
            select(model_class).where(model_class.id == field_value)
        )
        related_obj = result.scalar_one_or_none()

        if not related_obj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} 不存在"
            )

        # 检查租户一致性
        related_tenant_id = getattr(related_obj, 'tenant_id', None)
        if related_tenant_id and related_tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{field_name} 不属于当前租户"
            )


def require_tenant_context() -> callable:
    """创建租户上下文检查依赖

    确保请求有有效的租户上下文。
    用于公开预约接口等必须识别租户的场景。
    """
    async def check_tenant_context(
        tenant: Optional[dict] = Depends(get_current_tenant)
    ) -> dict:
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="缺少租户上下文，请通过 X-Tenant-ID 或 X-Tenant-Code 指定租户"
            )
        return tenant


async def require_tenant_active_for_write(
    db: AsyncSession = Depends(get_db),
) -> None:
    """写操作守卫：禁用/欠费/到期租户禁止写入

    用于患者端预约创建、取消、改约、支付等写操作。
    只读接口不要挂载本依赖，保证租户停服时仍可浏览。
    依赖租户上下文（TenantContextMiddleware 解析的 X-Tenant-ID）。
    """
    from datetime import datetime as _dt
    from app.middleware.exception import raise_business_http_error
    from app.core.error_codes import ErrorCode as TenantErrorCode

    tenant_id = get_current_tenant_id()
    if not tenant_id:
        return  # 没有租户上下文的接口由其他守卫负责

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return

    if tenant.status == 0:
        raise_business_http_error(
            status.HTTP_403_FORBIDDEN,
            TenantErrorCode.TENANT_DISABLED,
            "该机构已暂停服务，请联系机构管理员",
        )
    if tenant.status == 2:
        raise_business_http_error(
            status.HTTP_403_FORBIDDEN,
            TenantErrorCode.TENANT_SUSPENDED_WRITE,
            "该机构订阅已到期，暂不支持新预约/支付，请联系机构续费",
        )
    if (
        tenant.subscription_end_at is not None
        and tenant.subscription_end_at < _dt.utcnow()
    ):
        # 试用期到期 vs 正式订阅到期，区分错误码
        code = (
            TenantErrorCode.TENANT_TRIAL_EXPIRED
            if tenant.status == 3
            else TenantErrorCode.TENANT_SUSPENDED_WRITE
        )
        raise_business_http_error(
            status.HTTP_403_FORBIDDEN,
            code,
            "该机构订阅已到期，暂不支持新预约/支付，请联系机构续费",
        )

    return None
