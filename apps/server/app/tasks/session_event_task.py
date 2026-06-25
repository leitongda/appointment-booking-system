"""
会话回放与热力图相关任务
- 批量保存 rrweb 录制事件段（对象存储 + DB 索引）
- 提取热力图坐标并 upsert 聚合
- 定时清理过期会话事件 / 热力图数据
"""
import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.celery_app import celery_app
from app.db.session import get_sync_db
from app.infrastructure.storage import get_storage
from app.models.session_event import HeatmapPoint, SessionEvent

logger = logging.getLogger(__name__)

# 数据保留天数（清理任务默认参数）
SESSION_EVENT_RETENTION_DAYS = 30
HEATMAP_RETENTION_DAYS = 180

# mousemove 数据量大，按固定步长采样后再 upsert，避免每次移动都写库
_MOUSEMOVE_SAMPLE_STEP = 5

# rrweb 增量事件 type
_RRWEB_INCREMENTAL_SNAPSHOT = 2
# rrweb data.source
_SOURCE_MOUSE_MOVE = 2
_SOURCE_MOUSE_INTERACTION = 1
# 视为 click 的 MouseInteraction type
_CLICK_INTERACTIONS = {"click", "dblclick", "touchstart"}

# 视口分桶阈值
_VIEWPORT_LG_THRESHOLD = 1440
_VIEWPORT_SM_THRESHOLD = 768

# 清理任务分批大小
_CLEANUP_BATCH_SIZE = 2000


def _bucket_for_viewport(width: int | None) -> str:
    """根据视口宽度返回分桶: lg(>1440)/md(768-1440)/sm(<768)"""
    if width is None:
        return "md"
    if width > _VIEWPORT_LG_THRESHOLD:
        return "lg"
    if width < _VIEWPORT_SM_THRESHOLD:
        return "sm"
    return "md"


def _build_storage_key() -> str:
    """生成对象存储 key：session-replay/{YYYYMM}/{uuid}.json"""
    date_path = datetime.utcnow().strftime("%Y%m")
    unique_name = f"{uuid.uuid4().hex}.json"
    return f"session-replay/{date_path}/{unique_name}"


def _day_from_started_at(started_at: object) -> datetime.date:
    """从 started_at 计算 heatmap 聚合用的日期分桶（按 UTC）。

    router 上报的 started_at 多为 datetime.isoformat()（naive 本地时间），
    过去按本地时间直接取 .date() 在东八区会跨天偏移最多 8h，导致按天聚合错位。
    统一规则：naive 一律视为 UTC，带 tz 的 astimezone(UTC) 后取日期；
    解析失败或为空回退 datetime.utcnow().date()。

    返回 date 对象，与 HeatmapPoint.day（SQLAlchemy Date）一致。
    """
    if isinstance(started_at, str):
        try:
            value = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        except ValueError:
            return datetime.utcnow().date()
    elif isinstance(started_at, datetime):
        value = started_at
    else:
        return datetime.utcnow().date()

    if value.tzinfo is not None:
        value = value.astimezone(UTC)
    # naive 直接视为 UTC，不做本地时间转换
    return value.date()


def _extract_heatmap_points(events: list[dict], viewport_w: int | None, viewport_h: int | None) -> list[dict]:
    """从 rrweb 事件中提取热力图坐标点。

    返回 [{event_type, x_ratio, y_ratio}, ...]（不含 day/page_path/tenant，由调用方补齐）。
    缺失视口尺寸时返回空列表；mousemove 按 _MOUSEMOVE_SAMPLE_STEP 采样。
    """
    if not viewport_w or not viewport_h or viewport_w <= 0 or viewport_h <= 0:
        return []

    points: list[dict] = []
    move_index = 0

    for event in events:
        if not isinstance(event, dict):
            continue

        event_type = event.get("type")
        data = event.get("data")
        if not isinstance(data, dict):
            continue

        x = data.get("x")
        y = data.get("y")
        if x is None or y is None:
            continue

        source = data.get("source")

        if event_type == _RRWEB_INCREMENTAL_SNAPSHOT and source == _SOURCE_MOUSE_MOVE:
            # mousemove 数据量大，固定步长采样
            if move_index % _MOUSEMOVE_SAMPLE_STEP != 0:
                move_index += 1
                continue
            move_index += 1
            point_type = "move"
        elif event_type == _RRWEB_INCREMENTAL_SNAPSHOT and source == _SOURCE_MOUSE_INTERACTION:
            interaction_type = data.get("type")
            # rrweb 的 MouseInteraction.type 是数字枚举，但前端也可能上报字符串；
            # 字符串匹配 click/dblclick/touchstart，数字按 rrweb 枚举（2=click,3=dblclick,15=touchstart）
            interaction_key = str(interaction_type) if interaction_type is not None else ""
            # 字符串匹配 click/dblclick/touchstart；数字兜底 rrweb 枚举（2/3/15）
            if interaction_key not in _CLICK_INTERACTIONS and interaction_type not in (2, 3, 15):
                continue
            point_type = "click"
        else:
            continue

        try:
            x_val = float(x)
            y_val = float(y)
        except (TypeError, ValueError):
            continue

        x_ratio = round(x_val / viewport_w, 2)
        y_ratio = round(y_val / viewport_h, 2)
        # clamp 到 [0, 1]
        x_ratio = min(1.0, max(0.0, x_ratio))
        y_ratio = min(1.0, max(0.0, y_ratio))

        points.append({"event_type": point_type, "x_ratio": x_ratio, "y_ratio": y_ratio})

    return points


@celery_app.task(
    name="app.tasks.session_event_task.batch_save_session_events",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=180,
    soft_time_limit=150,
)
def batch_save_session_events(batch_payload: dict):
    """批量保存一次上报的 rrweb 事件段。

    流程：
      1) events 序列化为 JSON bytes 落对象存储
      2) 同步 DB 写 SessionEvent 行（存 storage_url / storage_key 索引）
      3) 提取热力图坐标并 upsert HeatmapPoint（mousemove 采样）

    Args:
        batch_payload: 见路由层组装，含 tenant_id/actor_id/session_id/events 等字段
    """
    tenant_id = batch_payload.get("tenant_id")
    actor_id = batch_payload.get("actor_id")
    actor_name = batch_payload.get("actor_name")
    ip = batch_payload.get("ip")
    user_agent = batch_payload.get("user_agent")
    platform = batch_payload.get("platform") or "admin"
    session_id = batch_payload.get("session_id")
    viewport_w = batch_payload.get("viewport_w")
    viewport_h = batch_payload.get("viewport_h")
    page_path = batch_payload.get("page_path")
    sequence = batch_payload.get("sequence") or 0
    started_at = batch_payload.get("started_at")
    ended_at = batch_payload.get("ended_at")
    events = batch_payload.get("events") or []

    if not session_id:
        logger.warning("[任务] session_event 缺少 session_id，跳过")
        return {"success": False, "error": "missing session_id"}

    logger.debug(
        f"[任务] 保存会话事件段: session={session_id} seq={sequence} events={len(events)}"
    )

    # ---------- 1) 对象存储 ----------
    storage_url = None
    storage_key = None
    if events:
        try:
            data = json.dumps(events, ensure_ascii=False).encode("utf-8")
            key = _build_storage_key()
            storage = get_storage()
            result = asyncio.run(storage.upload_bytes(data, key, "application/json"))
            storage_url = result.url
            storage_key = result.key
        except Exception as exc:
            # 存储失败直接抛出，触发任务重试；events 不会丢失
            logger.error(f"[任务] 会话事件对象存储上传失败: {exc}")
            raise

    # ---------- 2) / 3) DB 写入 + 热力图 upsert ----------
    with get_sync_db() as db:
        try:
            segment_id = str(uuid.uuid4())
            row = SessionEvent(
                id=segment_id,
                tenant_id=tenant_id,
                platform=platform,
                session_id=session_id,
                actor_id=actor_id,
                actor_name=actor_name,
                viewport_w=viewport_w,
                viewport_h=viewport_h,
                page_path=page_path,
                event_count=len(events),
                storage_url=storage_url,
                storage_key=storage_key,
                sequence=sequence,
                started_at=started_at,
                ended_at=ended_at,
                ip=ip,
                user_agent=user_agent,
            )
            db.add(row)

            # 热力图坐标提取 + upsert
            if page_path:
                points = _extract_heatmap_points(events, viewport_w, viewport_h)
                if points:
                    # day 一律按 UTC 计算（naive 视为 UTC，带 tz 转 UTC）
                    day_date = _day_from_started_at(started_at)

                    viewport_bucket = _bucket_for_viewport(viewport_w)

                    upsert_rows = [
                        {
                            "id": str(uuid.uuid4()),
                            "tenant_id": tenant_id,
                            "page_path": page_path,
                            "viewport_bucket": viewport_bucket,
                            "event_type": p["event_type"],
                            "x_ratio": p["x_ratio"],
                            "y_ratio": p["y_ratio"],
                            "weight": 1,
                            "day": day_date,
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow(),
                        }
                        for p in points
                    ]

                    stmt = (
                        pg_insert(HeatmapPoint.__table__)
                        .values(upsert_rows)
                        .on_conflict_do_update(
                            index_elements=[
                                "tenant_id", "page_path", "viewport_bucket",
                                "event_type", "x_ratio", "y_ratio", "day",
                            ],
                            set_={
                                "weight": HeatmapPoint.__table__.c.weight + 1,
                                "updated_at": datetime.utcnow(),
                            },
                        )
                    )
                    db.execute(stmt)

            db.commit()
            logger.debug(f"[任务] 会话事件段保存成功: segment_id={segment_id}")
            return {
                "success": True,
                "segment_id": segment_id,
                "event_count": len(events),
            }

        except Exception as exc:
            db.rollback()
            logger.error(f"[任务] 会话事件段保存失败: {exc}")
            raise


@celery_app.task(
    name="app.tasks.session_event_task.cleanup_session_events",
    time_limit=600,
    soft_time_limit=540,
)
def cleanup_session_events(retention_days: int = SESSION_EVENT_RETENTION_DAYS):
    """清理过期的会话事件段。

    删除前先按 storage_key 调对象存储删除清理原始 JSON 文件，
    存储删除失败仅 warning 不阻断 DB 清理。

    Args:
        retention_days: 保留天数，默认 30 天
    """
    cutoff = datetime.utcnow() - timedelta(days=retention_days)

    async def _delete_keys_async(keys: list[str]) -> None:
        """单事件循环内顺序删除多个对象存储 key，避免反复创建/销毁事件循环。"""
        storage = get_storage()
        for key in keys:
            try:
                await storage.delete(key)
            except Exception as del_exc:
                # 单文件删除失败不影响整体流程
                logger.warning(
                    f"[清理] 会话事件对象存储删除失败 key={key}: {del_exc}"
                )

    with get_sync_db() as db:
        try:
            total_deleted = 0

            while True:
                rows = db.execute(
                    SessionEvent.__table__.select()
                    .with_only_columns(
                        SessionEvent.id,
                        SessionEvent.storage_key,
                    )
                    .where(SessionEvent.created_at < cutoff)
                    .limit(_CLEANUP_BATCH_SIZE)
                ).fetchall()

                if not rows:
                    break

                # 收集本批待删 key，单次 asyncio.run 清理对象存储（失败不阻断）
                storage_keys = [row[1] for row in rows if row[1]]
                if storage_keys:
                    try:
                        asyncio.run(_delete_keys_async(storage_keys))
                    except Exception as batch_exc:
                        # 单批次存储清理整体异常也不阻断 DB 清理
                        logger.warning(
                            f"[清理] 会话事件对象存储批次删除异常: {batch_exc}"
                        )

                id_list = [row[0] for row in rows]
                db.execute(
                    SessionEvent.__table__.delete().where(SessionEvent.id.in_(id_list))
                )
                db.commit()
                total_deleted += len(id_list)
                logger.info(
                    f"[清理] 已删除 {total_deleted} 条过期会话事件（保留 {retention_days} 天）"
                )

            logger.info(
                f"[清理] 会话事件清理完成，共删除 {total_deleted} 条（截止 {cutoff.date()}）"
            )
            return {"success": True, "deleted": total_deleted, "cutoff": cutoff.isoformat()}

        except Exception as exc:
            db.rollback()
            logger.error(f"[任务] 会话事件清理失败: {exc}")
            raise


@celery_app.task(
    name="app.tasks.session_event_task.cleanup_heatmap_points",
    time_limit=600,
    soft_time_limit=540,
)
def cleanup_heatmap_points(retention_days: int = HEATMAP_RETENTION_DAYS):
    """清理过期的热力图聚合点。

    Args:
        retention_days: 保留天数，默认 180 天
    """
    cutoff = (datetime.utcnow() - timedelta(days=retention_days)).date()

    with get_sync_db() as db:
        try:
            total_deleted = 0

            while True:
                rows = db.execute(
                    HeatmapPoint.__table__.select()
                    .with_only_columns(HeatmapPoint.id)
                    .where(HeatmapPoint.day < cutoff)
                    .limit(_CLEANUP_BATCH_SIZE)
                ).fetchall()

                if not rows:
                    break

                id_list = [row[0] for row in rows]
                db.execute(
                    HeatmapPoint.__table__.delete().where(HeatmapPoint.id.in_(id_list))
                )
                db.commit()
                total_deleted += len(id_list)
                logger.info(
                    f"[清理] 已删除 {total_deleted} 条过期热力图点（保留 {retention_days} 天）"
                )

            logger.info(
                f"[清理] 热力图点清理完成，共删除 {total_deleted} 条（截止 {cutoff}）"
            )
            return {"success": True, "deleted": total_deleted, "cutoff": str(cutoff)}

        except Exception as exc:
            db.rollback()
            logger.error(f"[任务] 热力图点清理失败: {exc}")
            raise
