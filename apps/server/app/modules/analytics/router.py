"""
用户行为分析 API
- 埋点数据上报
- 行为统计查询
"""
import json
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.common.auth_unified import AccountInfo, get_optional_account
from app.core.config import settings
from app.middleware.tenant_context import get_current_tenant_id
from app.models.behavior_log import UserBehaviorLog
from app.schemas.behavior_log import (
    BatchTrackRequest,
    BehaviorOverview,
    ClickStats,
    DailyStats,
    PageViewStats,
    SearchKeywordStats,
    TenantActivityDaily,
    TenantActivityStats,
    TrackEventRequest,
    UserBehaviorLogResponse,
)
from app.schemas.response import PageResponse
from app.utils.ip import get_client_ip

logger = logging.getLogger(__name__)

router = APIRouter()

# ========== 安全：IP 级速率限制（Redis 滑动窗口，多实例共享） ==========

_RATE_LIMIT_WINDOW = 60  # 秒
# 埋点批量上报高频，单 IP 每分钟放宽到 300 次（全局中间件已豁免此接口，由此处兜底防滥用）
_RATE_LIMIT_MAX = 300   # 每窗口最大请求数
# 限流作用域，避免与 session_events 等其他高频接口共用配额
_RATE_LIMIT_SCOPE = "analytics"


async def _check_rate_limit(client_ip: str) -> None:
    """基于 Redis 滑动窗口的 IP 速率限制（多实例共享，全局生效）。

    迁移自进程内内存 dict：内存版在多 worker/多实例下各计数独立，
    实际限流阈值被放大 N 倍，无法有效防滥用。改为复用 RateLimitMiddleware
    的 Redis 滑窗逻辑，所有实例共享同一计数。Redis 不可用时 fail-open 放行。
    """
    from app.core.redis import get_redis
    from app.middleware.rate_limit import RateLimitMiddleware

    redis = await get_redis()
    allowed = await RateLimitMiddleware.check_ip_rate_limit(
        redis, client_ip, _RATE_LIMIT_SCOPE, _RATE_LIMIT_MAX, _RATE_LIMIT_WINDOW
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后再试",
        )


def _extract_user_id(account: AccountInfo | None) -> str | None:
    """从认证信息中提取 user_id"""
    if account is None:
        return None
    return getattr(account, "id", None)


def _get_client_ip(request: Request) -> str:
    """获取客户端真实 IP（包装函数，保持向后兼容）"""
    return get_client_ip(request)


def _parse_user_agent(user_agent: str) -> dict:
    """解析 User-Agent 获取设备信息"""
    result = {
        "device_type": "desktop",
        "browser": None,
        "os": None,
    }
    
    if not user_agent:
        return result
    
    ua_lower = user_agent.lower()
    
    # 判断设备类型
    if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
        result["device_type"] = "mobile"
    elif "ipad" in ua_lower or "tablet" in ua_lower:
        result["device_type"] = "tablet"
    
    # 判断浏览器
    if "chrome" in ua_lower and "edge" not in ua_lower:
        result["browser"] = "Chrome"
    elif "firefox" in ua_lower:
        result["browser"] = "Firefox"
    elif "safari" in ua_lower and "chrome" not in ua_lower:
        result["browser"] = "Safari"
    elif "edge" in ua_lower:
        result["browser"] = "Edge"
    elif "opera" in ua_lower:
        result["browser"] = "Opera"
    elif "micromessenger" in ua_lower:
        result["browser"] = "WeChat"
    
    # 判断操作系统
    if "windows" in ua_lower:
        result["os"] = "Windows"
    elif "mac os" in ua_lower or "macos" in ua_lower:
        result["os"] = "macOS"
    elif "linux" in ua_lower and "android" not in ua_lower:
        result["os"] = "Linux"
    elif "android" in ua_lower:
        result["os"] = "Android"
    elif "iphone" in ua_lower or "ipad" in ua_lower or "ios" in ua_lower:
        result["os"] = "iOS"
    
    return result


# ========== 埋点数据上报（无需认证） ==========

@router.post("/track", summary="上报埋点")
async def track_event(
    data: TrackEventRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    account: AccountInfo | None = Depends(get_optional_account),
):
    """
    单条埋点数据上报
    此接口不需要认证，允许匿名用户上报；提供 token 时自动提取 user_id
    """
    client_ip = _get_client_ip(request)
    await _check_rate_limit(client_ip)

    user_agent = request.headers.get("User-Agent", "")
    ua_info = _parse_user_agent(user_agent)
    tenant_id = get_current_tenant_id()

    log_data = {
        "platform": data.platform.value,
        "user_id": _extract_user_id(account),
        "tenant_id": tenant_id,
        "session_id": data.session_id,
        "event_type": data.event_type.value,
        "page_path": data.page_path,
        "page_title": data.page_title,
        "element_id": data.element_id,
        "element_text": data.element_text,
        "search_keyword": data.search_keyword,
        "event_name": data.event_name,
        "duration": data.duration,
        "referrer": data.referrer,
        "extra_data": data.extra_data,
        "ip": client_ip,
        "user_agent": user_agent[:500] if user_agent else None,
        "device_type": ua_info["device_type"],
        "browser": ua_info["browser"],
        "os": ua_info["os"],
    }

    # 异步保存到数据库
    try:
        from app.tasks.behavior_log_task import save_behavior_log
        save_behavior_log.delay(log_data)
    except Exception as e:
        logger.warning(f"Celery 任务发送失败，直接写入: {e}")
        import uuid
        log = UserBehaviorLog(
            id=str(uuid.uuid4()),
            **{k: (json.dumps(v, ensure_ascii=False) if k == "extra_data" and isinstance(v, dict) else v) for k, v in log_data.items()}
        )
        db.add(log)
        await db.commit()

    return {"success": True}


@router.post("/batch", summary="批量上报")
async def batch_track_events(
    data: BatchTrackRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    account: AccountInfo | None = Depends(get_optional_account),
):
    """
    批量埋点数据上报
    此接口不需要认证，允许匿名用户上报；提供 token 时自动提取 user_id
    """
    client_ip = _get_client_ip(request)
    await _check_rate_limit(client_ip)

    user_agent = request.headers.get("User-Agent", "")
    ua_info = _parse_user_agent(user_agent)
    user_id = _extract_user_id(account)
    tenant_id = get_current_tenant_id()

    logs_data = []
    for event in data.events:
        log_data = {
            "platform": event.platform.value,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "session_id": event.session_id,
            "event_type": event.event_type.value,
            "page_path": event.page_path,
            "page_title": event.page_title,
            "element_id": event.element_id,
            "element_text": event.element_text,
            "search_keyword": event.search_keyword,
            "event_name": event.event_name,
            "duration": event.duration,
            "referrer": event.referrer,
            "extra_data": event.extra_data,
            "ip": client_ip,
            "user_agent": user_agent[:500] if user_agent else None,
            "device_type": ua_info["device_type"],
            "browser": ua_info["browser"],
            "os": ua_info["os"],
        }
        logs_data.append(log_data)

    # 批量异步保存
    try:
        from app.tasks.behavior_log_task import batch_save_behavior_logs
        batch_save_behavior_logs.delay(logs_data)
    except Exception as e:
        logger.warning(f"Celery 批量任务发送失败，直接写入: {e}")
        import uuid
        logs = [
            UserBehaviorLog(
                id=str(uuid.uuid4()),
                **{k: (json.dumps(v, ensure_ascii=False) if k == "extra_data" and isinstance(v, dict) else v) for k, v in log_data.items()}
            )
            for log_data in logs_data
        ]
        db.add_all(logs)
        await db.commit()

    return {"success": True, "count": len(logs_data)}


# ========== 行为统计查询（需要管理员认证） ==========

@router.get("/logs", response_model=PageResponse[UserBehaviorLogResponse], summary="获取日志列表")
async def get_behavior_logs(
    platform: str | None = None,
    event_type: str | None = None,
    page_path: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取用户行为日志列表（管理员）"""
    query = select(UserBehaviorLog)
    conditions = []
    
    if platform:
        conditions.append(UserBehaviorLog.platform == platform)
    if event_type:
        conditions.append(UserBehaviorLog.event_type == event_type)
    if page_path:
        escaped = page_path.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        conditions.append(UserBehaviorLog.page_path.ilike(f"%{escaped}%", escape="\\"))
    if start_time:
        conditions.append(UserBehaviorLog.created_at >= start_time)
    if end_time:
        conditions.append(UserBehaviorLog.created_at <= end_time)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # 统计总数
    count_query = select(func.count(UserBehaviorLog.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = await db.scalar(count_query)
    
    # 分页查询
    query = query.order_by(desc(UserBehaviorLog.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    return PageResponse(
        data=[UserBehaviorLogResponse.model_validate(item) for item in items],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/overview", summary="获取概览统计")
async def get_behavior_overview(
    platform: str | None = None,
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取用户行为概览统计（管理员）"""
    start_date = datetime.now() - timedelta(days=days)
    
    base_conditions = [UserBehaviorLog.created_at >= start_date]
    if platform:
        base_conditions.append(UserBehaviorLog.platform == platform)
    
    # 总页面访问量
    pv_count = await db.scalar(
        select(func.count(UserBehaviorLog.id))
        .where(and_(*base_conditions, UserBehaviorLog.event_type == "page_view"))
    )
    
    # 独立用户数（基于 session_id）
    uv_count = await db.scalar(
        select(func.count(func.distinct(UserBehaviorLog.session_id)))
        .where(and_(*base_conditions))
    )
    
    # 总点击数
    click_count = await db.scalar(
        select(func.count(UserBehaviorLog.id))
        .where(and_(*base_conditions, UserBehaviorLog.event_type == "click"))
    )
    
    # 总搜索数
    search_count = await db.scalar(
        select(func.count(UserBehaviorLog.id))
        .where(and_(*base_conditions, UserBehaviorLog.event_type == "search"))
    )
    
    # 平均停留时长
    avg_duration = await db.scalar(
        select(func.avg(UserBehaviorLog.duration))
        .where(and_(
            *base_conditions,
            UserBehaviorLog.event_type == "page_leave",
            UserBehaviorLog.duration.isnot(None)
        ))
    )
    
    # Top 10 页面访问
    top_pages_result = await db.execute(
        select(
            UserBehaviorLog.page_path,
            UserBehaviorLog.page_title,
            func.count(UserBehaviorLog.id).label("view_count"),
            func.count(func.distinct(UserBehaviorLog.session_id)).label("unique_users")
        )
        .where(and_(*base_conditions, UserBehaviorLog.event_type == "page_view"))
        .group_by(UserBehaviorLog.page_path, UserBehaviorLog.page_title)
        .order_by(desc("view_count"))
        .limit(10)
    )
    top_pages = [
        PageViewStats(
            page_path=row.page_path or "",
            page_title=row.page_title,
            view_count=row.view_count,
            unique_users=row.unique_users
        )
        for row in top_pages_result.all()
    ]
    
    # Top 10 点击元素
    top_clicks_result = await db.execute(
        select(
            UserBehaviorLog.element_id,
            UserBehaviorLog.element_text,
            UserBehaviorLog.page_path,
            func.count(UserBehaviorLog.id).label("click_count")
        )
        .where(and_(*base_conditions, UserBehaviorLog.event_type == "click"))
        .group_by(UserBehaviorLog.element_id, UserBehaviorLog.element_text, UserBehaviorLog.page_path)
        .order_by(desc("click_count"))
        .limit(10)
    )
    top_clicks = [
        ClickStats(
            element_id=row.element_id,
            element_text=row.element_text,
            page_path=row.page_path,
            click_count=row.click_count
        )
        for row in top_clicks_result.all()
    ]
    
    # Top 10 搜索关键词
    top_keywords_result = await db.execute(
        select(
            UserBehaviorLog.search_keyword,
            func.count(UserBehaviorLog.id).label("search_count")
        )
        .where(and_(
            *base_conditions,
            UserBehaviorLog.event_type == "search",
            UserBehaviorLog.search_keyword.isnot(None)
        ))
        .group_by(UserBehaviorLog.search_keyword)
        .order_by(desc("search_count"))
        .limit(10)
    )
    top_keywords = [
        SearchKeywordStats(
            keyword=row.search_keyword or "",
            search_count=row.search_count
        )
        for row in top_keywords_result.all()
    ]
    
    # 每日统计（优化：2 条 SQL 替代 4*N 条）
    start_date_only = (datetime.now() - timedelta(days=days - 1)).date()
    date_start_boundary = datetime.combine(start_date_only, datetime.min.time())

    # 查询 1：按日期+事件类型聚合 PV/点击/搜索
    daily_event_rows = await db.execute(
        select(
            func.date(UserBehaviorLog.created_at).label("d"),
            UserBehaviorLog.event_type,
            func.count(UserBehaviorLog.id).label("cnt"),
        )
        .where(and_(*base_conditions, UserBehaviorLog.created_at >= date_start_boundary))
        .group_by(func.date(UserBehaviorLog.created_at), UserBehaviorLog.event_type)
    )

    # 查询 2：按日期聚合独立用户数
    daily_uv_rows = await db.execute(
        select(
            func.date(UserBehaviorLog.created_at).label("d"),
            func.count(func.distinct(UserBehaviorLog.session_id)).label("uv"),
        )
        .where(and_(*base_conditions, UserBehaviorLog.created_at >= date_start_boundary))
        .group_by(func.date(UserBehaviorLog.created_at))
    )

    # 组装日期索引
    daily_event_map: dict[tuple[str, str], int] = {}
    for row in daily_event_rows.all():
        d = str(row.d) if row.d else ""
        daily_event_map[(d, row.event_type)] = row.cnt

    daily_uv_map: dict[str, int] = {}
    for row in daily_uv_rows.all():
        d = str(row.d) if row.d else ""
        daily_uv_map[d] = row.uv

    daily_stats = []
    for i in range(days - 1, -1, -1):
        date = datetime.now().date() - timedelta(days=i)
        d = date.isoformat()
        daily_stats.append(DailyStats(
            date=d,
            page_views=daily_event_map.get((d, "page_view"), 0),
            unique_users=daily_uv_map.get(d, 0),
            clicks=daily_event_map.get((d, "click"), 0),
            searches=daily_event_map.get((d, "search"), 0),
        ))
    
    return BehaviorOverview(
        total_page_views=pv_count or 0,
        total_unique_users=uv_count or 0,
        total_clicks=click_count or 0,
        total_searches=search_count or 0,
        avg_duration=float(avg_duration) if avg_duration else None,
        top_pages=top_pages,
        top_clicks=top_clicks,
        top_keywords=top_keywords,
        daily_stats=daily_stats
    )


@router.get("/tenant-activity", response_model=TenantActivityStats, summary="租户活跃度统计")
async def get_tenant_activity_stats(
    days: int = Query(30, ge=1, le=90, description="统计天数"),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取租户活跃度统计（DAU/WAU/MAU）"""
    tenant_id = get_current_tenant_id()

    # 构建基础条件
    base_conditions = []
    if tenant_id:
        base_conditions.append(UserBehaviorLog.tenant_id == tenant_id)

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days - 1)

    # 每日统计（优化：2 条 SQL 替代 3*N 条）
    date_start_boundary = datetime.combine(start_date, datetime.min.time())

    # 查询 1：按日期聚合 DAU + 会话数
    daily_rows = await db.execute(
        select(
            func.date(UserBehaviorLog.created_at).label("d"),
            func.count(
                func.distinct(
                    case(
                        (UserBehaviorLog.user_id.isnot(None), UserBehaviorLog.user_id),
                    )
                )
            ).label("dau"),
            func.count(func.distinct(UserBehaviorLog.session_id)).label("total_sessions"),
        )
        .where(and_(*base_conditions, UserBehaviorLog.created_at >= date_start_boundary))
        .group_by(func.date(UserBehaviorLog.created_at))
    )

    daily_map: dict[str, tuple[int, int]] = {}
    for row in daily_rows.all():
        d = str(row.d) if row.d else ""
        daily_map[d] = (row.dau, row.total_sessions)

    # 查询 2：获取所有有记录的 user_id 及其首次出现日期（用于计算新用户）
    first_seen_rows = await db.execute(
        select(
            UserBehaviorLog.user_id,
            func.min(func.date(UserBehaviorLog.created_at)).label("first_date"),
        )
        .where(and_(
            *base_conditions,
            UserBehaviorLog.user_id.isnot(None),
            UserBehaviorLog.created_at >= date_start_boundary,
        ))
        .group_by(UserBehaviorLog.user_id)
    )

    new_users_map: dict[str, int] = {}
    for row in first_seen_rows.all():
        d = str(row.first_date) if row.first_date else ""
        new_users_map[d] = new_users_map.get(d, 0) + 1

    daily_stats = []
    for i in range(days - 1, -1, -1):
        current_date = end_date - timedelta(days=i)
        d = current_date.isoformat()
        dau, total_sessions = daily_map.get(d, (0, 0))
        daily_stats.append(TenantActivityDaily(
            date=d,
            dau=dau,
            total_sessions=total_sessions,
            new_users=new_users_map.get(d, 0),
        ))

    # 计算当前 DAU/WAU/MAU
    today_start = datetime.combine(end_date, datetime.min.time())
    today_end = datetime.combine(end_date, datetime.max.time())
    week_start = datetime.combine(end_date - timedelta(days=6), datetime.min.time())
    month_start = datetime.combine(end_date - timedelta(days=29), datetime.min.time())

    current_dau = await db.scalar(
        select(func.count(func.distinct(UserBehaviorLog.user_id)))
        .where(
            and_(
                *base_conditions,
                UserBehaviorLog.created_at >= today_start,
                UserBehaviorLog.created_at <= today_end,
                UserBehaviorLog.user_id.isnot(None),
            )
        )
    ) or 0

    current_wau = await db.scalar(
        select(func.count(func.distinct(UserBehaviorLog.user_id)))
        .where(
            and_(
                *base_conditions,
                UserBehaviorLog.created_at >= week_start,
                UserBehaviorLog.created_at <= today_end,
                UserBehaviorLog.user_id.isnot(None),
            )
        )
    ) or 0

    current_mau = await db.scalar(
        select(func.count(func.distinct(UserBehaviorLog.user_id)))
        .where(
            and_(
                *base_conditions,
                UserBehaviorLog.created_at >= month_start,
                UserBehaviorLog.created_at <= today_end,
                UserBehaviorLog.user_id.isnot(None),
            )
        )
    ) or 0

    return TenantActivityStats(
        tenant_id=tenant_id,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        current_dau=current_dau,
        current_wau=current_wau,
        current_mau=current_mau,
        daily_stats=daily_stats,
    )

