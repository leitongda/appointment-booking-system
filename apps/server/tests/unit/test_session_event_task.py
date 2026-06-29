"""
session_event_task 单元测试

重点守护本次修复：
1. _day_from_started_at 时区分桶（P1-2）—— 东八区 20:00-24:00 不再错位到次日
2. _extract_heatmap_points 视口缺失 / mousemove 采样 / 坐标 clamp
3. batch_save_session_events DB 失败时补偿删除已上传对象（P2-3）
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.tasks.session_event_task import (
    _bucket_for_viewport,
    _day_from_started_at,
    _extract_heatmap_points,
)


# ---------------------------------------------------------------------------
# P1-2: _day_from_started_at 时区分桶
# 业务时区 Asia/Shanghai（与 celery_app.timezone 一致）。
# 修复前：naive/带tz 一律按 UTC 取 date，导致东八区 20:00-24:00 归到次日。
# 修复后：带 tz 转 Asia/Shanghai，naive 视为业务时区本地时间。
# ---------------------------------------------------------------------------

# 东八区 +8h
_CST = timezone(timedelta(hours=8))


@pytest.mark.parametrize(
    "started_at, expected_date, desc",
    [
        # 带 tz UTC 字符串：12:00 UTC = 东八区 20:00 → 当天 06-27
        ("2026-06-27T12:00:00.000Z", "2026-06-27", "东八区20:00应归当天"),
        # 带 tz UTC 字符串：16:00 UTC = 东八区次日 00:00 → 06-28（关键跨天边界）
        ("2026-06-27T16:00:00.000Z", "2026-06-28", "东八区00:00次日应归次日"),
        # 带 tz UTC 23:00 = 东八区次日 07:00 → 06-28
        ("2026-06-27T23:00:00.000Z", "2026-06-28", "东八区清晨应归次日"),
        # naive 本地时间 20:00 → 视为业务时区，归 06-27
        (datetime(2026, 6, 27, 20, 0, 0), "2026-06-27", "naive本地20:00归当天"),
        # naive 本地时间 23:59 → 归当天（不到次日）
        (datetime(2026, 6, 27, 23, 59, 59), "2026-06-27", "naive本地23:59归当天"),
        # 带 tz 但显式东八区：2026-06-27 23:00 +08:00 → 06-27
        (datetime(2026, 6, 27, 23, 0, 0, tzinfo=_CST), "2026-06-27", "显式东八区23:00归当天"),
    ],
)
def test_day_from_started_at_business_timezone(started_at, expected_date, desc):
    """所有时间都应按业务时区（东八区）日历日归桶，不按 UTC。"""
    result = _day_from_started_at(started_at)
    assert str(result) == expected_date, f"用例失败：{desc}，得到 {result}"


def test_day_from_started_at_invalid_string_falls_back():
    """无法解析的字符串回退到当前业务日（不应抛异常）。"""
    result = _day_from_started_at("not-a-date")
    assert result is not None
    assert isinstance(result, type(datetime.now().date()))


def test_day_from_started_at_none_falls_back():
    """None 回退到当前业务日。"""
    result = _day_from_started_at(None)
    assert result is not None


def test_day_from_started_at_other_type_falls_back():
    """非 str/datetime 类型回退到当前业务日。"""
    result = _day_from_started_at(12345)
    assert result is not None


# ---------------------------------------------------------------------------
# 视口分桶
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "width, expected",
    [
        (1920, "lg"),
        (1441, "lg"),
        (1440, "md"),   # 边界：等于阈值归 md
        (1024, "md"),
        (769, "md"),
        (768, "md"),    # 边界：等于阈值归 md
        (767, "sm"),
        (375, "sm"),
        (None, "md"),   # 缺失归 md
    ],
)
def test_bucket_for_viewport(width, expected):
    assert _bucket_for_viewport(width) == expected


# ---------------------------------------------------------------------------
# _extract_heatmap_points
# ---------------------------------------------------------------------------

# rrweb 常量（与 task 内一致）
_INCREMENTAL = 2
_SRC_MOUSE_MOVE = 2
_SRC_MOUSE_INTERACTION = 1


def test_extract_heatmap_points_no_viewport_returns_empty():
    """缺失视口尺寸无法计算相对坐标，返回空。"""
    events = [{"type": _INCREMENTAL, "data": {"x": 10, "y": 20, "source": _SRC_MOUSE_MOVE}}]
    assert _extract_heatmap_points(events, None, 100) == []
    assert _extract_heatmap_points(events, 0, 100) == []
    assert _extract_heatmap_points(events, 100, 0) == []


def test_extract_heatmap_points_clamp_to_unit():
    """坐标超出视口应 clamp 到 [0, 1]。"""
    events = [
        {"type": _INCREMENTAL, "data": {"x": 2000, "y": 3000, "source": _SRC_MOUSE_MOVE}},
    ]
    points = _extract_heatmap_points(events, 1000, 1000)
    assert len(points) == 1
    assert points[0]["x_ratio"] == 1.0
    assert points[0]["y_ratio"] == 1.0


def test_extract_heatmap_points_mousemove_sampled():
    """mousemove 按 _MOUSEMOVE_SAMPLE_STEP=5 采样：10 条仅保留 2 条。"""
    events = [
        {"type": _INCREMENTAL, "data": {"x": i * 10, "y": i * 10, "source": _SRC_MOUSE_MOVE}}
        for i in range(10)
    ]
    points = _extract_heatmap_points(events, 1000, 1000)
    # 采样步长 5：move_index 0,5 命中，其余跳过
    assert len(points) == 2


def test_extract_heatmap_points_click_via_numeric_type():
    """rrweb MouseInteraction.type 数字枚举 2=click 应被识别。"""
    events = [
        {"type": _INCREMENTAL, "data": {"x": 100, "y": 200, "source": _SRC_MOUSE_INTERACTION, "type": 2}},
    ]
    points = _extract_heatmap_points(events, 1000, 1000)
    assert len(points) == 1
    assert points[0]["event_type"] == "click"
    assert points[0]["x_ratio"] == 0.1
    assert points[0]["y_ratio"] == 0.2


def test_extract_heatmap_points_skips_non_positional_events():
    """无 x/y 的事件、非 mouse/interaction source 的事件应跳过。"""
    events = [
        {"type": _INCREMENTAL, "data": {"source": _SRC_MOUSE_MOVE}},  # 无 x/y
        {"type": 4, "data": {"x": 10, "y": 10, "source": 99}},         # 非 incremental
        {"type": _INCREMENTAL, "data": "not-a-dict"},                  # data 非 dict
        "not-a-dict",                                                   # 非 dict
    ]
    assert _extract_heatmap_points(events, 1000, 1000) == []


# ---------------------------------------------------------------------------
# P2-3: batch_save_session_events DB 失败补偿删除孤儿对象
# ---------------------------------------------------------------------------

def _get_raw_batch_save():
    """获取 batch_save_session_events 的原始函数（绕过 Celery autoretry 包装）"""
    from app.tasks.session_event_task import batch_save_session_events
    # Celery task 对象本身可调用，内部逻辑即为原函数
    return batch_save_session_events


@patch("app.tasks.session_event_task.get_storage")
@patch("app.tasks.session_event_task.get_sync_db")
def test_batch_save_cleans_up_orphan_object_on_db_failure(mock_get_sync_db, mock_get_storage):
    """DB 写入失败时，已上传的对象存储文件应被补偿删除，避免孤儿。"""
    # 构造 storage：上传成功返回 key，delete 应被调用
    storage = MagicMock()
    storage.upload_bytes = MagicMock(return_value=MagicMock(url="http://x/y.json", key="session-replay/202606/abc.json"))
    mock_get_storage.return_value = storage

    # 构造 db：commit 抛异常模拟 DB 失败
    db = MagicMock()
    db.commit.side_effect = Exception("DB down")
    ctx = MagicMock()
    ctx.__enter__.return_value = db
    ctx.__exit__.return_value = False
    mock_get_sync_db.return_value = ctx

    # asyncio.run 会被 get_storage().upload_bytes 调用，patch 掉
    with patch("app.tasks.session_event_task.asyncio.run") as mock_run:
        # 第一次 asyncio.run(upload) 返回 result，第二次(delete) 无返回值
        upload_result = MagicMock(url="http://x/y.json", key="session-replay/202606/abc.json")
        mock_run.side_effect = [upload_result, None]
        raw = _get_raw_batch_save()
        with pytest.raises(Exception, match="DB down"):
            raw({
                "tenant_id": "t1",
                "actor_id": "a1",
                "actor_name": "tester",
                "session_id": "s1",
                "platform": "admin",
                "viewport_w": 1920,
                "viewport_h": 1080,
                "page_path": "/x",
                "sequence": 0,
                "started_at": "2026-06-27T12:00:00.000Z",
                "ended_at": "2026-06-27T12:01:00.000Z",
                "events": [{"type": 2, "data": {"x": 1, "y": 1, "source": 2}}],
                "ip": "127.0.0.1",
                "user_agent": "ua",
            })

    # 关键断言：DB 失败后，已上传对象的 delete 被调用（补偿清理）
    assert mock_run.call_count == 2  # 一次上传 + 一次删除
    # db.rollback 被调用
    db.rollback.assert_called_once()


@patch("app.tasks.session_event_task.get_storage")
@patch("app.tasks.session_event_task.get_sync_db")
def test_batch_save_skips_when_no_session_id(mock_get_sync_db, mock_get_storage):
    """缺少 session_id 时应跳过，不触发对象存储上传。"""
    raw = _get_raw_batch_save()
    result = raw({"session_id": None, "events": []})
    assert result["success"] is False
    mock_get_storage.assert_not_called()
