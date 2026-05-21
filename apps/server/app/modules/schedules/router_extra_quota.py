from fastapi import APIRouter, Depends, Header, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.db.session import get_db
from app.api.deps import get_current_admin, get_store_filter, require_permission
from app.core.redis import get_redis
from app.schemas.extra_quota import (
    ExtraQuotaRequestCreate, ExtraQuotaApprovalRequest,
    ExtraQuotaRequestResponse, ExtraQuotaListResponse,
)
from app.models.schedule import Schedule
from app.utils.idempotency import check_idempotency, store_idempotency

router = APIRouter()


@router.post(
    "/extra-quota",
    response_model=ExtraQuotaRequestResponse,
    summary="创建加号申请",
    description="""
    创建加号申请。

    **权限要求**：管理员权限（schedule:extra-quota）。

    **业务规则**：
    - 加号数量 <= 5 时自动批准并立即更新排班号源
    - 加号数量 > 5 时创建待审批记录，等待有审批权限的管理员审批
    - 使用分布式锁保护号源更新，防止并发冲突
    """,
)
async def create_extra_quota_request(
    data: ExtraQuotaRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:extra-quota")),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """创建加号申请"""
    from app.modules.schedules.service_extra_quota import ExtraQuotaService

    tenant_id = get_store_filter(current_admin) or current_admin.get("tenant_id", "")

    # 幂等性检查：如果提供了 Idempotency-Key，先查 Redis 缓存
    if idempotency_key:
        redis = await get_redis()
        cached = await check_idempotency(redis, idempotency_key, tenant_id)
        if cached is not None:
            return ExtraQuotaRequestResponse(**cached)

    service = ExtraQuotaService(db)

    # 获取门店 ID
    store_id = current_admin.get("current_store_id") or current_admin.get("store_id", "")
    if not store_id:
        schedule_result = await db.execute(
            select(Schedule.store_id).where(Schedule.id == data.schedule_id)
        )
        store_id_row = schedule_result.scalar_one_or_none()
        if store_id_row:
            store_id = store_id_row

    try:
        request = await service.create_request(
            tenant_id=tenant_id,
            store_id=store_id,
            applicant_id=current_admin.get("id", ""),
            schedule_id=data.schedule_id,
            quantity=data.quantity,
            quota_type=data.quota_type.value if hasattr(data.quota_type, 'value') else data.quota_type,
            open_to_public=data.open_to_public,
            patient_id=data.patient_id,
            reason=data.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    response = ExtraQuotaRequestResponse.model_validate(request)

    # 幂等性存储：成功后缓存响应
    if idempotency_key:
        redis = await get_redis()
        await store_idempotency(redis, idempotency_key, tenant_id, response.model_dump(mode="json"))

    return response


@router.post(
    "/extra-quota/{request_id}/approve",
    response_model=ExtraQuotaRequestResponse,
    summary="审批通过加号申请",
    description="""
    审批通过加号申请。

    **权限要求**：管理员权限（schedule:extra-quota:approve）。

    **业务规则**：
    - 只有 pending 状态的申请可以审批
    - 批准后自动更新排班的 extra_quota 号源
    - 使用分布式锁保护号源更新
    """,
)
async def approve_extra_quota(
    request_id: str,
    data: ExtraQuotaApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:extra-quota:approve")),
):
    """审批通过加号申请"""
    from app.modules.schedules.service_extra_quota import ExtraQuotaService

    service = ExtraQuotaService(db)
    tenant_id = get_store_filter(current_admin) or current_admin.get("tenant_id", "")

    try:
        request = await service.approve(
            tenant_id=tenant_id,
            request_id=request_id,
            approver_id=current_admin.get("id", ""),
            remark=data.remark,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return ExtraQuotaRequestResponse.model_validate(request)


@router.post(
    "/extra-quota/{request_id}/reject",
    response_model=ExtraQuotaRequestResponse,
    summary="拒绝加号申请",
    description="""
    拒绝加号申请。

    **权限要求**：管理员权限（schedule:extra-quota:approve）。

    **业务规则**：
    - 只有 pending 状态的申请可以操作
    - 拒绝后不更新排班号源
    """,
)
async def reject_extra_quota(
    request_id: str,
    data: ExtraQuotaApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:extra-quota:approve")),
):
    """拒绝加号申请"""
    from app.modules.schedules.service_extra_quota import ExtraQuotaService

    service = ExtraQuotaService(db)
    tenant_id = get_store_filter(current_admin) or current_admin.get("tenant_id", "")

    try:
        request = await service.reject(
            tenant_id=tenant_id,
            request_id=request_id,
            approver_id=current_admin.get("id", ""),
            remark=data.remark,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return ExtraQuotaRequestResponse.model_validate(request)


@router.get(
    "/extra-quota",
    response_model=ExtraQuotaListResponse,
    summary="查询加号申请列表",
    description="""
    查询加号申请列表。

    **权限要求**：管理员权限（schedule:extra-quota）。

    **支持筛选条件**：
    - store_id: 按门店筛选
    - schedule_id: 按排班筛选
    - doctor_id: 按医生筛选
    - approval_status: 按审批状态筛选（pending/approved/rejected/cancelled）
    - start_date / end_date: 按排班日期范围筛选
    """,
)
async def list_extra_quota_requests(
    store_id: Optional[str] = Query(None, description="门店ID"),
    schedule_id: Optional[str] = Query(None, description="排班ID"),
    doctor_id: Optional[str] = Query(None, description="医生ID"),
    approval_status: Optional[str] = Query(None, description="审批状态"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:extra-quota")),
):
    """查询加号申请列表"""
    from app.modules.schedules.service_extra_quota import ExtraQuotaService

    service = ExtraQuotaService(db)
    tenant_id = get_store_filter(current_admin) or current_admin.get("tenant_id", "")

    # 门店过滤：门店管理员自动限制
    effective_store_id = get_store_filter(current_admin) or store_id

    items, total = await service.get_list(
        tenant_id=tenant_id,
        store_id=effective_store_id,
        schedule_id=schedule_id,
        doctor_id=doctor_id,
        approval_status=approval_status,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

    return ExtraQuotaListResponse(
        data=[ExtraQuotaRequestResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )
