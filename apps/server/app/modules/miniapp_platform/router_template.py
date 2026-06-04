"""小程序平台 - 模板管理路由 (AppTemplate + TemplateVersion)"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.common.deps import get_current_admin
from app.schemas.miniapp_template import (
    AppTemplateCreate, AppTemplateUpdate, AppTemplateResponse, AppTemplateListResponse,
    TemplateVersionCreate, TemplateVersionResponse,
)
from app.modules.miniapp_platform.service_instance import AppTemplateService
from app.schemas.response import PageResponse

router = APIRouter()


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


# ==================== TemplateVersion (模板版本) ====================

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
