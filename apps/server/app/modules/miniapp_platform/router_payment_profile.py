"""小程序平台 - 支付配置管理路由 (PaymentProfile CRUD + set-default)"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.common.deps import get_current_admin, get_tenant_from_admin
from app.modules.miniapp_platform.schemas import (
    PaymentProfileCreate, PaymentProfileUpdate, PaymentProfileResponse,
    PaymentProfileListResponse, PaymentProfileQuery,
)
from app.modules.miniapp_platform.service import PaymentProfileService
from app.schemas.response import PageResponse

router = APIRouter()


# ==================== PaymentProfile (支付配置) ====================

@router.get("/payment-profiles", response_model=PageResponse[PaymentProfileListResponse], summary="获取支付配置列表")
async def get_payment_profiles(
    keyword: Optional[str] = None,
    status: Optional[int] = Query(None, ge=0, le=1),
    company_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant: Optional[dict] = Depends(get_tenant_from_admin)
):
    """获取支付配置列表

    平台管理员可以查看所有租户的支付配置。
    租户管理员只能查看自己租户的支付配置。
    """
    service = PaymentProfileService(db)

    # 平台管理员可以指定任意租户，租户管理员只能查看自己的租户
    tenant_id = None if current_admin.get("is_super_admin") else (tenant["id"] if tenant else None)

    query = PaymentProfileQuery(
        keyword=keyword,
        status=status,
        company_id=company_id,
        page=page,
        page_size=page_size
    )

    profiles, total = await service.get_list(tenant_id=tenant_id, query=query)

    result = []
    for profile in profiles:
        result.append(PaymentProfileListResponse(
            id=profile.id,
            name=profile.name,
            code=profile.code,
            mode=profile.mode,
            app_id=profile.app_id,
            is_default=profile.is_default,
            status=profile.status,
            company_name=profile.company.name if profile.company else None,
            created_at=profile.created_at,
        ))

    return PageResponse(
        data=result,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/payment-profiles", response_model=PaymentProfileResponse, summary="创建支付配置")
async def create_payment_profile(
    data: PaymentProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant: Optional[dict] = Depends(get_tenant_from_admin)
):
    """创建支付配置

    平台管理员可以为任意租户创建支付配置。
    租户管理员只能为自己租户创建支付配置。
    """
    # 非平台管理员需要关联租户
    if not current_admin.get("is_super_admin"):
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未关联租户"
            )
        tenant_id = tenant["id"]
    else:
        # 平台管理员需要从上下文获取租户ID（如果有的话）
        tenant_id = tenant["id"] if tenant else None
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="需要指定租户"
            )

    service = PaymentProfileService(db)

    try:
        profile = await service.create(data, tenant_id, operator_id=current_admin.get("id"))
        # 重新加载关联
        await db.refresh(profile, ["company"])
        return PaymentProfileResponse.model_validate(profile)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/payment-profiles/{profile_id}", response_model=PaymentProfileResponse, summary="获取支付配置详情")
async def get_payment_profile(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取支付配置详情"""
    service = PaymentProfileService(db)
    profile = await service.get_by_id(profile_id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="支付配置不存在"
        )

    # 权限检查：非平台管理员只能查看自己租户的支付配置
    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id and profile.tenant_id != admin_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权访问此支付配置"
            )

    return PaymentProfileResponse.model_validate(profile)


@router.put("/payment-profiles/{profile_id}", response_model=PaymentProfileResponse, summary="更新支付配置")
async def update_payment_profile(
    profile_id: str,
    data: PaymentProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """更新支付配置"""
    service = PaymentProfileService(db)
    profile = await service.get_by_id(profile_id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="支付配置不存在"
        )

    # 权限检查：非平台管理员只能修改自己租户的支付配置
    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id and profile.tenant_id != admin_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权修改此支付配置"
            )

    try:
        profile = await service.update(profile_id, data, operator_id=current_admin.get("id"))
        # 重新加载关联
        await db.refresh(profile, ["company"])
        return PaymentProfileResponse.model_validate(profile)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/payment-profiles/{profile_id}", summary="删除支付配置")
async def delete_payment_profile(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """删除支付配置"""
    service = PaymentProfileService(db)
    profile = await service.get_by_id(profile_id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="支付配置不存在"
        )

    # 权限检查：非平台管理员只能删除自己租户的支付配置
    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id and profile.tenant_id != admin_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权删除此支付配置"
            )

    try:
        success = await service.delete(profile_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="支付配置不存在"
            )
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/payment-profiles/{profile_id}/set-default", summary="设置为默认支付配置")
async def set_default_payment_profile(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant: Optional[dict] = Depends(get_tenant_from_admin)
):
    """设置为默认支付配置"""
    # 非平台管理员需要关联租户
    if not current_admin.get("is_super_admin"):
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未关联租户"
            )
        tenant_id = tenant["id"]
    else:
        tenant_id = tenant["id"] if tenant else None
        if not tenant_id:
            # 平台管理员需要先获取配置来确定租户
            service = PaymentProfileService(db)
            profile = await service.get_by_id(profile_id)
            if not profile:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="支付配置不存在"
                )
            tenant_id = profile.tenant_id

    service = PaymentProfileService(db)

    try:
        profile = await service.set_default(profile_id, tenant_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="支付配置不存在"
            )
        return {"message": "已设置为默认支付配置"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/payment-profiles/check-unique", summary="检查支付配置编码唯一性")
async def check_payment_profile_code_unique(
    code: str = Query(..., min_length=1, max_length=50),
    exclude_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant: Optional[dict] = Depends(get_tenant_from_admin)
):
    """检查支付配置编码是否已存在"""
    # 非平台管理员需要关联租户
    if not current_admin.get("is_super_admin"):
        tenant_id = tenant["id"] if tenant else None
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未关联租户"
            )
    else:
        tenant_id = tenant["id"] if tenant else None
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="需要指定租户"
            )

    service = PaymentProfileService(db)
    exists = await service.check_code_exists(code, tenant_id, exclude_id)
    return {"exists": exists}
