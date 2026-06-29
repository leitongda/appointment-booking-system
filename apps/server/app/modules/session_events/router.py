"""
会话回放与热力图 API
- POST /batch: rrweb 录制事件批量上报（无需认证，提取可选 actor）
- GET /:       会话列表（按 session_id 聚合）
- GET /{session_id}/replay: 会话回放数据拼装（presigned eventsUrl）
- GET /heatmap: 热力图坐标聚合查询

风格对齐 app/modules/analytics/router.py：
- 内存级 IP 限流（_check_rate_limit / _get_client_ip / _parse_user_agent）
- get_optional_account 提取 actor；get_current_admin 守护管理端点
- Celery delay + try/except 回退直写
"""
import json
import logging
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.common.auth_unified import AccountInfo, get_optional_account
from app.core.config import settings
from app.infrastructure.storage import get_storage
from app.middleware.tenant_context import get_current_tenant_id
from app.models.session_event import HeatmapPoint, SessionEvent
from app.schemas.response import PageResponse
from app.schemas.session_event import (
    HeatmapPointItem,
    HeatmapQueryResponse,
    SessionBatchResponse,
    SessionEventBatchRequest,
    SessionListResponse,
    SessionReplayResponse,
    SessionSegmentResponse,
)
from app.utils.ip import get_client_ip

logger = logging.getLogger(__name__)

router = APIRouter()

# 视口分桶阈值（与 session_event_task 保持一致）
_VIEWPORT_LG_THRESHOLD = 1440
_VIEWPORT_SM_THRESHOLD = 768


def _bucket_for_viewport(width: int | None) -> str:
    """根据视口宽度返回分桶: lg(>1440)/md(768-1440)/sm(<768)"""
    if width is None:
        return "md"
    if width > _VIEWPORT_LG_THRESHOLD:
        return "lg"
    if width < _VIEWPORT_SM_THRESHOLD:
        return "sm"
    return "md"


# ========== 安全：IP 级速率限制（Redis 滑动窗口，多实例共享） ==========

_RATE_LIMIT_WINDOW = 60  # 秒
_RATE_LIMIT_MAX = 120    # 每窗口最大请求数
# 限流作用域，避免与 analytics 等其他高频接口共用配额
_RATE_LIMIT_SCOPE = "session_events_batch"


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


def _get_client_ip(request: Request) -> str:
    """获取客户端真实 IP（包装函数，保持向后兼容）"""
    return get_client_ip(request)


def _extract_actor(account: AccountInfo | None) -> tuple[str | None, str | None]:
    """从认证信息中提取 (actor_id, actor_name)"""
    if account is None:
        return None, None
    actor_id = getattr(account, "id", None)
    actor_name = getattr(account, "name", None)
    return (str(actor_id) if actor_id is not None else None), actor_name


def _detect_platform(request: Request) -> str:
    """根据 User-Agent 粗略推断上报平台（admin/h5/miniapp）"""
    ua = (request.headers.get("User-Agent", "") or "").lower()
    if "miniprogram" in ua or "micromessenger" in ua:
        return "miniapp"
    if "mobile" in ua or "android" in ua or "iphone" in ua:
        return "h5"
    return "admin"


# ========== 批量上报（无需认证） ==========

@router.post("/batch", response_model=SessionBatchResponse, summary="上报会话回放事件批次")
async def batch_upload_session_events(
    data: SessionEventBatchRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    account: AccountInfo | None = Depends(get_optional_account),
):
    """rrweb 录制事件批量上报。

    此接口不需要认证，允许匿名上报；提供 token 时自动提取 actor_id / actor_name。
    正常路径：Celery 异步落对象存储 + 写库 + 提取热力图坐标。
    回退路径：Celery 不可用时直接同步上传对象存储 + 写 SessionEvent 行
    （简化：回退路径跳过热力图坐标提取，避免阻塞请求）。
    """
    client_ip = _get_client_ip(request)
    await _check_rate_limit(client_ip)

    user_agent = request.headers.get("User-Agent", "")
    tenant_id = get_current_tenant_id()
    actor_id, actor_name = _extract_actor(account)
    platform = _detect_platform(request)

    event_count = len(data.events)
    segment_id = str(uuid.uuid4())

    batch_payload = {
        "segment_id": segment_id,
        "tenant_id": tenant_id,
        "actor_id": actor_id,
        "actor_name": actor_name,
        "ip": client_ip,
        "user_agent": user_agent[:500] if user_agent else None,
        "platform": platform,
        "session_id": data.session_id,
        "viewport_w": data.viewport_w,
        "viewport_h": data.viewport_h,
        "page_path": data.page_path,
        "sequence": data.sequence or 0,
        "started_at": data.started_at.isoformat() if data.started_at else None,
        "ended_at": data.ended_at.isoformat() if data.ended_at else None,
        "events": data.events,
    }

    # 异步保存：Celery delay
    try:
        from app.tasks.session_event_task import batch_save_session_events
        batch_save_session_events.delay(batch_payload)
        return SessionBatchResponse(success=True, count=event_count, segment_id=segment_id)
    except Exception as exc:
        logger.warning(f"Celery 会话事件任务发送失败，回退直写: {exc}")
        # 回退：直接同步上传对象存储 + 写 SessionEvent 行（跳过热力图）
        storage_url = None
        storage_key = None
        try:
            storage = get_storage()
            from app.tasks.session_event_task import _build_storage_key
            key = _build_storage_key()
            payload_bytes = json.dumps(data.events, ensure_ascii=False).encode("utf-8")
            upload_result = await storage.upload_bytes(payload_bytes, key, "application/json")
            storage_url = upload_result.url
            storage_key = upload_result.key
        except Exception as storage_exc:
            logger.error(f"回退路径对象存储上传失败: {storage_exc}")

        try:
            row = SessionEvent(
                id=segment_id,
                tenant_id=tenant_id,
                platform=platform,
                session_id=data.session_id,
                actor_id=actor_id,
                actor_name=actor_name,
                viewport_w=data.viewport_w,
                viewport_h=data.viewport_h,
                page_path=data.page_path,
                event_count=event_count,
                storage_url=storage_url,
                storage_key=storage_key,
                sequence=data.sequence or 0,
                started_at=data.started_at,
                ended_at=data.ended_at,
                ip=client_ip,
                user_agent=user_agent[:500] if user_agent else None,
            )
            db.add(row)
            await db.commit()
        except Exception as db_exc:
            await db.rollback()
            logger.error(f"回退路径 SessionEvent 写入失败: {db_exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="会话事件保存失败",
            ) from db_exc

        return SessionBatchResponse(success=True, count=event_count, segment_id=segment_id)


# ========== 会话列表（管理员） ==========

@router.get("", response_model=PageResponse[SessionListResponse], summary="获取会话列表")
async def list_sessions(
    platform: str | None = None,
    actor_id: str | None = Query(None, alias="actorId"),
    page_path: str | None = Query(None, alias="pagePath"),
    session_id: str | None = Query(None, alias="sessionId"),
    start_time: datetime | None = Query(None, alias="startTime"),
    end_time: datetime | None = Query(None, alias="endTime"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=settings.MAX_PAGE_SIZE, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """按 session_id 聚合的会话列表（每个 session 一行，event_count 求和）。

    取每个会话最新批次的代表信息（actor/page_path/viewport/created_at）。
    """
    tenant_id = get_current_tenant_id()

    conditions = []
    if tenant_id is not None:
        conditions.append(SessionEvent.tenant_id == tenant_id)
    if platform:
        conditions.append(SessionEvent.platform == platform)
    if actor_id:
        conditions.append(SessionEvent.actor_id == actor_id)
    if session_id:
        conditions.append(SessionEvent.session_id == session_id)
    if start_time:
        conditions.append(SessionEvent.created_at >= start_time)
    if end_time:
        conditions.append(SessionEvent.created_at <= end_time)
    if page_path:
        escaped = page_path.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        conditions.append(SessionEvent.page_path.ilike(f"%{escaped}%", escape="\\"))

    where_clause = and_(*conditions) if conditions else None

    # 去重会话总数
    count_stmt = select(func.count(func.distinct(SessionEvent.session_id)))
    if where_clause is not None:
        count_stmt = count_stmt.where(where_clause)
    total = await db.scalar(count_stmt) or 0

    # 用 row_number 取每个 session 的最新代表行（PostgreSQL）
    # 简化实现：先聚合得到 session_id 列表 + 聚合指标，再 join 取代表行字段。
    # 但为减少往返，这里用窗口函数一次性取出代表行。
    latest_id_subq = (
        select(
            SessionEvent.id.label("id"),
            SessionEvent.session_id.label("session_id"),
            func.row_number()
            .over(
                partition_by=SessionEvent.session_id,
                order_by=desc(SessionEvent.created_at),
            )
            .label("rn"),
        )
        .where(where_clause)
        .subquery()
    )

    # 聚合指标 + 代表行（rn=1）
    agg_subq = (
        select(
            SessionEvent.session_id.label("session_id"),
            func.sum(SessionEvent.event_count).label("event_count"),
            func.max(SessionEvent.sequence).label("sequence"),
            func.min(SessionEvent.started_at).label("started_at"),
            func.max(SessionEvent.ended_at).label("ended_at"),
            func.max(SessionEvent.created_at).label("created_at"),
        )
        .where(where_clause)
        .group_by(SessionEvent.session_id)
        .subquery()
    )

    stmt = (
        select(
            latest_id_subq.c.id.label("id"),
            latest_id_subq.c.session_id.label("session_id"),
            SessionEvent.actor_id.label("actor_id"),
            SessionEvent.actor_name.label("actor_name"),
            SessionEvent.page_path.label("page_path"),
            SessionEvent.viewport_w.label("viewport_w"),
            SessionEvent.viewport_h.label("viewport_h"),
            SessionEvent.platform.label("platform"),
            agg_subq.c.event_count.label("event_count"),
            agg_subq.c.sequence.label("sequence"),
            agg_subq.c.started_at.label("started_at"),
            agg_subq.c.ended_at.label("ended_at"),
            agg_subq.c.created_at.label("created_at"),
        )
        .select_from(latest_id_subq)
        .join(SessionEvent, SessionEvent.id == latest_id_subq.c.id)
        .join(agg_subq, agg_subq.c.session_id == latest_id_subq.c.session_id)
        .where(latest_id_subq.c.rn == 1)
        .order_by(desc(agg_subq.c.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(stmt)
    rows = result.all()
    items = [
        SessionListResponse(
            id=row.id,
            session_id=row.session_id,
            actor_id=row.actor_id,
            actor_name=row.actor_name,
            page_path=row.page_path,
            viewport_w=row.viewport_w,
            viewport_h=row.viewport_h,
            event_count=int(row.event_count or 0),
            sequence=int(row.sequence or 0),
            started_at=row.started_at,
            ended_at=row.ended_at,
            created_at=row.created_at,
        )
        for row in rows
    ]

    return PageResponse(
        data=items,
        total=int(total),
        page=page,
        page_size=page_size,
    )


# ========== 会话回放数据（管理员） ==========

@router.get(
    "/{session_id}/replay",
    response_model=SessionReplayResponse,
    summary="获取会话回放数据",
)
async def get_session_replay(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """返回该 session 所有批次段（按 sequence/created_at 排序）。

    前端按顺序拉取各 eventsUrl，拼接 events 数组后喂给 rrweb-player。
    viewport_w/H 取首段。storage_key 缺失的段（孤儿对象/清理中途）会被跳过，
    通过 missing_count 暴露给前端，避免返回 events_url=null 导致回放拼接失败。
    """
    tenant_id = get_current_tenant_id()

    conditions = [SessionEvent.session_id == session_id]
    if tenant_id is not None:
        conditions.append(SessionEvent.tenant_id == tenant_id)

    stmt = (
        select(SessionEvent)
        .where(and_(*conditions))
        .order_by(SessionEvent.sequence.asc(), SessionEvent.created_at.asc())
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在或无回放数据",
        )

    storage = get_storage()
    segments: list[SessionSegmentResponse] = []
    missing_count = 0
    for row in rows:
        # storage_key 缺失：对象存储文件不存在（孤儿/清理中/直写回退未存对象），
        # 跳过该段而非返回 null events_url，避免前端拼接出错。
        if not row.storage_key:
            missing_count += 1
            continue
        events_url: str | None = None
        try:
            events_url = await storage.get_url(row.storage_key, expires=3600)
        except Exception as exc:
            logger.warning(f"生成 eventsUrl 失败 segment={row.id}: {exc}")
            events_url = row.storage_url
        segments.append(
            SessionSegmentResponse(
                segment_id=row.id,
                sequence=row.sequence or 0,
                event_count=row.event_count or 0,
                events_url=events_url,
            )
        )

    if not segments:
        # 所有段都缺失数据：回放不可用
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话回放数据全部缺失（{missing_count} 段无对象存储引用）",
        )

    first = rows[0]
    return SessionReplayResponse(
        session_id=session_id,
        viewport_w=first.viewport_w,
        viewport_h=first.viewport_h,
        segments=segments,
        missing_count=missing_count,
    )


# ========== 热力图查询（管理员） ==========

@router.get("/heatmap", response_model=HeatmapQueryResponse, summary="热力图坐标聚合查询")
async def query_heatmap(
    page_path: str = Query(..., alias="pagePath", description="页面路径（必填）"),
    event_type: str = Query("click", alias="eventType", description="事件类型: click/move"),
    viewport_bucket: str | None = Query(None, alias="viewportBucket", description="视口分桶: lg/md/sm"),
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """按 page_path + eventType(+viewportBucket 可选) + 当前租户 + 近 N 天聚合 HeatmapPoint。

    返回 sum(weight)，按 (x_ratio, y_ratio) 分组的坐标点列表。
    """
    if event_type not in ("click", "move"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="eventType 仅支持 click 或 move",
        )
    if viewport_bucket is not None and viewport_bucket not in ("lg", "md", "sm"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="viewportBucket 仅支持 lg/md/sm",
        )

    tenant_id = get_current_tenant_id()
    cutoff_date = (datetime.utcnow() - timedelta(days=days)).date()

    conditions = [
        HeatmapPoint.page_path == page_path,
        HeatmapPoint.event_type == event_type,
        HeatmapPoint.day >= cutoff_date,
    ]
    if tenant_id is not None:
        conditions.append(HeatmapPoint.tenant_id == tenant_id)
    if viewport_bucket:
        conditions.append(HeatmapPoint.viewport_bucket == viewport_bucket)

    stmt = (
        select(
            HeatmapPoint.x_ratio.label("x_ratio"),
            HeatmapPoint.y_ratio.label("y_ratio"),
            func.sum(HeatmapPoint.weight).label("weight"),
        )
        .where(and_(*conditions))
        .group_by(HeatmapPoint.x_ratio, HeatmapPoint.y_ratio)
        .order_by(desc("weight"))
    )
    result = await db.execute(stmt)
    rows = result.all()

    points = [
        HeatmapPointItem(
            x_ratio=float(row.x_ratio),
            y_ratio=float(row.y_ratio),
            weight=int(row.weight or 0),
        )
        for row in rows
    ]

    return HeatmapQueryResponse(
        page_path=page_path,
        viewport_bucket=viewport_bucket,
        event_type=event_type,
        points=points,
    )
