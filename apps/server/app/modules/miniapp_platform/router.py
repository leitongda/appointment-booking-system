"""小程序平台管理路由"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.db.session import get_db
from app.common.deps import (
    get_current_admin, require_permission, get_platform_admin,
    require_platform_admin, get_tenant_from_admin
)
from app.modules.miniapp_platform.schemas import (
    CompanyCreate, CompanyUpdate, CompanyResponse, CompanyListResponse,
    PaymentProfileCreate, PaymentProfileUpdate, PaymentProfileResponse, PaymentProfileListResponse, PaymentProfileQuery,
    MiniappInstanceCreate, MiniappInstanceUpdate, MiniappInstanceResponse, MiniappInstanceListResponse, MiniappInstanceQuery,
)
from app.schemas.miniapp_template import (
    AppTemplateCreate, AppTemplateUpdate, AppTemplateResponse, AppTemplateListResponse,
    TemplateVersionCreate, TemplateVersionResponse,
    BuildJobCreate, BuildJobResponse, BuildJobListResponse,
    ReleaseJobCreate, ReleaseJobResponse, ReleaseJobListResponse,
)
from app.modules.miniapp_platform.service import (
    CompanyService, PaymentProfileService, MiniappInstanceService,
    AppTemplateService, BuildJobService, ReleaseJobService
)
from app.schemas.response import PageResponse

router = APIRouter()


# ==================== Company (公司/结算主体) ====================

@router.get("/companies", response_model=PageResponse[CompanyListResponse], summary="获取公司列表")
async def get_companies(
    keyword: Optional[str] = None,
    status: Optional[int] = Query(None, ge=0, le=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant: Optional[dict] = Depends(get_tenant_from_admin)
):
    """获取公司列表

    平台管理员可以查看所有租户的公司。
    租户管理员只能查看自己租户的公司。
    """
    service = CompanyService(db)

    # 平台管理员可以指定任意租户，租户管理员只能查看自己的租户
    tenant_id = None if current_admin.get("is_super_admin") else (tenant["id"] if tenant else None)

    companies, total = await service.get_list(
        tenant_id=tenant_id,
        keyword=keyword,
        status=status,
        page=page,
        page_size=page_size
    )

    result = [CompanyListResponse.model_validate(c) for c in companies]

    return PageResponse(
        data=result,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/companies", response_model=CompanyResponse, summary="创建公司")
async def create_company(
    data: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant: Optional[dict] = Depends(get_tenant_from_admin)
):
    """创建公司

    平台管理员可以为任意租户创建公司。
    租户管理员只能为自己租户创建公司。
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

    service = CompanyService(db)

    try:
        company = await service.create(data, tenant_id, operator_id=current_admin.get("id"))
        return CompanyResponse.model_validate(company)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/companies/{company_id}", response_model=CompanyResponse, summary="获取公司详情")
async def get_company(
    company_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取公司详情"""
    service = CompanyService(db)
    company = await service.get_by_id(company_id)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="公司不存在"
        )

    # 权限检查：非平台管理员只能查看自己租户的公司
    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id and company.tenant_id != admin_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权访问此公司"
            )

    return CompanyResponse.model_validate(company)


@router.put("/companies/{company_id}", response_model=CompanyResponse, summary="更新公司")
async def update_company(
    company_id: str,
    data: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """更新公司"""
    service = CompanyService(db)
    company = await service.get_by_id(company_id)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="公司不存在"
        )

    # 权限检查：非平台管理员只能修改自己租户的公司
    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id and company.tenant_id != admin_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权修改此公司"
            )

    try:
        company = await service.update(company_id, data, operator_id=current_admin.get("id"))
        return CompanyResponse.model_validate(company)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/companies/{company_id}", summary="删除公司")
async def delete_company(
    company_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """删除公司"""
    service = CompanyService(db)
    company = await service.get_by_id(company_id)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="公司不存在"
        )

    # 权限检查：非平台管理员只能删除自己租户的公司
    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id and company.tenant_id != admin_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权删除此公司"
            )

    try:
        success = await service.delete(company_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="公司不存在"
            )
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/companies/check-unique", summary="检查公司编码唯一性")
async def check_company_code_unique(
    code: str = Query(..., min_length=1, max_length=50),
    exclude_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant: Optional[dict] = Depends(get_tenant_from_admin)
):
    """检查公司编码是否已存在"""
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

    service = CompanyService(db)
    exists = await service.check_code_exists(code, tenant_id, exclude_id)
    return {"exists": exists}


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


# ==================== MiniappInstance (小程序实例) ====================

@router.get("/instances", response_model=PageResponse[MiniappInstanceListResponse], summary="获取小程序实例列表")
async def get_miniapp_instances(
    keyword: Optional[str] = None,
    status: Optional[int] = Query(None, ge=0, le=2),
    template_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant: Optional[dict] = Depends(get_tenant_from_admin)
):
    """获取小程序实例列表

    平台管理员可以查看所有租户的实例。
    租户管理员只能查看自己租户的实例。
    """
    service = MiniappInstanceService(db)

    # 平台管理员可以指定任意租户，租户管理员只能查看自己的租户
    tenant_id = None if current_admin.get("is_super_admin") else (tenant["id"] if tenant else None)

    query = MiniappInstanceQuery(
        keyword=keyword,
        status=status,
        template_id=template_id,
        page=page,
        page_size=page_size
    )

    instances, total = await service.get_list(tenant_id=tenant_id, query=query)

    result = []
    for instance in instances:
        result.append(MiniappInstanceListResponse(
            id=instance.id,
            code=instance.code,
            name=instance.name,
            app_id=instance.app_id,
            status=instance.status,
            template_name=instance.template.name if instance.template else None,
            template_version=instance.template_version.version if instance.template_version else None,
            store_name=instance.default_store.name if instance.default_store else None,
            payment_profile_name=instance.default_payment_profile.name if instance.default_payment_profile else None,
            created_at=instance.created_at,
        ))

    return PageResponse(
        data=result,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/instances", response_model=MiniappInstanceResponse, summary="创建小程序实例")
async def create_miniapp_instance(
    data: MiniappInstanceCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant: Optional[dict] = Depends(get_tenant_from_admin)
):
    """创建小程序实例

    平台管理员可以为任意租户创建实例。
    租户管理员只能为自己租户创建实例。
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

    service = MiniappInstanceService(db)

    try:
        instance = await service.create(data, tenant_id, operator_id=current_admin.get("id"))
        # 重新加载关联
        instance = await service.get_by_id(instance.id)
        return MiniappInstanceResponse.model_validate(instance)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/instances/{instance_id}", response_model=MiniappInstanceResponse, summary="获取小程序实例详情")
async def get_miniapp_instance(
    instance_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取小程序实例详情"""
    service = MiniappInstanceService(db)
    instance = await service.get_by_id(instance_id)

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="小程序实例不存在"
        )

    # 权限检查：非平台管理员只能查看自己租户的实例
    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id and instance.tenant_id != admin_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权访问此实例"
            )

    return MiniappInstanceResponse.model_validate(instance)


@router.put("/instances/{instance_id}", response_model=MiniappInstanceResponse, summary="更新小程序实例")
async def update_miniapp_instance(
    instance_id: str,
    data: MiniappInstanceUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """更新小程序实例"""
    service = MiniappInstanceService(db)
    instance = await service.get_by_id(instance_id)

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="小程序实例不存在"
        )

    # 权限检查：非平台管理员只能修改自己租户的实例
    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id and instance.tenant_id != admin_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权修改此实例"
            )

    try:
        instance = await service.update(instance_id, data, operator_id=current_admin.get("id"))
        # 重新加载关联
        instance = await service.get_by_id(instance.id)
        return MiniappInstanceResponse.model_validate(instance)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/instances/{instance_id}", summary="删除小程序实例")
async def delete_miniapp_instance(
    instance_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """删除小程序实例（归档）"""
    service = MiniappInstanceService(db)
    instance = await service.get_by_id(instance_id)

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="小程序实例不存在"
        )

    # 权限检查：非平台管理员只能删除自己租户的实例
    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id and instance.tenant_id != admin_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权删除此实例"
            )

    try:
        success = await service.delete(instance_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="小程序实例不存在"
            )
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/instances/{instance_id}/activate", summary="激活小程序实例")
async def activate_miniapp_instance(
    instance_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """激活小程序实例"""
    service = MiniappInstanceService(db)

    # 权限检查
    instance = await service.get_by_id(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="小程序实例不存在"
        )

    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id and instance.tenant_id != admin_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权操作此实例"
            )

    instance = await service.update_status(instance_id, 1)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="小程序实例不存在"
        )

    return {"message": "实例已激活"}


@router.post("/instances/{instance_id}/archive", summary="归档小程序实例")
async def archive_miniapp_instance(
    instance_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """归档小程序实例"""
    service = MiniappInstanceService(db)

    # 权限检查
    instance = await service.get_by_id(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="小程序实例不存在"
        )

    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id and instance.tenant_id != admin_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权操作此实例"
            )

    instance = await service.update_status(instance_id, 2)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="小程序实例不存在"
        )

    return {"message": "实例已归档"}


@router.get("/instances/check-unique", summary="检查实例编码唯一性")
async def check_instance_code_unique(
    code: str = Query(None, min_length=1, max_length=50),
    app_id: str = Query(None, min_length=1, max_length=100),
    exclude_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant: Optional[dict] = Depends(get_tenant_from_admin)
):
    """检查实例编码或AppID是否已存在"""
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

    service = MiniappInstanceService(db)
    result = {}

    if code:
        result["code_exists"] = await service.check_code_exists(code, tenant_id, exclude_id)

    if app_id:
        result["app_id_exists"] = await service.check_app_id_exists(app_id, tenant_id, exclude_id)

    return result


# ==================== AppTemplate (小程序模板) ====================

@router.get("/templates", response_model=PageResponse[AppTemplateListResponse], summary="获取模板列表")
async def get_templates(
    category: Optional[str] = Query(None, description="模板分类"),
    status: Optional[int] = Query(None, ge=0, le=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取模板列表

    所有管理员都可以查看模板列表。
    """
    service = AppTemplateService(db)

    templates, total = await service.get_list(
        category=category,
        status=status,
        skip=(page - 1) * page_size,
        limit=page_size
    )

    result = [AppTemplateListResponse.model_validate(t) for t in templates]

    return PageResponse(
        data=result,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/templates/{template_id}", response_model=AppTemplateResponse, summary="获取模板详情")
async def get_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取模板详情"""
    service = AppTemplateService(db)
    template = await service.get_by_id(template_id)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在"
        )

    return AppTemplateResponse.model_validate(template)


@router.post("/templates", response_model=AppTemplateResponse, summary="创建模板")
async def create_template(
    data: AppTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """创建模板

    仅平台管理员可以创建模板。
    """
    if not current_admin.get("is_super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅平台管理员可以创建模板"
        )

    service = AppTemplateService(db)

    try:
        template = await service.create(
            name=data.name,
            code=data.code,
            description=data.description,
            category=data.category,
            default_config=data.default_config,
            operator_id=current_admin.get("id")
        )
        return AppTemplateResponse.model_validate(template)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/templates/{template_id}", response_model=AppTemplateResponse, summary="更新模板")
async def update_template(
    template_id: str,
    data: AppTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """更新模板

    仅平台管理员可以更新模板。
    """
    if not current_admin.get("is_super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅平台管理员可以更新模板"
        )

    service = AppTemplateService(db)

    try:
        template = await service.update(
            template_id=template_id,
            name=data.name,
            description=data.description,
            default_config=data.default_config,
            status=data.status,
            operator_id=current_admin.get("id")
        )
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模板不存在"
            )
        return AppTemplateResponse.model_validate(template)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/templates/{template_id}/versions", response_model=PageResponse[TemplateVersionResponse], summary="获取模板版本列表")
async def get_template_versions(
    template_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取模板版本列表"""
    service = AppTemplateService(db)

    # 先验证模板是否存在
    template = await service.get_by_id(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在"
        )

    versions, total = await service.get_versions(
        template_id=template_id,
        skip=(page - 1) * page_size,
        limit=page_size
    )

    result = [TemplateVersionResponse.model_validate(v) for v in versions]

    return PageResponse(
        data=result,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/templates/{template_id}/versions", response_model=TemplateVersionResponse, summary="创建模板版本")
async def create_template_version(
    template_id: str,
    data: TemplateVersionCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """创建模板版本

    仅平台管理员可以创建模板版本。
    """
    if not current_admin.get("is_super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅平台管理员可以创建模板版本"
        )

    service = AppTemplateService(db)

    # 先验证模板是否存在
    template = await service.get_by_id(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在"
        )

    try:
        version = await service.create_version(
            template_id=template_id,
            version=data.version,
            source_ref=data.source_ref,
            schema_version=data.schema_version,
            changelog=data.changelog,
            operator_id=current_admin.get("id")
        )
        return TemplateVersionResponse.model_validate(version)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ==================== BuildJob (构建任务) ====================

@router.get("/build-jobs", response_model=PageResponse[BuildJobListResponse], summary="获取构建任务列表")
async def get_build_jobs(
    instance_id: Optional[str] = Query(None, description="小程序实例ID"),
    status: Optional[str] = Query(None, description="任务状态"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant: Optional[dict] = Depends(get_tenant_from_admin)
):
    """获取构建任务列表

    平台管理员可以查看所有租户的构建任务。
    租户管理员只能查看自己租户的构建任务。
    """
    tenant_id = None if current_admin.get("is_super_admin") else (tenant["id"] if tenant else None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未关联租户"
        )

    service = BuildJobService(db)

    jobs, total = await service.get_list(
        tenant_id=tenant_id,
        instance_id=instance_id,
        status=status,
        skip=(page - 1) * page_size,
        limit=page_size
    )

    result = []
    for job in jobs:
        result.append(BuildJobListResponse(
            id=job.id,
            miniapp_instance_id=job.miniapp_instance_id,
            miniapp_instance_name=job.miniapp_instance.name if job.miniapp_instance else None,
            template_version=job.template_version.version if job.template_version else None,
            trigger_source=job.trigger_source,
            status=job.status,
            started_at=job.started_at,
            finished_at=job.finished_at,
            created_at=job.created_at,
        ))

    return PageResponse(
        data=result,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/build-jobs/{job_id}", response_model=BuildJobResponse, summary="获取构建任务详情")
async def get_build_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取构建任务详情"""
    service = BuildJobService(db)
    job = await service.get_by_id(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="构建任务不存在"
        )

    # 权限检查：非平台管理员只能查看自己租户的任务
    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id and job.tenant_id != admin_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权访问此构建任务"
            )

    return BuildJobResponse.model_validate(job)


@router.post("/build-jobs", response_model=BuildJobResponse, summary="创建构建任务")
async def create_build_job(
    data: BuildJobCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant: Optional[dict] = Depends(get_tenant_from_admin)
):
    """创建构建任务

    租户管理员可以为自己租户的实例创建构建任务。
    """
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="需要指定租户"
            )

    service = BuildJobService(db)

    try:
        job = await service.create(
            tenant_id=tenant_id,
            data=data,
            operator_id=current_admin.get("id")
        )
        return BuildJobResponse.model_validate(job)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ==================== ReleaseJob (发布任务) ====================

@router.get("/release-jobs", response_model=PageResponse[ReleaseJobListResponse], summary="获取发布任务列表")
async def get_release_jobs(
    instance_id: Optional[str] = Query(None, description="小程序实例ID"),
    action: Optional[str] = Query(None, description="动作类型"),
    status: Optional[str] = Query(None, description="任务状态"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant: Optional[dict] = Depends(get_tenant_from_admin)
):
    """获取发布任务列表

    平台管理员可以查看所有租户的发布任务。
    租户管理员只能查看自己租户的发布任务。
    """
    # 由于 ReleaseJob 模型没有 tenant_id 字段，我们需要通过 miniapp_instance 来过滤
    # 这里暂时返回所有任务，在服务层进行过滤
    service = ReleaseJobService(db)

    # 获取当前租户
    if not current_admin.get("is_super_admin"):
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未关联租户"
            )
        tenant_id = tenant["id"]
    else:
        # 平台管理员查看所有
        jobs, total = await service.get_list(
            tenant_id=None,  # 不需要租户过滤
            instance_id=instance_id,
            action=action,
            status=status,
            skip=(page - 1) * page_size,
            limit=page_size
        )

        result = []
        for job in jobs:
            result.append(ReleaseJobListResponse(
                id=job.id,
                miniapp_instance_id=job.miniapp_instance_id,
                miniapp_instance_name=job.miniapp_instance.name if job.miniapp_instance else None,
                action=job.action,
                target_version=job.target_version,
                status=job.status,
                result=job.result,
                created_at=job.created_at,
            ))

        return PageResponse(
            data=result,
            total=total,
            page=page,
            page_size=page_size
        )

    # 对于租户管理员，需要在获取结果后进行过滤
    jobs, total = await service.get_list(
        tenant_id=None,
        instance_id=instance_id,
        action=action,
        status=status,
        skip=0,  # 先获取所有，然后过滤
        limit=1000
    )

    # 过滤出属于当前租户的任务
    filtered_jobs = []
    for job in jobs:
        if job.miniapp_instance and hasattr(job.miniapp_instance, 'tenant_id'):
            if job.miniapp_instance.tenant_id == tenant_id:
                filtered_jobs.append(job)

    # 手动分页
    filtered_total = len(filtered_jobs)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_jobs = filtered_jobs[start:end]

    result = []
    for job in paginated_jobs:
        result.append(ReleaseJobListResponse(
            id=job.id,
            miniapp_instance_id=job.miniapp_instance_id,
            miniapp_instance_name=job.miniapp_instance.name if job.miniapp_instance else None,
            action=job.action,
            target_version=job.target_version,
            status=job.status,
            result=job.result,
            created_at=job.created_at,
        ))

    return PageResponse(
        data=result,
        total=filtered_total,
        page=page,
        page_size=page_size
    )


@router.get("/release-jobs/{job_id}", response_model=ReleaseJobResponse, summary="获取发布任务详情")
async def get_release_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取发布任务详情"""
    service = ReleaseJobService(db)
    job = await service.get_by_id(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="发布任务不存在"
        )

    # 权限检查：非平台管理员只能查看自己租户的任务
    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id and job.miniapp_instance and hasattr(job.miniapp_instance, 'tenant_id'):
            if job.miniapp_instance.tenant_id != admin_tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="您无权访问此发布任务"
                )

    return ReleaseJobResponse.model_validate(job)


@router.post("/release-jobs", response_model=ReleaseJobResponse, summary="创建发布任务")
async def create_release_job(
    data: ReleaseJobCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant: Optional[dict] = Depends(get_tenant_from_admin)
):
    """创建发布任务

    租户管理员可以为自己租户的实例创建发布任务。
    """
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="需要指定租户"
            )

    service = ReleaseJobService(db)

    try:
        job = await service.create(
            tenant_id=tenant_id,
            data=data,
            operator_id=current_admin.get("id")
        )
        return ReleaseJobResponse.model_validate(job)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
