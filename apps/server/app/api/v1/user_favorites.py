"""用户收藏 API"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.api.deps import get_current_user
from app.services.user_favorite_service import UserFavoriteService
from app.schemas.user_favorite import (
    UserFavoriteCreate,
    UserFavoriteResponse,
    FavoriteCheckResponse,
)
from app.core.config import settings

router = APIRouter()


@router.get("", summary="获取收藏列表")
async def get_favorites(
    target_type: Optional[str] = Query(None, alias="targetType", pattern="^(doctor|department)$", description="收藏类型"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=settings.MAX_PAGE_SIZE, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取当前用户收藏列表"""
    service = UserFavoriteService(db)
    favorites, total = await service.get_list(
        user_id=current_user["id"],
        target_type=target_type,
        page=page,
        page_size=page_size
    )
    
    return {
        "data": favorites,
        "total": total,
        "page": page,
        "pageSize": page_size
    }


@router.get("/check", response_model=FavoriteCheckResponse, summary="检查是否已收藏")
async def check_favorite(
    target_type: str = Query(..., alias="targetType", pattern="^(doctor|department)$"),
    target_id: str = Query(..., alias="targetId"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """检查是否已收藏"""
    service = UserFavoriteService(db)
    is_favorited, favorite_id = await service.check_favorite(
        user_id=current_user["id"],
        target_type=target_type,
        target_id=target_id
    )
    
    return FavoriteCheckResponse(
        is_favorited=is_favorited,
        favorite_id=favorite_id
    )


@router.post("", response_model=UserFavoriteResponse, status_code=status.HTTP_201_CREATED, summary="添加收藏")
async def create_favorite(
    data: UserFavoriteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """添加收藏"""
    service = UserFavoriteService(db)
    try:
        favorite = await service.create(user_id=current_user["id"], data=data)
        return favorite
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT, summary="取消收藏")
async def delete_favorite(
    favorite_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """取消收藏（通过收藏ID）"""
    service = UserFavoriteService(db)
    success = await service.delete(favorite_id=favorite_id, user_id=current_user["id"])
    
    if not success:
        raise HTTPException(status_code=404, detail="收藏不存在或无权操作")


@router.delete("/target/{target_type}/{target_id}", status_code=status.HTTP_204_NO_CONTENT, summary="取消收藏")
async def delete_favorite_by_target(
    target_type: str,
    target_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """取消收藏（通过目标类型和ID）"""
    if target_type not in ["doctor", "department"]:
        raise HTTPException(status_code=400, detail="无效的收藏类型")
    
    service = UserFavoriteService(db)
    success = await service.delete_by_target(
        user_id=current_user["id"],
        target_type=target_type,
        target_id=target_id
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="收藏不存在")

