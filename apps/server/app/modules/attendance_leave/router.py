"""假期管理 API

提供假期类型、假期余额、假期申请的 CRUD 接口
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, require_admin_tenant_anchor
from app.common.auth_unified import get_current_account
from app.core.config import settings
from app.db.session import get_db
from app.modules.attendance_leave.schemas import (
    LeaveBalanceResponse,
    LeaveBalanceUpdate,
    LeaveRequestCreate,
    LeaveRequestResponse,
    LeaveReviewRequest,
    LeaveTypeCreate,
    LeaveTypeResponse,
    LeaveTypeUpdate,
)
from app.modules.attendance_leave.service import AttendanceLeaveService
from app.schemas.rule_set import PageResult

router = APIRouter()


def _require_anchor(tenant_anchor: str | None) -> str:
    """R1-11：管理端写路径必须拿到账号锚点，禁止写出 tenant_id=NULL 的记录。"""
    if not tenant_anchor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法确定租户ID，请指定 tenant_id 后重试",
        )
    return tenant_anchor


# ==================== 假期类型 ====================


@router.get("/types", response_model=PageResult[LeaveTypeResponse], summary="获取假期类型列表")
async def get_leave_types(
    enabled: bool | None = Query(None, description="是否启用"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    service = AttendanceLeaveService(db, tenant_id=tenant_anchor)
    items, total = await service.get_type_list(enabled=enabled, page=page, page_size=page_size)
    return PageResult(data=items, total=total)


@router.post("/types", response_model=LeaveTypeResponse, status_code=status.HTTP_201_CREATED, summary="创建假期类型")
async def create_leave_type(
    data: LeaveTypeCreate,
    db: AsyncSession = Depends(get_db),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    current_admin: dict = Depends(get_current_admin),
):
    service = AttendanceLeaveService(db, tenant_id=_require_anchor(tenant_anchor))
    try:
        leave_type = await service.create_type(
            data=data.model_dump(),
            operator_id=current_admin["id"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return leave_type


@router.put("/types/{type_id}", response_model=LeaveTypeResponse, summary="更新假期类型")
async def update_leave_type(
    type_id: str,
    data: LeaveTypeUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    current_admin: dict = Depends(get_current_admin),
):
    service = AttendanceLeaveService(db, tenant_id=_require_anchor(tenant_anchor))
    leave_type = await service.update_type(
        type_id=type_id,
        data=data.model_dump(exclude_unset=True),
        operator_id=current_admin["id"],
    )
    if not leave_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="假期类型不存在")
    return leave_type


@router.delete("/types/{type_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除假期类型")
async def delete_leave_type(
    type_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    current_admin: dict = Depends(get_current_admin),
):
    service = AttendanceLeaveService(db, tenant_id=_require_anchor(tenant_anchor))
    success = await service.delete_type(type_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="假期类型不存在")
    return None


# ==================== 假期余额 ====================


@router.get("/balances", response_model=list[LeaveBalanceResponse], summary="获取假期余额")
async def get_leave_balances(
    account_id: str = Query(..., description="账号ID"),
    year: int | None = Query(None, description="年度"),
    db: AsyncSession = Depends(get_db),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    service = AttendanceLeaveService(db, tenant_id=tenant_anchor)
    return await service.get_balances(account_id=account_id, year=year)


@router.put("/balances", response_model=LeaveBalanceResponse, summary="更新假期余额")
async def update_leave_balance(
    data: LeaveBalanceUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    current_admin: dict = Depends(get_current_admin),
):
    service = AttendanceLeaveService(db, tenant_id=_require_anchor(tenant_anchor))
    balance = await service.update_balance(
        account_id=data.account_id,
        leave_type_id=data.leave_type_id,
        year=data.year,
        total_days=data.total_days,
        operator_id=current_admin["id"],
    )
    return balance


# ==================== 假期申请 ====================


@router.post("/requests", response_model=LeaveRequestResponse, status_code=status.HTTP_201_CREATED, summary="创建假期申请")
async def create_leave_request(
    data: LeaveRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_account: dict = Depends(get_current_account),
):
    service = AttendanceLeaveService(db)
    leave_request = await service.create_request(
        account_id=current_account["id"],
        data=data.model_dump(),
        operator_id=current_account["id"],
    )
    return leave_request


@router.get("/requests/my", response_model=PageResult[LeaveRequestResponse], summary="我的假期申请")
async def get_my_leave_requests(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_account: dict = Depends(get_current_account),
):
    service = AttendanceLeaveService(db)
    items, total = await service.get_my_requests(
        account_id=current_account["id"],
        page=page,
        page_size=page_size,
    )
    return PageResult(data=items, total=total)


@router.get("/requests", response_model=PageResult[LeaveRequestResponse], summary="所有假期申请（管理员）")
async def get_all_leave_requests(
    keyword: str | None = Query(None, description="搜索关键词"),
    status_filter: str | None = Query(None, alias="status", description="状态过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    service = AttendanceLeaveService(db, tenant_id=tenant_anchor)
    items, total = await service.get_all_requests(
        tenant_id=tenant_anchor,
        keyword=keyword,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    return PageResult(data=items, total=total)


@router.post("/requests/{request_id}/approve", response_model=LeaveRequestResponse, summary="审批通过")
async def approve_leave_request(
    request_id: str,
    body: LeaveReviewRequest | None = None,
    db: AsyncSession = Depends(get_db),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    current_admin: dict = Depends(get_current_admin),
):
    service = AttendanceLeaveService(db, tenant_id=_require_anchor(tenant_anchor))
    comment = body.comment if body else None
    leave_request = await service.approve(
        request_id=request_id,
        reviewer_id=current_admin["id"],
        comment=comment,
    )
    if not leave_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="假期申请不存在或已处理")
    return leave_request


@router.post("/requests/{request_id}/reject", response_model=LeaveRequestResponse, summary="驳回")
async def reject_leave_request(
    request_id: str,
    body: LeaveReviewRequest | None = None,
    db: AsyncSession = Depends(get_db),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    current_admin: dict = Depends(get_current_admin),
):
    service = AttendanceLeaveService(db, tenant_id=_require_anchor(tenant_anchor))
    comment = body.comment if body else None
    leave_request = await service.reject(
        request_id=request_id,
        reviewer_id=current_admin["id"],
        comment=comment,
    )
    if not leave_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="假期申请不存在或已处理")
    return leave_request
