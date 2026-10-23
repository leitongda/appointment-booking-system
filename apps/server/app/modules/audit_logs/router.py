"""审计日志 API"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_admin, require_admin_tenant_anchor
from app.core.config import settings
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.rule_set import AppointmentCheckin

router = APIRouter()


def _resolve_audit_tenant(current_admin: dict, tenant_id: str | None) -> str:
    """R1-19：审计数据只按账号锚点访问（不回退请求上下文）。

    - 租户管理员传他人 tenant_id → 403；
    - 平台管理员未指定租户 → 400；
    - 平台管理员指定租户 → 以该租户为锚点。
    """
    anchor = require_admin_tenant_anchor(tenant_id=tenant_id, current_admin=current_admin)
    if tenant_id and anchor and tenant_id != anchor:
        raise HTTPException(status_code=403, detail="无权访问其他租户的数据")
    if not anchor:
        raise HTTPException(status_code=400, detail="无法确定租户ID，请指定 tenant_id 后重试")
    return anchor


@router.get("/checkin-logs")
async def get_checkin_logs(
    appointment_id: str | None = Query(None, description="预约ID"),
    patient_id: str | None = Query(None, description="患者ID"),
    status: str | None = Query(None, description="状态"),
    checkin_method: str | None = Query(None, description="签到方式"),
    start_time: datetime | None = Query(None, description="开始时间"),
    end_time: datetime | None = Query(None, description="结束时间"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量"),
    tenant_id: str | None = Query(None, description="租户ID（平台管理员必须显式指定）"),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """查询签到审计日志"""
    tenant_id = _resolve_audit_tenant(current_admin, tenant_id)

    # 构建 with appointment join
    query = select(AppointmentCheckin).options(
        selectinload(AppointmentCheckin.appointment)
    ).join(Appointment, AppointmentCheckin.appointment_id == Appointment.id)

    conditions = []

    # 租户过滤
    if tenant_id:
        conditions.append(Appointment.tenant_id == tenant_id)

    if appointment_id:
        conditions.append(AppointmentCheckin.appointment_id == appointment_id)

    if status:
        conditions.append(AppointmentCheckin.status == status)

    if checkin_method:
        conditions.append(AppointmentCheckin.checkin_method == checkin_method)

    if start_time:
        conditions.append(AppointmentCheckin.checkin_time >= start_time)

    if end_time:
        conditions.append(AppointmentCheckin.checkin_time <= end_time)

    if patient_id:
        conditions.append(Appointment.patient_id == patient_id)

    if conditions:
        query = query.where(and_(*conditions))

    # 统计总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页查询
    query = query.order_by(desc(AppointmentCheckin.checkin_time))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    # 格式化返回
    items = []
    for log in logs:
        item = {
            "id": log.id,
            "appointmentId": log.appointment_id,
            "checkinTime": log.checkin_time.isoformat() if log.checkin_time else None,
            "checkinMethod": log.checkin_method,
            "deviceInfo": log.device_info,
            "locationInfo": log.location_info,
            "operatorId": log.operator_id,
            "operatorType": log.operator_type,
            "status": log.status,
            "failReason": log.fail_reason,
            "createdAt": log.created_at.isoformat() if log.created_at else None,
        }

        if log.appointment:
            item["patientName"] = getattr(log.appointment, 'patient_name', None)
            item["patientPhone"] = getattr(log.appointment, 'patient_phone', None)
            item["doctorName"] = getattr(log.appointment, 'doctor_name', None)
            item["departmentName"] = getattr(log.appointment, 'department_name', None)

        items.append(item)

    return {
        "data": items,
        "total": total,
        "page": page,
        "pageSize": page_size
    }


@router.get("/checkin-logs/statistics")
async def get_checkin_log_statistics(
    start_date: datetime | None = Query(None, description="开始日期"),
    end_date: datetime | None = Query(None, description="结束日期"),
    tenant_id: str | None = Query(None, description="租户ID（平台管理员必须显式指定）"),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取签到审计日志统计"""
    tenant_id = _resolve_audit_tenant(current_admin, tenant_id)

    query = select(
        AppointmentCheckin.status,
        func.count(AppointmentCheckin.id).label('count')
    ).join(Appointment, AppointmentCheckin.appointment_id == Appointment.id)

    conditions = []
    if tenant_id:
        conditions.append(Appointment.tenant_id == tenant_id)
    if start_date:
        conditions.append(AppointmentCheckin.checkin_time >= start_date)
    if end_date:
        conditions.append(AppointmentCheckin.checkin_time <= end_date)

    if conditions:
        query = query.where(and_(*conditions))

    query = query.group_by(AppointmentCheckin.status)

    result = await db.execute(query)
    stats = result.all()

    return {
        "data": [
            {
                "status": row.status,
                "count": row.count
            }
            for row in stats
        ],
        "total": sum(row.count for row in stats)
    }


@router.get("/export", summary="导出审计日志")
async def export_audit_logs(
    format: str = Query("json", pattern="^(json|csv)$", description="导出格式: json / csv"),
    tenant_id: str | None = Query(None, description="租户ID（平台管理员可指定）"),
    event_type: str | None = Query(None, description="事件类型筛选"),
    start_date: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """导出审计日志（支持 JSON / CSV 格式）

    租户管理员导出本租户日志，平台管理员可指定 tenant_id。
    """
    import io
    import json as _json

    from fastapi import HTTPException

    from app.models.tenant_audit_log import TenantAuditLog

    # R1-19：确定租户范围（只认账号锚点，不回退请求上下文）
    tid = _resolve_audit_tenant(current_admin, tenant_id)
    if not current_admin.get("is_super_admin") and tenant_id and tenant_id != tid:
        raise HTTPException(status_code=403, detail="无权导出其他租户的审计日志")

    query = select(TenantAuditLog).where(TenantAuditLog.tenant_id == tid)

    if event_type:
        query = query.where(TenantAuditLog.event_type == event_type)
    if start_date:
        try:
            sd = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.where(TenantAuditLog.created_at >= sd)
        except ValueError:
            raise HTTPException(status_code=400, detail="开始日期格式错误")
    if end_date:
        try:
            ed = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.where(TenantAuditLog.created_at < ed)
        except ValueError:
            raise HTTPException(status_code=400, detail="结束日期格式错误")

    query = query.order_by(TenantAuditLog.created_at.desc()).limit(10000)
    result = await db.execute(query)
    logs = list(result.scalars().all())

    if format == "csv":
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "事件类型", "操作人", "资源类型", "资源ID", "操作", "创建时间", "变更前", "变更后"])
        for log in logs:
            writer.writerow([
                log.id,
                log.event_type,
                log.actor_name or log.actor_id or "",
                log.resource_type,
                log.resource_id,
                log.action,
                log.created_at.isoformat() if log.created_at else "",
                log.before_data or "",
                log.after_data or "",
            ])
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=audit_logs_{tid[:8]}.csv"},
        )

    # JSON 格式
    data = [
        {
            "id": log.id,
            "event_type": log.event_type,
            "actor_id": log.actor_id,
            "actor_name": log.actor_name,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "action": log.action,
            "before_data": _json.loads(log.before_data) if log.before_data else None,
            "after_data": _json.loads(log.after_data) if log.after_data else None,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
    content = _json.dumps(data, ensure_ascii=False, indent=2)
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=audit_logs_{tid[:8]}.json"},
    )
