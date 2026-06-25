"""Admin logs and online status router."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_admin
from app.common.deps import require_permission
from app.core.config import settings
from app.core.redis import RedisCache
from app.db.session import get_db
from app.models.admin import Admin, AdminLoginHistory
from app.modules.admin.schemas import (
    AccountStatsDetail,
    AccountStatsResponse,
    AccountStatsSummary,
    DeviceDistribution,
    HourlyDistribution,
    LoginHistoryResponse,
    OnlineUserResponse,
    OperationLogResponse,
    UserStatusResponse,
)
from app.modules.admin.service_logs import OperationLogService
from app.schemas.response import PageResponse

router = APIRouter()


@router.get("/logs", response_model=PageResponse[OperationLogResponse], summary="获取操作日志")
async def get_operation_logs(
    admin_id: str | None = None,
    module: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("system:log", "log:list")),
):
    service = OperationLogService(db)
    tenant_id = None if current_admin.get("is_super_admin") else current_admin.get("tenant_id")
    items, total = await service.get_list(
        admin_id=admin_id,
        module=module,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
        tenant_id=tenant_id,
    )
    return PageResponse(
        data=[OperationLogResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/online-users", summary="获取在线用户")
async def get_online_users(
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("system:log", "log:list")),
):
    # 非超管仅查看当前租户的在线用户，超管可查看全部
    tenant_id = None if current_admin.get("is_super_admin") else current_admin.get("tenant_id")
    sessions = await RedisCache.get_all_admin_sessions(tenant_id=tenant_id)
    return [
        OnlineUserResponse(
            admin_id=session.get("admin_id", ""),
            username=session.get("username", ""),
            name=session.get("name"),
            role_name=session.get("role_name"),
            login_time=session.get("login_time", ""),
            login_ip=session.get("login_ip", ""),
            user_agent=session.get("user_agent", ""),
            device_info=session.get("device_info", {}),
            ttl=session.get("ttl", 0),
        ).model_dump(by_alias=True)
        for session in sessions
    ]


@router.post("/online-users/{admin_id}/kick", summary="强制用户下线")
async def kick_online_user(
    admin_id: str,
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("system:log", "log:list")),
):
    if not current_admin.get("is_super_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要超级管理员权限")
    if admin_id == current_admin.get("id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能强制自己下线")

    # 获取被踢管理员的租户ID，用于构建租户隔离的 Redis 键
    result = await db.execute(select(Admin).where(Admin.id == admin_id))
    target_admin = result.scalar_one_or_none()
    target_tenant_id = target_admin.tenant_id if target_admin else None

    session = await RedisCache.get_admin_session(admin_id, tenant_id=target_tenant_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不在线，无法执行此操作")

    login_history_id = session.get("login_history_id")
    login_time_str = session.get("login_time")
    if login_history_id:
        result = await db.execute(select(AdminLoginHistory).where(AdminLoginHistory.id == login_history_id))
        login_history = result.scalar_one_or_none()
        if login_history:
            logout_time = datetime.utcnow()
            login_history.logout_time = logout_time
            login_history.logout_type = "kicked"
            if login_time_str:
                try:
                    login_time = datetime.fromisoformat(login_time_str)
                    login_history.duration = int((logout_time - login_time).total_seconds())
                except Exception:
                    pass
            await db.commit()

    token_hash = session.get("token_hash")
    session_key = RedisCache._build_admin_session_key(admin_id, tenant_id=target_tenant_id)
    ttl = await RedisCache.ttl(session_key)
    if token_hash and ttl > 0:
        await RedisCache.add_token_to_blacklist(token_hash, ttl, tenant_id=target_tenant_id)
    await RedisCache.delete_admin_session(admin_id, tenant_id=target_tenant_id)
    return {"message": "用户已强制下线"}


@router.get("/user-status", summary="获取用户状态")
async def get_user_status(
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("system:log", "log:list")),
):
    # 非超管仅查看当前租户的在线用户，超管可查看全部
    tenant_id = None if current_admin.get("is_super_admin") else current_admin.get("tenant_id")
    sessions = await RedisCache.get_all_admin_sessions(tenant_id=tenant_id)
    online_admin_ids = {s.get("admin_id") for s in sessions}
    session_map = {s.get("admin_id"): s for s in sessions}

    admin_query = select(Admin).options(selectinload(Admin.role)).where(Admin.status == 1)
    if tenant_id:
        admin_query = admin_query.where(Admin.tenant_id == tenant_id)
    admin_query = admin_query.order_by(Admin.created_at.desc())
    result = await db.execute(admin_query)
    admins = result.scalars().all()

    user_status_list = []
    for admin in admins:
        if admin.id in online_admin_ids:
            session = session_map[admin.id]
            user_status_list.append(
                UserStatusResponse(
                    admin_id=admin.id,
                    username=admin.username,
                    name=admin.name,
                    role_name=admin.role.name if admin.role else None,
                    status="online",
                    login_time=session.get("login_time"),
                    login_ip=session.get("login_ip"),
                    device_info=session.get("device_info"),
                    ttl=session.get("ttl", 0),
                    last_login_at=None,
                    last_login_ip=None,
                ).model_dump(by_alias=True)
            )
        else:
            user_status_list.append(
                UserStatusResponse(
                    admin_id=admin.id,
                    username=admin.username,
                    name=admin.name,
                    role_name=admin.role.name if admin.role else None,
                    status="offline",
                    login_time=None,
                    login_ip=None,
                    device_info=None,
                    ttl=None,
                    last_login_at=admin.last_login_at.isoformat() if admin.last_login_at else None,
                    last_login_ip=admin.last_login_ip,
                ).model_dump(by_alias=True)
            )
    return user_status_list


@router.get("/login-history/{admin_id}", summary="获取登录历史")
async def get_login_history(
    admin_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=settings.MAX_PAGE_SIZE),
    start_time: datetime | None = Query(None, description="开始时间"),
    end_time: datetime | None = Query(None, description="结束时间"),
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("system:log", "log:list")),
):
    target_admin_result = await db.execute(select(Admin).where(Admin.id == admin_id))
    target_admin = target_admin_result.scalar_one_or_none()
    if not target_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在，请检查后重试")

    if (
        not current_admin.get("is_super_admin")
        and target_admin.tenant_id != current_admin.get("tenant_id")
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权查看该用户的登录历史")

    conditions = [AdminLoginHistory.admin_id == admin_id]
    if start_time:
        conditions.append(AdminLoginHistory.login_time >= start_time)
    if end_time:
        conditions.append(AdminLoginHistory.login_time <= end_time)

    count_stmt = select(func.count(AdminLoginHistory.id)).where(*conditions)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    stmt = (
        select(AdminLoginHistory)
        .where(*conditions)
        .order_by(AdminLoginHistory.login_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    history_list = [
        LoginHistoryResponse(
            id=record.id,
            login_time=record.login_time.isoformat() if record.login_time else "",
            logout_time=record.logout_time.isoformat() if record.logout_time else None,
            logout_type=record.logout_type,
            login_ip=record.login_ip,
            browser=record.browser,
            os=record.os,
            device_type=record.device_type,
            duration=record.duration,
        ).model_dump(by_alias=True)
        for record in records
    ]
    return {"list": history_list, "total": total, "page": page, "pageSize": page_size}


def _build_account_stats_conditions(
    tenant_id: str | None,
    start_date: str | None,
    end_date: str | None,
    admin_id: str | None,
):
    """构建账号统计通用查询条件。"""
    conditions = []
    if tenant_id:
        conditions.append(Admin.tenant_id == tenant_id)
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        conditions.append(AdminLoginHistory.login_time >= start_dt)
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        conditions.append(AdminLoginHistory.login_time < end_dt)
    if admin_id:
        conditions.append(AdminLoginHistory.admin_id == admin_id)
    return conditions


@router.get("/account-stats/summary", summary="账号使用统计概览")
async def get_account_stats_summary(
    start_date: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    admin_id: str | None = Query(None, description="指定账号ID"),
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("system:log", "log:list")),
):
    """返回账号使用统计概览 + 设备/浏览器/时段分布 + 每日趋势。"""
    tenant_id = None if current_admin.get("is_super_admin") else current_admin.get("tenant_id")
    conditions = _build_account_stats_conditions(tenant_id, start_date, end_date, admin_id)

    # 基础 JOIN：AdminLoginHistory -> Admin
    base_join = select(AdminLoginHistory).join(Admin, AdminLoginHistory.admin_id == Admin.id)
    if conditions:
        base_join = base_join.where(*conditions)

    # --- 概览聚合 ---
    agg_stmt = select(
        func.count(AdminLoginHistory.id).label("total_logins"),
        func.count(func.distinct(AdminLoginHistory.admin_id)).label("active_accounts"),
        func.coalesce(func.avg(AdminLoginHistory.duration), 0).label("avg_duration"),
        func.coalesce(func.sum(AdminLoginHistory.duration), 0).label("total_duration"),
    ).select_from(AdminLoginHistory.__table__.join(Admin.__table__, AdminLoginHistory.admin_id == Admin.id))
    if conditions:
        agg_stmt = agg_stmt.where(*conditions)

    agg_result = await db.execute(agg_stmt)
    row = agg_result.one()
    summary = AccountStatsSummary(
        total_logins=row.total_logins or 0,
        active_accounts=row.active_accounts or 0,
        avg_duration_minutes=round((row.avg_duration or 0) / 60, 2),
        total_duration_hours=round((row.total_duration or 0) / 3600, 2),
    )

    # --- 设备分布 ---
    device_stmt = (
        select(
            AdminLoginHistory.device_type,
            func.count(AdminLoginHistory.id).label("count"),
        )
        .select_from(AdminLoginHistory.__table__.join(Admin.__table__, AdminLoginHistory.admin_id == Admin.id))
        .group_by(AdminLoginHistory.device_type)
    )
    if conditions:
        device_stmt = device_stmt.where(*conditions)

    device_result = await db.execute(device_stmt)
    device_rows = device_result.all()
    total_for_pct = sum(r.count for r in device_rows) or 1
    device_distribution = [
        DeviceDistribution(
            device_type=r.device_type or "unknown",
            count=r.count,
            percentage=round(r.count / total_for_pct * 100, 2),
        )
        for r in device_rows
    ]

    # --- 浏览器分布 ---
    browser_stmt = (
        select(
            AdminLoginHistory.browser,
            func.count(AdminLoginHistory.id).label("count"),
        )
        .select_from(AdminLoginHistory.__table__.join(Admin.__table__, AdminLoginHistory.admin_id == Admin.id))
        .group_by(AdminLoginHistory.browser)
    )
    if conditions:
        browser_stmt = browser_stmt.where(*conditions)

    browser_result = await db.execute(browser_stmt)
    browser_rows = browser_result.all()
    total_for_pct_b = sum(r.count for r in browser_rows) or 1
    browser_distribution = [
        DeviceDistribution(
            device_type=r.browser or "unknown",
            count=r.count,
            percentage=round(r.count / total_for_pct_b * 100, 2),
        )
        for r in browser_rows
    ]

    # --- 时段分布 ---
    hourly_stmt = (
        select(
            func.extract("hour", AdminLoginHistory.login_time).label("hour"),
            func.count(AdminLoginHistory.id).label("count"),
        )
        .select_from(AdminLoginHistory.__table__.join(Admin.__table__, AdminLoginHistory.admin_id == Admin.id))
        .group_by(func.extract("hour", AdminLoginHistory.login_time))
        .order_by(func.extract("hour", AdminLoginHistory.login_time))
    )
    if conditions:
        hourly_stmt = hourly_stmt.where(*conditions)

    hourly_result = await db.execute(hourly_stmt)
    hourly_distribution = [
        HourlyDistribution(hour=int(r.hour), count=r.count) for r in hourly_result.all()
    ]

    # --- 每日趋势 ---
    daily_stmt = (
        select(
            func.date(AdminLoginHistory.login_time).label("date"),
            func.count(AdminLoginHistory.id).label("count"),
        )
        .select_from(AdminLoginHistory.__table__.join(Admin.__table__, AdminLoginHistory.admin_id == Admin.id))
        .group_by(func.date(AdminLoginHistory.login_time))
        .order_by(func.date(AdminLoginHistory.login_time))
    )
    if conditions:
        daily_stmt = daily_stmt.where(*conditions)

    daily_result = await db.execute(daily_stmt)
    daily_trend = [{"date": str(r.date), "count": r.count} for r in daily_result.all()]

    return AccountStatsResponse(
        summary=summary,
        device_distribution=device_distribution,
        browser_distribution=browser_distribution,
        hourly_distribution=hourly_distribution,
        daily_trend=daily_trend,
    ).model_dump(by_alias=True)


@router.get("/account-stats/details", summary="账号使用统计明细")
async def get_account_stats_details(
    start_date: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("system:log", "log:list")),
):
    """返回每个账号的使用统计明细，支持分页。"""
    tenant_id = None if current_admin.get("is_super_admin") else current_admin.get("tenant_id")

    # 构建时间条件（不含 admin_id，明细按账号分组）
    time_conditions = []
    if tenant_id:
        time_conditions.append(Admin.tenant_id == tenant_id)
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        time_conditions.append(AdminLoginHistory.login_time >= start_dt)
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        time_conditions.append(AdminLoginHistory.login_time < end_dt)

    # 子查询：每个账号的聚合统计
    stats_subq = (
        select(
            AdminLoginHistory.admin_id.label("admin_id"),
            func.count(AdminLoginHistory.id).label("login_count"),
            func.sum(AdminLoginHistory.duration).label("total_duration"),
            func.max(AdminLoginHistory.login_time).label("last_login_at"),
            func.mode().within_group(AdminLoginHistory.device_type).label("primary_device"),
            func.mode().within_group(AdminLoginHistory.browser).label("primary_browser"),
        )
        .select_from(AdminLoginHistory.__table__.join(Admin.__table__, AdminLoginHistory.admin_id == Admin.id))
        .group_by(AdminLoginHistory.admin_id)
    )
    if time_conditions:
        stats_subq = stats_subq.where(*time_conditions)

    stats_subq = stats_subq.subquery()

    # 总数
    count_stmt = select(func.count()).select_from(stats_subq)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # 主查询：JOIN Admin 获取账号信息
    stmt = (
        select(
            stats_subq.c.admin_id,
            Admin.username,
            Admin.name,
            stats_subq.c.login_count,
            stats_subq.c.total_duration,
            stats_subq.c.last_login_at,
            stats_subq.c.primary_device,
            stats_subq.c.primary_browser,
        )
        .join(Admin, Admin.id == stats_subq.c.admin_id)
        .order_by(stats_subq.c.login_count.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    rows = result.all()

    # 获取最后登录 IP（从 login_history 中取最近一条）
    admin_ids = [r.admin_id for r in rows]
    details = []
    if admin_ids:
        # 取每个账号最近一条记录的 login_ip
        last_login_ip_subq = (
            select(
                AdminLoginHistory.admin_id,
                AdminLoginHistory.login_ip,
                func.row_number()
                .over(
                    partition_by=AdminLoginHistory.admin_id,
                    order_by=AdminLoginHistory.login_time.desc(),
                )
                .label("rn"),
            )
            .where(AdminLoginHistory.admin_id.in_(admin_ids))
        ).subquery()

        ip_stmt = select(
            last_login_ip_subq.c.admin_id,
            last_login_ip_subq.c.login_ip,
        ).where(last_login_ip_subq.c.rn == 1)

        ip_result = await db.execute(ip_stmt)
        ip_map = {r.admin_id: r.login_ip for r in ip_result.all()}

        # 获取角色名（JOIN Admin 的 role 关系）
        admin_map = {}
        if admin_ids:
            admin_q = select(Admin).options(selectinload(Admin.role)).where(Admin.id.in_(admin_ids))
            admin_res = await db.execute(admin_q)
            for a in admin_res.scalars().all():
                admin_map[a.id] = a

        for r in rows:
            admin_obj = admin_map.get(r.admin_id)
            details.append(
                AccountStatsDetail(
                    admin_id=r.admin_id,
                    username=r.username,
                    name=r.name,
                    role_name=admin_obj.role.name if admin_obj and admin_obj.role else None,
                    login_count=r.login_count,
                    total_duration_seconds=int(r.total_duration) if r.total_duration else None,
                    last_login_at=r.last_login_at.isoformat() if r.last_login_at else None,
                    last_login_ip=ip_map.get(r.admin_id),
                    primary_device=r.primary_device,
                    primary_browser=r.primary_browser,
                ).model_dump(by_alias=True)
            )

    return PageResponse(
        data=details,
        total=total,
        page=page,
        page_size=page_size,
    )
