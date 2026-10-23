
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_admin,
    get_current_user,
    require_permission,
    require_tenant_active_for_write,
)
from app.core.config import settings
from app.db.session import get_db
from app.modules.support_tickets.service import SupportTicketService
from app.schemas.response import PageResponse
from app.schemas.support_ticket import (
    SupportTicketAssignRequest,
    SupportTicketCreate,
    SupportTicketQuery,
    SupportTicketResolveRequest,
    SupportTicketResponse,
    SupportTicketStatisticsResponse,
    SupportTicketStatus,
    SupportTicketUpdate,
)

router = APIRouter()


def _build_response(ticket) -> SupportTicketResponse:
    """构建工单响应"""
    return SupportTicketResponse.model_validate(ticket)


@router.get(
    "",
    response_model=PageResponse[SupportTicketResponse],
    summary="获取工单列表",
)
async def get_support_tickets(
    status: SupportTicketStatus | None = None,
    type: str | None = None,
    priority: str | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("support_ticket:list")),
):
    """获取工单列表（管理端）"""
    service = SupportTicketService(db)
    query = SupportTicketQuery(
        status=status,
        type=type,
        priority=priority,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    tickets, total = await service.get_list(query)
    return PageResponse(
        data=[_build_response(t) for t in tickets],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=SupportTicketResponse,
    summary="创建工单",
)
async def create_support_ticket(
    data: SupportTicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user),
    _tenant_guard: None = Depends(require_tenant_active_for_write),
):
    """创建工单（患者端/管理端均可）

    如果已登录，自动关联当前用户为创建人；
    未登录时需要通过其他方式传递 creator_id（当前不允许匿名）。
    """
    service = SupportTicketService(db)
    if current_user:
        creator_id = current_user.get("id")
        creator_type = "user"
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录后提交工单",
        )
    ticket = await service.create(data, creator_id=creator_id, creator_type=creator_type)
    return _build_response(ticket)


@router.get(
    "/statistics",
    response_model=SupportTicketStatisticsResponse,
    summary="获取工单统计",
)
async def get_support_ticket_statistics(
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("support_ticket:list")),
):
    """获取各状态工单数量统计"""
    service = SupportTicketService(db)
    stats = await service.get_statistics()
    return SupportTicketStatisticsResponse(**stats)


@router.get(
    "/{ticket_id}",
    response_model=SupportTicketResponse,
    summary="获取工单详情",
)
async def get_support_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("support_ticket:view")),
):
    """获取工单详情"""
    service = SupportTicketService(db)
    ticket = await service.get_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工单不存在，请检查后重试",
        )
    return _build_response(ticket)


@router.put(
    "/{ticket_id}",
    response_model=SupportTicketResponse,
    summary="更新工单",
)
async def update_support_ticket(
    ticket_id: str,
    data: SupportTicketUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("support_ticket:update")),
):
    """更新工单信息"""
    service = SupportTicketService(db)
    ticket = await service.update(ticket_id, data)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工单不存在，请检查后重试",
        )
    return _build_response(ticket)


@router.post(
    "/{ticket_id}/assign",
    response_model=SupportTicketResponse,
    summary="分配工单",
)
async def assign_support_ticket(
    ticket_id: str,
    req: SupportTicketAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("support_ticket:manage")),
):
    """分配工单给指定处理人"""
    service = SupportTicketService(db)
    ticket = await service.assign(ticket_id, req.assignee_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工单不存在，请检查后重试",
        )
    return _build_response(ticket)


@router.post(
    "/{ticket_id}/resolve",
    response_model=SupportTicketResponse,
    summary="解决工单",
)
async def resolve_support_ticket(
    ticket_id: str,
    req: SupportTicketResolveRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("support_ticket:manage")),
):
    """标记工单为已解决"""
    service = SupportTicketService(db)
    resolution = req.resolution if req else None
    ticket = await service.resolve(ticket_id, resolution=resolution)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工单不存在，请检查后重试",
        )
    return _build_response(ticket)


@router.post(
    "/{ticket_id}/close",
    response_model=SupportTicketResponse,
    summary="关闭工单",
)
async def close_support_ticket(
    ticket_id: str,
    req: SupportTicketResolveRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("support_ticket:manage")),
):
    """关闭工单"""
    service = SupportTicketService(db)
    resolution = req.resolution if req else None
    ticket = await service.close(ticket_id, resolution=resolution)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工单不存在，请检查后重试",
        )
    return _build_response(ticket)


@router.post(
    "/{ticket_id}/reopen",
    response_model=SupportTicketResponse,
    summary="重开工单",
)
async def reopen_support_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("support_ticket:manage")),
):
    """重开工单"""
    service = SupportTicketService(db)
    ticket = await service.reopen(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工单不存在，请检查后重试",
        )
    return _build_response(ticket)
