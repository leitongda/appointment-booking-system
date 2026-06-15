"""平台公告 API（仅平台管理员可访问）"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_current_admin, require_platform_admin
from app.db.session import get_db
from app.modules.platform_announcements.service import PlatformAnnouncementService
from app.schemas.platform_announcement import (
    PlatformAnnouncementCreate,
    PlatformAnnouncementListResponse,
    PlatformAnnouncementResponse,
    PlatformAnnouncementUpdate,
)

router = APIRouter()


@router.post("", response_model=PlatformAnnouncementResponse, status_code=status.HTTP_201_CREATED, summary="创建平台公告")
async def create_announcement(
    data: PlatformAnnouncementCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_platform_admin),
):
    """创建平台公告（草稿状态）"""
    service = PlatformAnnouncementService(db)
    announcement = await service.create(
        data=data,
        publisher_id=current_admin.get("id"),
        publisher_name=current_admin.get("name") or current_admin.get("username"),
    )
    return PlatformAnnouncementResponse.model_validate(announcement)


@router.get("", response_model=PlatformAnnouncementListResponse, summary="获取平台公告列表")
async def get_announcements(
    status: str | None = Query(None, pattern="^(draft|published|revoked)$", description="状态筛选"),
    keyword: str | None = Query(None, description="关键词搜索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_platform_admin),
):
    """获取平台公告列表（平台管理员）"""
    service = PlatformAnnouncementService(db)
    items, total = await service.get_list(
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return PlatformAnnouncementListResponse(
        data=[PlatformAnnouncementResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{announcement_id}", response_model=PlatformAnnouncementResponse, summary="获取公告详情")
async def get_announcement(
    announcement_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_platform_admin),
):
    """获取平台公告详情"""
    service = PlatformAnnouncementService(db)
    announcement = await service.get_by_id(announcement_id)
    if not announcement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="公告不存在")
    return PlatformAnnouncementResponse.model_validate(announcement)


@router.put("/{announcement_id}", response_model=PlatformAnnouncementResponse, summary="更新公告")
async def update_announcement(
    announcement_id: str,
    data: PlatformAnnouncementUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_platform_admin),
):
    """更新平台公告（仅草稿状态可修改）"""
    service = PlatformAnnouncementService(db)
    try:
        announcement = await service.update(announcement_id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    if not announcement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="公告不存在")
    return PlatformAnnouncementResponse.model_validate(announcement)


@router.post("/{announcement_id}/publish", response_model=PlatformAnnouncementResponse, summary="发布公告")
async def publish_announcement(
    announcement_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_platform_admin),
):
    """发布平台公告：向目标租户推送通知"""
    service = PlatformAnnouncementService(db)
    try:
        announcement = await service.publish(announcement_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    if not announcement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="公告不存在")
    return PlatformAnnouncementResponse.model_validate(announcement)


@router.post("/{announcement_id}/revoke", response_model=PlatformAnnouncementResponse, summary="撤回公告")
async def revoke_announcement(
    announcement_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_platform_admin),
):
    """撤回已发布的平台公告"""
    service = PlatformAnnouncementService(db)
    try:
        announcement = await service.revoke(announcement_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    if not announcement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="公告不存在")
    return PlatformAnnouncementResponse.model_validate(announcement)


@router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除公告")
async def delete_announcement(
    announcement_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_platform_admin),
):
    """删除平台公告"""
    service = PlatformAnnouncementService(db)
    success = await service.delete(announcement_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="公告不存在")
