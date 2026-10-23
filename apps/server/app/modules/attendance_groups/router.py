"""
签到组管理 API

提供签到组的 CRUD 及成员管理接口
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, require_admin_tenant_anchor
from app.core.config import settings
from app.db.session import get_db
from app.modules.attendance_groups.schemas import (
    AttendanceGroupCreate,
    AttendanceGroupResponse,
    AttendanceGroupUpdate,
    GroupMemberAdd,
    GroupMemberResponse,
)
from app.modules.attendance_groups.service import AttendanceGroupService
from app.schemas.rule_set import PageResult

router = APIRouter()


def _require_anchor(tenant_anchor: str | None) -> str:
    """R1-11：考勤写路径必须拿到账号锚点，禁止写出 tenant_id=NULL 的记录。"""
    if not tenant_anchor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法确定租户ID，请指定 tenant_id 后重试",
        )
    return tenant_anchor


@router.get("", response_model=PageResult[AttendanceGroupResponse], summary="获取签到组列表")
async def get_groups(
    keyword: str | None = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """获取签到组列表"""
    service = AttendanceGroupService(db, tenant_id=tenant_anchor)
    items, total = await service.get_list(
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return PageResult(data=items, total=total)


@router.get("/{group_id}", response_model=AttendanceGroupResponse, summary="获取签到组详情")
async def get_group(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """获取签到组详情"""
    service = AttendanceGroupService(db, tenant_id=tenant_anchor)
    group = await service.get_by_id(group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="签到组不存在",
        )
    return AttendanceGroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        check_method=group.check_method,
        location_lat=group.location_lat,
        location_lng=group.location_lng,
        location_radius=group.location_radius,
        wifi_ssid=group.wifi_ssid,
        wifi_ssids=group.wifi_ssids,
        device_whitelist=group.device_whitelist,
        require_device_bind=group.require_device_bind,
        enabled=group.enabled,
        created_at=group.created_at.isoformat() if group.created_at else None,
    )


@router.post("", response_model=AttendanceGroupResponse, status_code=status.HTTP_201_CREATED, summary="创建签到组")
async def create_group(
    data: AttendanceGroupCreate,
    db: AsyncSession = Depends(get_db),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    current_admin: dict = Depends(get_current_admin),
):
    """创建签到组"""
    service = AttendanceGroupService(db, tenant_id=_require_anchor(tenant_anchor))
    group = await service.create(
        data=data.model_dump(),
        operator_id=current_admin.get("id"),
    )
    return AttendanceGroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        check_method=group.check_method,
        location_lat=group.location_lat,
        location_lng=group.location_lng,
        location_radius=group.location_radius,
        wifi_ssid=group.wifi_ssid,
        wifi_ssids=group.wifi_ssids,
        device_whitelist=group.device_whitelist,
        require_device_bind=group.require_device_bind,
        enabled=group.enabled,
        created_at=group.created_at.isoformat() if group.created_at else None,
    )


@router.put("/{group_id}", response_model=AttendanceGroupResponse, summary="更新签到组")
async def update_group(
    group_id: str,
    data: AttendanceGroupUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    current_admin: dict = Depends(get_current_admin),
):
    """更新签到组"""
    service = AttendanceGroupService(db, tenant_id=_require_anchor(tenant_anchor))
    group = await service.update(
        group_id=group_id,
        data=data.model_dump(exclude_unset=True),
        operator_id=current_admin.get("id"),
    )
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="签到组不存在",
        )
    return AttendanceGroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        check_method=group.check_method,
        location_lat=group.location_lat,
        location_lng=group.location_lng,
        location_radius=group.location_radius,
        wifi_ssid=group.wifi_ssid,
        wifi_ssids=group.wifi_ssids,
        device_whitelist=group.device_whitelist,
        require_device_bind=group.require_device_bind,
        enabled=group.enabled,
        created_at=group.created_at.isoformat() if group.created_at else None,
    )


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除签到组")
async def delete_group(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    current_admin: dict = Depends(get_current_admin),
):
    """删除签到组"""
    service = AttendanceGroupService(db, tenant_id=_require_anchor(tenant_anchor))
    success = await service.delete(group_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="签到组不存在",
        )
    return None


@router.post("/{group_id}/members", summary="批量添加成员")
async def add_members(
    group_id: str,
    data: GroupMemberAdd,
    db: AsyncSession = Depends(get_db),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    current_admin: dict = Depends(get_current_admin),
):
    """批量添加签到组成员"""
    service = AttendanceGroupService(db, tenant_id=_require_anchor(tenant_anchor))
    group = await service.get_by_id(group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="签到组不存在",
        )
    added = await service.add_members(group_id, data.account_ids)
    return {"added": added}


@router.delete(
    "/{group_id}/members/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="移除成员",
)
async def remove_member(
    group_id: str,
    account_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    current_admin: dict = Depends(get_current_admin),
):
    """移除签到组成员"""
    service = AttendanceGroupService(db, tenant_id=_require_anchor(tenant_anchor))
    success = await service.remove_member(group_id, account_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="成员不存在",
        )
    return None


@router.get(
    "/{group_id}/members",
    response_model=PageResult[GroupMemberResponse],
    summary="获取成员列表",
)
async def get_members(
    group_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """获取签到组成员列表（分页）"""
    service = AttendanceGroupService(db, tenant_id=tenant_anchor)
    group = await service.get_by_id(group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="签到组不存在",
        )
    members, total = await service.get_members(
        group_id=group_id,
        page=page,
        page_size=page_size,
    )
    return PageResult(data=members, total=total)
