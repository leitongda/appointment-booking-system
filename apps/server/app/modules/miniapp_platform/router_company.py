"""小程序平台 - 公司管理路由 (Company CRUD)"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_current_admin, get_tenant_from_admin
from app.db.session import get_db
from app.modules.miniapp_platform.schemas import (
    CompanyCreate,
    CompanyListResponse,
    CompanyResponse,
    CompanyUpdate,
)
from app.modules.miniapp_platform.service import CompanyService
from app.schemas.response import PageResponse

router = APIRouter()


# ==================== Company (公司/结算主体) ====================

@router.get("/companies", response_model=PageResponse[CompanyListResponse], summary="获取公司列表")
async def get_companies(
    keyword: str | None = None,
    status: int | None = Query(None, ge=0, le=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant: dict | None = Depends(get_tenant_from_admin)
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
    tenant: dict | None = Depends(get_tenant_from_admin)
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
    exclude_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant: dict | None = Depends(get_tenant_from_admin)
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
