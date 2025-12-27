"""黑名单管理 API"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.services.blacklist_service import BlacklistService
from app.schemas.blacklist import BlacklistCreate

router = APIRouter()


@router.get("")
async def get_blacklist_list(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    store_id: Optional[str] = Query(None, description="门店ID"),
    status: Optional[int] = Query(None, description="状态: 1生效 0已解禁"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取黑名单列表"""
    service = BlacklistService(db)
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


@router.post("")
async def add_blacklist(
    data: BlacklistCreate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """添加黑名单"""
    # 验证：必须有用户ID或关键词
    if not data.user_id and not data.keyword:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请选择用户或填写手机号/身份证关键词"
        )
    
    service = BlacklistService(db)
    result = await service.create(data)
    return {"message": "添加成功", "data": result}


@router.delete("/{blacklist_id}")
async def remove_blacklist(
    blacklist_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """移除黑名单（解禁）"""
    service = BlacklistService(db)
    success = await service.remove(blacklist_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="黑名单记录不存在，请检查后重试"
        )
    
    return {"message": "解禁成功"}


@router.post("/check")
async def check_blacklist(
    user_id: Optional[str] = None,
    phone: Optional[str] = None,
    id_card: Optional[str] = None,
    store_id: Optional[str] = None,
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
