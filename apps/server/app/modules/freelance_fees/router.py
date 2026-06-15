"""兼职费用模块路由"""
from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_store_filter, require_permission
from app.core.config import settings
from app.db.session import get_db
from app.modules.freelance_fees.schemas import (
    EngagementBatchUpdate,
    FreelanceInteractionCreate,
    FreelanceInteractionResponse,
    FreelancerCreate,
    FreelancerQuery,
    FreelancerResponse,
    FreelancerUpdate,
    FreelanceSettlementQuery,
    FreelanceSettlementResponse,
    FreelanceTaskCreate,
    FreelanceTaskQuery,
    FreelanceTaskResponse,
    FreelanceTaskUpdate,
    SettlementConfirmRequest,
    SettlementRejectRequest,
)
from app.modules.freelance_fees.service import FreelanceService
from app.schemas.response import PageResponse
from app.utils.audit import set_create_audit, set_update_audit

router = APIRouter()


# ========== 兼职人员 ==========

@router.get("/freelancers", response_model=PageResponse[FreelancerResponse], summary="兼职人员列表")
async def get_freelancer_list(
    name: str | None = None,
    store_id: str | None = None,
    status: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("freelance:list")),
):
    store_filter = get_store_filter(current_admin)
    service = FreelanceService(db)
    query = FreelancerQuery(
        name=name,
        store_id=store_filter if isinstance(store_filter, str) else store_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    items, total = await service.get_freelancer_list(query)
    return PageResponse(
        data=[FreelancerResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/freelancers/{freelancer_id}", response_model=FreelancerResponse, summary="兼职人员详情")
async def get_freelancer(
    freelancer_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("freelance:list")),
):
    service = FreelanceService(db)
    freelancer = await service.get_freelancer_by_id(freelancer_id)
    if not freelancer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="兼职人员不存在")
    return FreelancerResponse.model_validate(freelancer)


@router.post("/freelancers", response_model=FreelancerResponse, summary="新增兼职人员")
async def create_freelancer(
    data: FreelancerCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("freelance:create")),
):
    service = FreelanceService(db)
    freelancer = await service.create_freelancer(data, operator_id=current_admin.get("id"))
    return FreelancerResponse.model_validate(freelancer)


@router.put("/freelancers/{freelancer_id}", response_model=FreelancerResponse, summary="更新兼职人员")
async def update_freelancer(
    freelancer_id: str,
    data: FreelancerUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("freelance:update")),
):
    service = FreelanceService(db)
    freelancer = await service.update_freelancer(freelancer_id, data, operator_id=current_admin.get("id"))
    if not freelancer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="兼职人员不存在")
    return FreelancerResponse.model_validate(freelancer)


@router.delete("/freelancers/{freelancer_id}", summary="禁用兼职人员")
async def delete_freelancer(
    freelancer_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("freelance:delete")),
):
    service = FreelanceService(db)
    success = await service.delete_freelancer(freelancer_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="兼职人员不存在")
    return {"message": "已禁用"}


# ========== 发布任务 ==========

@router.get("/tasks", response_model=PageResponse[FreelanceTaskResponse], summary="任务列表")
async def get_task_list(
    freelancer_id: str | None = None,
    store_id: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("freelance:list")),
):
    store_filter = get_store_filter(current_admin)
    service = FreelanceService(db)
    query = FreelanceTaskQuery(
        freelancer_id=freelancer_id,
        store_id=store_filter if isinstance(store_filter, str) else store_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    items, total = await service.get_task_list(query)

    # 补充兼职人员姓名
    result = []
    for item in items:
        resp = FreelanceTaskResponse.model_validate(item)
        if item.freelancer_id:
            freelancer = await service.get_freelancer_by_id(item.freelancer_id)
            if freelancer:
                resp.freelancer_name = freelancer.name
        result.append(resp)

    return PageResponse(data=result, total=total, page=page, page_size=page_size)


@router.get("/tasks/{task_id}", response_model=FreelanceTaskResponse, summary="任务详情")
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("freelance:list")),
):
    service = FreelanceService(db)
    task = await service.get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    resp = FreelanceTaskResponse.model_validate(task)
    if task.freelancer_id:
        freelancer = await service.get_freelancer_by_id(task.freelancer_id)
        if freelancer:
            resp.freelancer_name = freelancer.name
    return resp


@router.post("/tasks", response_model=FreelanceTaskResponse, summary="新增任务")
async def create_task(
    data: FreelanceTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("freelance:create")),
):
    service = FreelanceService(db)
    task = await service.create_task(data, operator_id=current_admin.get("id"))
    return FreelanceTaskResponse.model_validate(task)


@router.put("/tasks/{task_id}", response_model=FreelanceTaskResponse, summary="更新任务")
async def update_task(
    task_id: str,
    data: FreelanceTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("freelance:update")),
):
    service = FreelanceService(db)
    task = await service.update_task(task_id, data, operator_id=current_admin.get("id"))
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return FreelanceTaskResponse.model_validate(task)


# ========== 互动记录 ==========

@router.get("/tasks/{task_id}/interactions", response_model=list[FreelanceInteractionResponse], summary="任务互动列表")
async def get_task_interactions(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("freelance:list")),
):
    service = FreelanceService(db)
    interactions = await service.get_interactions_by_task(task_id)
    return [FreelanceInteractionResponse.model_validate(i) for i in interactions]


@router.post("/interactions", response_model=FreelanceInteractionResponse, summary="新增互动记录")
async def create_interaction(
    data: FreelanceInteractionCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("freelance:create")),
):
    service = FreelanceService(db)
    interaction = await service.add_interaction(data, operator_id=current_admin.get("id"))
    if not interaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return FreelanceInteractionResponse.model_validate(interaction)


# ========== 数据采集 ==========

@router.post("/engagement/batch-update", summary="批量更新互动数据")
async def batch_update_engagement(
    data: EngagementBatchUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("freelance:update")),
):
    """批量更新任务的点赞、评论、收录等数据（数据采集用）"""
    from decimal import Decimal
    service = FreelanceService(db)
    updated = 0
    errors = []

    for item in data.updates:
        try:
            task = await service.get_task_by_id(item.task_id)
            if not task:
                errors.append({"task_id": item.task_id, "error": "任务不存在"})
                continue

            if item.likes_count is not None:
                task.likes_count = item.likes_count
                task.likes_bonus_amount = Decimal("10") if item.likes_count >= 50 else Decimal("0")

            if item.comments_count is not None:
                task.comments_count = item.comments_count

            if item.is_indexed is not None:
                task.is_indexed = item.is_indexed
                if item.is_indexed and task.status == "published":
                    task.status = "indexed"

            if item.screenshot_url:
                task.remark = (task.remark or "") + f"\n截图: {item.screenshot_url}"

            set_update_audit(task, current_admin.get("id"))
            updated += 1
        except Exception as e:
            errors.append({"task_id": item.task_id, "error": str(e)})

    await db.commit()
    return {"updated": updated, "errors": errors}


# ========== 结算 ==========

@router.get("/settlements", response_model=PageResponse[FreelanceSettlementResponse], summary="结算列表")
async def get_settlement_list(
    freelancer_id: str | None = None,
    store_id: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("freelance:list")),
):
    store_filter = get_store_filter(current_admin)
    service = FreelanceService(db)
    query = FreelanceSettlementQuery(
        freelancer_id=freelancer_id,
        store_id=store_filter if isinstance(store_filter, str) else store_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    items, total = await service.get_settlement_list(query)

    result = []
    for item in items:
        resp = FreelanceSettlementResponse.model_validate(item)
        freelancer = await service.get_freelancer_by_id(item.freelancer_id)
        if freelancer:
            resp.freelancer_name = freelancer.name
        result.append(resp)

    return PageResponse(data=result, total=total, page=page, page_size=page_size)


@router.get("/settlements/{settlement_id}", response_model=FreelanceSettlementResponse, summary="结算详情")
async def get_settlement(
    settlement_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("freelance:list")),
):
    service = FreelanceService(db)
    settlement = await service.get_settlement_by_id(settlement_id)
    if not settlement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="结算单不存在")

    resp = FreelanceSettlementResponse.model_validate(settlement)
    freelancer = await service.get_freelancer_by_id(settlement.freelancer_id)
    if freelancer:
        resp.freelancer_name = freelancer.name

    items = await service.get_settlement_items(settlement_id)
    from app.modules.freelance_fees.schemas import FreelanceSettlementItemResponse
    resp.items = [FreelanceSettlementItemResponse.model_validate(i) for i in items]
    return resp


@router.post("/settlements/generate", response_model=FreelanceSettlementResponse, summary="生成结算单")
async def generate_settlement(
    freelancer_id: str = Query(..., description="兼职人员ID"),
    store_id: str | None = Query(None, description="门店ID"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("freelance:settle")),
):
    service = FreelanceService(db)
    settlement = await service.generate_settlement(
        freelancer_id=freelancer_id,
        store_id=store_id,
        operator_id=current_admin.get("id"),
    )
    if not settlement:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无可结算的记录")
    return FreelanceSettlementResponse.model_validate(settlement)


@router.post("/settlements/{settlement_id}/confirm", response_model=FreelanceSettlementResponse, summary="确认结算")
async def confirm_settlement(
    settlement_id: str,
    data: SettlementConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("freelance:settle")),
):
    service = FreelanceService(db)
    settlement = await service.confirm_settlement(
        settlement_id=settlement_id,
        operator_id=current_admin.get("id"),
        remark=data.remark,
    )
    if not settlement:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="结算单不存在或状态不允许确认")
    return FreelanceSettlementResponse.model_validate(settlement)


@router.post("/settlements/{settlement_id}/reject", response_model=FreelanceSettlementResponse, summary="驳回结算")
async def reject_settlement(
    settlement_id: str,
    data: SettlementRejectRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("freelance:settle")),
):
    service = FreelanceService(db)
    settlement = await service.reject_settlement(
        settlement_id=settlement_id,
        operator_id=current_admin.get("id"),
        reject_reason=data.reject_reason,
    )
    if not settlement:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="结算单不存在或状态不允许驳回")
    return FreelanceSettlementResponse.model_validate(settlement)


@router.post("/settlements/{settlement_id}/paid", response_model=FreelanceSettlementResponse, summary="标记已支付")
async def mark_settlement_paid(
    settlement_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("freelance:settle")),
):
    service = FreelanceService(db)
    settlement = await service.mark_settlement_paid(
        settlement_id=settlement_id,
        operator_id=current_admin.get("id"),
    )
    if not settlement:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="结算单不存在或状态不允许标记支付")
    return FreelanceSettlementResponse.model_validate(settlement)


# ========== 统计 ==========

@router.get("/statistics", summary="兼职费用统计")
async def get_statistics(
    store_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("freelance:list")),
):
    store_filter = get_store_filter(current_admin)
    service = FreelanceService(db)
    stats = await service.get_freelancer_stats(
        store_id=store_filter if isinstance(store_filter, str) else store_id,
    )
    return stats


@router.get("/statistics/by-freelancer", summary="按兼职人员统计")
async def get_statistics_by_freelancer(
    store_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("freelance:list")),
):
    store_filter = get_store_filter(current_admin)
    service = FreelanceService(db)
    return await service.get_stats_by_freelancer(
        store_id=store_filter if isinstance(store_filter, str) else store_id,
    )


@router.get("/statistics/by-month", summary="按月统计")
async def get_statistics_by_month(
    store_id: str | None = None,
    months: int = Query(12, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("freelance:list")),
):
    store_filter = get_store_filter(current_admin)
    service = FreelanceService(db)
    return await service.get_stats_by_month(
        store_id=store_filter if isinstance(store_filter, str) else store_id,
        months=months,
    )


@router.get("/statistics/tasks", summary="任务统计")
async def get_task_statistics(
    store_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("freelance:list")),
):
    store_filter = get_store_filter(current_admin)
    service = FreelanceService(db)
    return await service.get_task_stats(
        store_id=store_filter if isinstance(store_filter, str) else store_id,
    )


# ========== 导出 ==========

@router.get("/export/settlements", summary="导出结算数据")
async def export_settlements(
    store_id: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("freelance:list")),
):
    """导出结算列表为 Excel"""
    from app.infrastructure.excel.export_service import ExcelExportService
    from app.middleware.tenant_context import get_current_tenant_id
    from app.models.freelance import Freelancer, FreelanceSettlement

    store_filter = get_store_filter(current_admin)
    tenant_id = get_current_tenant_id()

    stmt = select(FreelanceSettlement).join(
        Freelancer, FreelanceSettlement.freelancer_id == Freelancer.id
    )
    if tenant_id:
        stmt = stmt.where(FreelanceSettlement.tenant_id == tenant_id)
    if isinstance(store_filter, str):
        stmt = stmt.where(FreelanceSettlement.store_id == store_filter)
    elif store_id:
        stmt = stmt.where(FreelanceSettlement.store_id == store_id)
    if status_filter:
        stmt = stmt.where(FreelanceSettlement.status == status_filter)
    if start_date:
        stmt = stmt.where(FreelanceSettlement.created_at >= start_date)
    if end_date:
        stmt = stmt.where(FreelanceSettlement.created_at <= end_date)
    stmt = stmt.order_by(FreelanceSettlement.created_at.desc())

    settlements = (await db.execute(stmt)).scalars().all()

    # 构建兼职人员名称映射
    freelancer_ids = {s.freelancer_id for s in settlements}
    if freelancer_ids:
        freelancers = (await db.execute(
            select(Freelancer).where(Freelancer.id.in_(freelancer_ids))
        )).scalars().all()
        name_map = {f.id: f.name for f in freelancers}
    else:
        name_map = {}

    status_labels = {"pending": "待确认", "confirmed": "已确认", "paid": "已支付", "cancelled": "已驳回"}

    headers = ["结算单号", "兼职人员", "基础金额", "补贴金额", "点赞奖励", "互动金额", "总金额", "实付金额", "状态", "创建时间"]
    data = []
    for s in settlements:
        data.append([
            s.settlement_no,
            name_map.get(s.freelancer_id, s.freelancer_id),
            float(s.base_total or 0),
            float(s.bonus_total or 0),
            float(s.likes_bonus_total or 0),
            float(s.interaction_total or 0),
            float(s.total_amount or 0),
            float(s.actual_amount or 0),
            status_labels.get(s.status, s.status),
            s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "",
        ])

    excel_bytes = ExcelExportService.create_workbook(headers, data, "结算数据")
    filename = f"兼职结算_{datetime.utcnow().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ========== 导入 ==========

@router.get("/import/template", summary="下载兼职人员导入模板")
async def download_import_template():
    """下载兼职人员导入模板"""
    from app.infrastructure.excel.import_service import ExcelImportService

    headers = ["姓名", "手机号", "门店名称", "平台", "账号名", "账号类型", "备注"]
    sample_data = [
        ["张三", "13800138000", "总店", "小红书", "zhangsan_xhs", "老账号", "中医方向"],
        ["李四", "13900139000", "分店A", "抖音", "lisi_dy", "新账号", ""],
    ]
    required_fields = ["姓名"]
    field_notes = {
        "平台": "可选值：小红书/抖音/微博/微信/其他",
        "账号类型": "可选值：老账号/新账号",
    }

    excel_bytes = ExcelImportService.create_template(headers, sample_data, required_fields, field_notes)
    filename = "兼职人员导入模板.xlsx"
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/import/freelancers", summary="批量导入兼职人员")
async def import_freelancers(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("freelance:create")),
):
    """批量导入兼职人员"""
    from app.middleware.tenant_context import get_current_tenant_id
    from app.models.freelance import Freelancer
    from app.models.store import Store
    from app.modules.import_export.service_import import ImportService

    filename = (file.filename or "").lower()
    if not filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="请上传 .xlsx 或 .xls 格式的 Excel 文件")

    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="导入操作需要租户上下文")

    content = await file.read()
    headers = ["姓名", "手机号", "门店名称", "平台", "账号名", "账号类型", "备注"]
    required_fields = ["姓名"]

    # 预加载门店映射
    stores_result = await db.execute(select(Store).where(Store.tenant_id == tenant_id))
    stores = {s.name: s for s in stores_result.scalars().all()}

    platform_map = {"小红书": "xiaohongshu", "抖音": "douyin", "微博": "weibo", "微信": "wechat", "其他": "other"}
    type_map = {"老账号": "old", "新账号": "new"}

    async def process_row(row_data):
        import uuid
        store_name = row_data.get("门店名称")
        store_id = None
        if store_name:
            store = stores.get(store_name)
            if not store:
                raise ValueError(f"门店 '{store_name}' 不存在")
            store_id = store.id

        platform = platform_map.get(row_data.get("平台", ""), "other")
        account_type = type_map.get(row_data.get("账号类型", ""), "old")

        freelancer = Freelancer(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            store_id=store_id,
            name=row_data.get("姓名"),
            phone=row_data.get("手机号"),
            account_name=row_data.get("账号名"),
            account_platform=platform,
            account_type=account_type,
            access_token=uuid.uuid4().hex,
            status=1,
            remark=row_data.get("备注"),
        )
        set_create_audit(freelancer, current_admin.get("id"))
        db.add(freelancer)

    import_service = ImportService(db)
    result = await import_service.validate_and_import(
        content, file.filename, headers, required_fields, process_row
    )
    return result
