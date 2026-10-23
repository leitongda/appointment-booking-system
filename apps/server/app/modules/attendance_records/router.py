"""考勤打卡记录 API

提供签到、签退、考勤记录查询、统计等接口。
"""
from datetime import date
from io import BytesIO
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth_unified import get_current_account
from app.common.auth_types import AccountInfo
from app.common.permission_deps import require_permission
from app.common.tenant_deps import require_admin_tenant_anchor
from app.core.config import settings
from app.db.session import get_db
from app.infrastructure.excel.export_service import ExcelExportService
from app.modules.attendance_records.schemas import (
    AttendanceRecordResponse,
    CheckInRequest,
    CheckOutRequest,
    DailyStatResponse,
)
from app.modules.attendance_records.service import AttendanceRecordService
from app.schemas.rule_set import PageResult

router = APIRouter()


def _record_to_response(record) -> AttendanceRecordResponse:
    """将 ORM 对象转换为响应 Schema"""
    account_name = None
    shift_name = None

    return AttendanceRecordResponse(
        id=record.id,
        account_id=record.account_id,
        account_name=account_name,
        shift_id=record.shift_id,
        shift_name=shift_name,
        group_id=record.group_id,
        check_date=record.check_date.isoformat() if record.check_date else "",
        check_in_time=record.check_in_time.isoformat() if record.check_in_time else None,
        check_out_time=record.check_out_time.isoformat() if record.check_out_time else None,
        status=record.status or "normal",
        late_minutes=record.late_minutes or 0,
        early_minutes=record.early_minutes or 0,
        work_hours=record.work_hours,
        remark=record.remark,
    )


# ------------------------------------------------------------------ #
#  签到 / 签退（任何角色）
# ------------------------------------------------------------------ #


@router.post("/check-in", response_model=AttendanceRecordResponse, summary="签到")
async def check_in(
    data: CheckInRequest,
    current_account: AccountInfo = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    """签到打卡（支持 admin / doctor / user 任意角色）"""
    service = AttendanceRecordService(db)
    try:
        record = await service.check_in(
            account_id=current_account.id,
            tenant_id=current_account.tenant_id,
            account_name=current_account.name,
            lat=data.lat,
            lng=data.lng,
            device_info=data.device_info,
            group_id=data.group_id,
            wifi_ssid=data.wifi_ssid,
            device_id=data.device_id,
            remark=data.remark,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return _record_to_response(record)


@router.post("/check-out", response_model=AttendanceRecordResponse, summary="签退")
async def check_out(
    data: CheckOutRequest,
    current_account: AccountInfo = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    """签退打卡（支持 admin / doctor / user 任意角色）"""
    service = AttendanceRecordService(db)
    try:
        record = await service.check_out(
            account_id=current_account.id,
            lat=data.lat,
            lng=data.lng,
            device_info=data.device_info,
            remark=data.remark,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return _record_to_response(record)


# ------------------------------------------------------------------ #
#  我的考勤记录（任何角色）
# ------------------------------------------------------------------ #


@router.get("/my", response_model=PageResult[AttendanceRecordResponse], summary="我的考勤记录")
async def get_my_records(
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量"),
    current_account: AccountInfo = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的考勤记录"""
    service = AttendanceRecordService(db)
    records, total = await service.get_my_records(
        account_id=current_account.id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
    return PageResult(
        data=[_record_to_response(r) for r in records],
        total=total,
    )


# ------------------------------------------------------------------ #
#  管理员接口
# ------------------------------------------------------------------ #


@router.get(
    "/daily-stats/{target_date}",
    response_model=DailyStatResponse,
    summary="每日考勤统计",
)
async def get_daily_stats(
    target_date: date,
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("attendance:record")),
    db: AsyncSession = Depends(get_db),
):
    """获取指定日期的考勤汇总统计（管理员）"""
    service = AttendanceRecordService(db, tenant_id=tenant_anchor)
    stats = await service.get_daily_stats(tenant_anchor, target_date)
    return DailyStatResponse(**stats)


@router.get(
    "",
    response_model=PageResult[AttendanceRecordResponse],
    summary="全部考勤记录",
)
async def get_all_records(
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
    keyword: str | None = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量"),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("attendance:record")),
    db: AsyncSession = Depends(get_db),
):
    """获取全部考勤记录（管理员）"""
    service = AttendanceRecordService(db, tenant_id=tenant_anchor)
    records, total = await service.get_all_records(
        tenant_id=tenant_anchor,
        start_date=start_date,
        end_date=end_date,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return PageResult(
        data=[_record_to_response(r) for r in records],
        total=total,
    )


# ------------------------------------------------------------------ #
#  导出考勤报表（管理员）
# ------------------------------------------------------------------ #

# 考勤状态中文映射
_STATUS_CN = {
    "normal": "正常",
    "late": "迟到",
    "early": "早退",
    "absent": "缺勤",
    "leave": "请假",
    "field_work": "外勤",
}


@router.get("/export", summary="导出考勤报表")
async def export_attendance_records(
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    keyword: str | None = Query(None, description="搜索关键词"),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("attendance:record", "record:export")),
):
    """导出考勤记录为 Excel"""
    # 1. 解析日期
    sd = date.fromisoformat(start_date)
    ed = date.fromisoformat(end_date)

    # 2. 租户隔离（R1-11：账号锚点，不再回退请求上下文）
    tenant_id = tenant_anchor

    # 3. 查询全部数据（不分页）
    service = AttendanceRecordService(db, tenant_id=tenant_anchor)
    records, _ = await service.get_all_records(
        tenant_id=tenant_id,
        start_date=sd,
        end_date=ed,
        keyword=keyword,
        page=1,
        page_size=100000,
    )

    # 4. 批量获取账号信息（账号名、姓名）
    from sqlalchemy import select
    from app.models.account import Account

    account_ids = list({r.account_id for r in records})
    account_map: dict[str, tuple[str, str]] = {}  # id -> (username, name)
    if account_ids:
        result = await db.execute(
            select(Account.id, Account.username, Account.name).where(
                Account.id.in_(account_ids)
            )
        )
        for row in result:
            account_map[row.id] = (row.username or "", row.name or "")

    # 5. 批量获取班次信息
    from app.models.attendance import AttendanceShift

    shift_ids = list({r.shift_id for r in records if r.shift_id})
    shift_map: dict[str, str] = {}  # id -> name
    if shift_ids:
        result = await db.execute(
            select(AttendanceShift.id, AttendanceShift.name).where(
                AttendanceShift.id.in_(shift_ids)
            )
        )
        for row in result:
            shift_map[row.id] = row.name

    # 6. 构建 Excel 数据
    headers = [
        "账号名", "姓名", "班次", "日期",
        "签到时间", "签退时间", "状态",
        "迟到分钟", "早退分钟", "工作时长", "备注",
    ]

    data = []
    for r in records:
        acct = account_map.get(r.account_id, ("", ""))
        check_in = r.check_in_time.strftime("%H:%M:%S") if r.check_in_time else ""
        check_out = r.check_out_time.strftime("%H:%M:%S") if r.check_out_time else ""
        work_hours = f"{r.work_hours:.2f}" if r.work_hours is not None else ""

        data.append([
            acct[0],                    # 账号名
            acct[1],                    # 姓名
            shift_map.get(r.shift_id, ""),  # 班次
            r.check_date.isoformat(),   # 日期
            check_in,                   # 签到时间
            check_out,                  # 签退时间
            _STATUS_CN.get(r.status, r.status),  # 状态
            r.late_minutes or 0,        # 迟到分钟
            r.early_minutes or 0,       # 早退分钟
            work_hours,                 # 工作时长
            r.remark or "",             # 备注
        ])

    excel_bytes = ExcelExportService.create_workbook(headers, data, "考勤报表")
    suffix = f"{sd.strftime('%Y%m%d')}_{ed.strftime('%Y%m%d')}"
    # Content-Disposition 头只允许 latin-1：ASCII 兜底 + RFC 5987 中文文件名
    disposition = (
        f"attachment; filename=attendance_{suffix}.xlsx; "
        f"filename*=UTF-8''{quote(f'考勤报表_{suffix}.xlsx')}"
    )

    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": disposition},
    )
