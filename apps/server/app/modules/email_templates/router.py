from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, require_permission
from app.core.config import settings
from app.db.session import get_db
from app.schemas.email_template import (
    EmailTemplateCreate,
    EmailTemplateListResponse,
    EmailTemplateQuery,
    EmailTemplateResponse,
    EmailTemplateUpdate,
    EmailTestRequest,
)
from app.infrastructure.email.service import EmailService
from app.services.email_template_service import EmailTemplateService

router = APIRouter()


@router.get("", summary="获取邮件模板列表")
async def get_email_templates(
    template_type: Optional[str] = Query(None, description="模板类型"),
    status: Optional[int] = Query(None, description="状态"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    service = EmailTemplateService(db)
    query = EmailTemplateQuery(
        template_type=template_type,
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    templates, total = await service.get_list(query)
    return {
        "data": [EmailTemplateListResponse.model_validate(t) for t in templates],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/all", summary="获取所有邮件模板")
async def get_all_email_templates(
    status: Optional[int] = Query(None, description="状态"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    service = EmailTemplateService(db)
    templates = await service.get_all(status)
    return [EmailTemplateListResponse.model_validate(t) for t in templates]


@router.get("/{template_id}", summary="获取邮件模板详情")
async def get_email_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    service = EmailTemplateService(db)
    template = await service.get_by_id(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="邮件模板不存在，请检查后重试")
    return EmailTemplateResponse.model_validate(template)


@router.post("", summary="创建邮件模板")
async def create_email_template(
    data: EmailTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("system:settings")),
):
    service = EmailTemplateService(db)
    try:
        template = await service.create(data)
        return EmailTemplateResponse.model_validate(template)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{template_id}", summary="更新邮件模板")
async def update_email_template(
    template_id: str,
    data: EmailTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("system:settings")),
):
    service = EmailTemplateService(db)
    template = await service.update(template_id, data)
    if not template:
        raise HTTPException(status_code=404, detail="邮件模板不存在，请检查后重试")
    return EmailTemplateResponse.model_validate(template)


@router.delete("/{template_id}", summary="删除邮件模板")
async def delete_email_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("system:settings")),
):
    service = EmailTemplateService(db)
    success = await service.delete(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="邮件模板不存在，请检查后重试")
    return {"message": "删除成功"}


@router.post("/{template_id}/test", summary="发送测试邮件")
async def send_test_email(
    template_id: str,
    data: EmailTestRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    email_service = EmailService(db)
    try:
        await email_service.send_test_email(
            template_id=template_id,
            to_email=data.to_email,
            variables=data.variables,
        )
        return {"message": "测试邮件发送成功"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
