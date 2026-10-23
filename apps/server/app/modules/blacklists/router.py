"""黑名单管理 API"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_admin,
    require_admin_tenant_anchor,
    require_permission,
)
from app.core.config import settings
from app.db.session import get_db
from app.modules.blacklists.service import BlacklistService
from app.schemas.blacklist import BlacklistCreate

router = APIRouter()


def _require_anchor(tenant_anchor: str | None) -> str:
    """R1-14：黑名单写路径必须拿到账号锚点，禁止写出 tenant_id=NULL 的记录。"""
    if not tenant_anchor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法确定租户ID，请指定 tenant_id 后重试",
        )
    return tenant_anchor


@router.get("", summary="获取列表")
async def get_blacklist_list(
    keyword: str | None = Query(None, description="搜索关键词"),
    store_id: str | None = Query(None, description="门店ID"),
    status: int | None = Query(None, description="状态: 1生效 0已解禁"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("blacklist:list")),
):
    """获取黑名单列表"""
    service = BlacklistService(db, tenant_id=tenant_anchor)
    items, total = await service.get_list(
        keyword=keyword,
        store_id=store_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    return {
        "data": items,
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


@router.post("", summary="添加黑名单")
async def add_blacklist(
    data: BlacklistCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("blacklist:create")),
):
    """添加黑名单"""
    # 验证：必须有用户ID或关键词
    if not data.user_id and not data.keyword:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请选择用户或填写手机号/身份证关键词"
        )

    service = BlacklistService(db, tenant_id=_require_anchor(tenant_anchor))
    try:
        result = await service.create(data, operator_id=current_admin.get("id"))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return {"message": "添加成功", "data": result}


@router.delete("/{blacklist_id}", summary="移除黑名单")
async def remove_blacklist(
    blacklist_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("blacklist:delete")),
):
    """移除黑名单（解禁）"""
    service = BlacklistService(db, tenant_id=_require_anchor(tenant_anchor))
    success = await service.remove(blacklist_id, operator_id=current_admin.get("id"))
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="黑名单记录不存在，请检查后重试"
        )
    
    return {"message": "解禁成功"}


@router.post("/check", summary="检查黑名单")
async def check_blacklist(
    user_id: str | None = None,
    phone: str | None = None,
    id_card: str | None = None,
    store_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """检查是否在黑名单中（公开接口，用于预约时检查）"""
    service = BlacklistService(db)
    result = await service.check_blacklist(
        user_id=user_id,
        phone=phone,
        id_card=id_card,
        store_id=store_id,
    )
    return result.model_dump()
