"""
session_events 接口集成测试

重点守护本次修复：
1. replay 接口跳过 storage_key 缺失的段并返回 missing_count（P2-3）
2. replay 全部段缺失时返回 404（避免前端拿到空 segments 拼接失败）
3. batch 上报正常路径
"""
import uuid
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api import deps
from app.main import app
from app.models.session_event import SessionEvent


async def _override_admin():
    """绕过 get_current_admin 认证"""
    return {"id": "admin-1", "is_super_admin": True, "permissions": ["*"]}


async def _insert_session_event(
    db_session,
    *,
    session_id: str,
    storage_key: str | None,
    storage_url: str | None,
    sequence: int = 0,
    event_count: int = 10,
):
    """插入一条 SessionEvent 行。storage_key=None 模拟孤儿/清理中场景。"""
    row = SessionEvent(
        id=str(uuid.uuid4()),
        tenant_id=None,
        platform="admin",
        session_id=session_id,
        actor_id="actor-1",
        actor_name="tester",
        viewport_w=1920,
        viewport_h=1080,
        page_path="/home",
        event_count=event_count,
        storage_url=storage_url,
        storage_key=storage_key,
        sequence=sequence,
    )
    db_session.add(row)
    await db_session.commit()
    return row


@pytest.mark.asyncio
async def test_replay_skips_segments_without_storage_key(db_session, async_client):
    """P2-3: storage_key 缺失的段应被跳过，missing_count 计数。"""
    # 插入 3 段：2 段有 storage_key，1 段缺失（孤儿）
    await _insert_session_event(
        db_session, session_id="sess-mixed", storage_key="k1", storage_url="u1", sequence=0
    )
    await _insert_session_event(
        db_session, session_id="sess-mixed", storage_key=None, storage_url=None, sequence=1
    )
    await _insert_session_event(
        db_session, session_id="sess-mixed", storage_key="k2", storage_url="u2", sequence=2
    )

    app.dependency_overrides[deps.get_current_admin] = _override_admin
    try:
        response = await async_client.get("/api/v1/session-events/sess-mixed/replay")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 200
    payload = response.json()["data"]
    # 缺失的 1 段被跳过，只返回 2 个有效 segment
    assert len(payload["segments"]) == 2
    assert payload["missingCount"] == 1
    # 每个返回的 segment 都有非空 eventsUrl
    for seg in payload["segments"]:
        assert seg["eventsUrl"] is not None


@pytest.mark.asyncio
async def test_replay_returns_404_when_all_segments_missing(db_session, async_client):
    """P2-3: 所有段都缺失 storage_key 时返回 404，不返回空 segments。"""
    await _insert_session_event(
        db_session, session_id="sess-all-missing", storage_key=None, storage_url=None, sequence=0
    )
    await _insert_session_event(
        db_session, session_id="sess-all-missing", storage_key=None, storage_url=None, sequence=1
    )

    app.dependency_overrides[deps.get_current_admin] = _override_admin
    try:
        response = await async_client.get("/api/v1/session-events/sess-all-missing/replay")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_replay_404_when_session_not_found(async_client):
    """不存在的 session_id 应返回 404。"""
    app.dependency_overrides[deps.get_current_admin] = _override_admin
    try:
        response = await async_client.get("/api/v1/session-events/nonexistent/replay")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_batch_upload_normal_path(async_client):
    """batch 上报正常路径：Celery delay 成功，返回 segment_id。"""
    with patch("app.tasks.session_event_task.batch_save_session_events") as mock_task:
        mock_task.delay.return_value = None
        response = await async_client.post(
            "/api/v1/session-events/batch",
            json={
                "sessionId": "sess-upload",
                "viewportW": 1920,
                "viewportH": 1080,
                "pagePath": "/home",
                "sequence": 0,
                "startedAt": "2026-06-27T12:00:00.000Z",
                "endedAt": "2026-06-27T12:01:00.000Z",
                "events": [{"type": 2, "data": {"x": 1, "y": 1}}],
            },
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["success"] is True
    assert payload["count"] == 1
    assert "segmentId" in payload
    assert mock_task.delay.called
