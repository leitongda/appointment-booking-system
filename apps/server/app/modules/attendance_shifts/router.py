"""
考勤班次管理 API

提供考勤班次的 CRUD 接口
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, require_admin_tenant_anchor
from app.core.config import settings
from app.db.session import get_db
from app.modules.attendance_shifts.schemas import (
    AttendanceShiftCreate,
    AttendanceShiftResponse,
    AttendanceShiftUpdate,
)
from app.modules.attendance_shifts.service import AttendanceShiftService
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


@router.get("", response_model=PageResult[AttendanceShiftResponse], summary="获取考勤班次列表")
async def get_attendance_shifts(
    enabled: bool | None = Query(None, description="是否启用"),
    keyword: str | None = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """获取考勤班次列表"""
    service = AttendanceShiftService(db, tenant_id=tenant_anchor)
    items, total = await service.get_list(
        enabled=enabled,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return PageResult(data=items, total=total)


@router.get("/all", response_model=list[AttendanceShiftResponse], summary="获取所有启用班次")
async def get_all_attendance_shifts(
    db: AsyncSession = Depends(get_db),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """获取所有启用的考勤班次（用于下拉选择）"""
    service = AttendanceShiftService(db, tenant_id=tenant_anchor)
    return await service.get_all_enabled()


@router.get("/{shift_id}", response_model=AttendanceShiftResponse, summary="获取考勤班次详情")
async def get_attendance_shift(
    shift_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """获取考勤班次详情"""
    service = AttendanceShiftService(db, tenant_id=tenant_anchor)
    shift = await service.get_by_id(shift_id)
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="考勤班次不存在",
        )
    return shift


@router.post("", response_model=AttendanceShiftResponse, status_code=status.HTTP_201_CREATED, summary="创建考勤班次")
async def create_attendance_shift(
    data: AttendanceShiftCreate,
    db: AsyncSession = Depends(get_db),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    current_admin: dict = Depends(get_current_admin),
):
    """创建考勤班次"""
    service = AttendanceShiftService(db, tenant_id=_require_anchor(tenant_anchor))
    try:
        shift = await service.create(
            data=data.model_dump(),
            operator_id=current_admin["id"],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return shift


@router.put("/{shift_id}", response_model=AttendanceShiftResponse, summary="更新考勤班次")
async def update_attendance_shift(
    shift_id: str,
    data: AttendanceShiftUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    current_admin: dict = Depends(get_current_admin),
):
    """更新考勤班次"""
    service = AttendanceShiftService(db, tenant_id=_require_anchor(tenant_anchor))
    shift = await service.update(
        shift_id=shift_id,
        data=data.model_dump(exclude_unset=True),
        operator_id=current_admin["id"],
    )
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="考勤班次不存在",
        )
    return shift


@router.delete("/{shift_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除考勤班次")
async def delete_attendance_shift(
    shift_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    current_admin: dict = Depends(get_current_admin),
):
    """删除考勤班次"""
    service = AttendanceShiftService(db, tenant_id=_require_anchor(tenant_anchor))
    success = await service.delete(shift_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="考勤班次不存在",
        )
    return None
