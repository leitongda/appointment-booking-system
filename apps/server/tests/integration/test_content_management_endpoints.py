from datetime import datetime
from uuid import uuid4
from unittest.mock import patch

import pytest

from app.api import deps
from app.main import app
from app.models.content import Banner, News, Notice


async def _override_get_current_admin():
    return {
        "id": "admin-1",
        "is_admin": True,
        "is_super_admin": True,
        "permissions": ["*"],
    }


@pytest.mark.asyncio
async def test_content_news_crud_endpoints(async_client, db_session):
    seeded_news = News(
        id=str(uuid4()),
        title="种子新闻",
        type=1,
        summary="summary",
        content="content",
        status=1,
        publish_time=datetime.now(),
    )
    db_session.add(seeded_news)
    await db_session.commit()

    app.dependency_overrides[deps.get_current_admin] = _override_get_current_admin
    try:
        with patch("app.tasks.operation_log_task.save_operation_log") as mock_task:
            mock_task.delay.return_value = None
            list_response = await async_client.get("/api/v1/content/news")
            detail_response = await async_client.get(f"/api/v1/content/news/{seeded_news.id}")
            create_response = await async_client.post(
                "/api/v1/content/news",
                json={
                    "title": "新新闻",
                    "type": 2,
                    "summary": "created",
                    "content": "created content",
                    "status": 1,
                    "is_top": 0,
                },
            )
            created_id = create_response.json()["data"]["id"]
            update_response = await async_client.put(
                f"/api/v1/content/news/{created_id}",
                json={
                    "title": "更新后的新闻",
                    "type": 2,
                    "summary": "updated",
                    "content": "updated content",
                    "status": 1,
                    "is_top": 1,
                },
            )
            delete_response = await async_client.delete(f"/api/v1/content/news/{created_id}")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert list_response.status_code == 200
    assert list_response.json()["data"][0]["title"] == "种子新闻"

    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["id"] == seeded_news.id

    assert create_response.status_code == 200
    assert create_response.json()["data"]["title"] == "新新闻"

    assert update_response.status_code == 200
    assert update_response.json()["data"]["title"] == "更新后的新闻"
    assert update_response.json()["data"]["is_top"] == 1

    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["message"] == "删除成功"


@pytest.mark.asyncio
async def test_content_notice_crud_endpoints(async_client, db_session):
    seeded_notice = Notice(
        id=str(uuid4()),
        title="种子公告",
        type=1,
        content="notice",
        status=1,
        publish_time=datetime.now(),
    )
    db_session.add(seeded_notice)
    await db_session.commit()

    app.dependency_overrides[deps.get_current_admin] = _override_get_current_admin
    try:
        with patch("app.tasks.operation_log_task.save_operation_log") as mock_task:
            mock_task.delay.return_value = None
            list_response = await async_client.get("/api/v1/content/notices")
            detail_response = await async_client.get(f"/api/v1/content/notices/{seeded_notice.id}")
            create_response = await async_client.post(
                "/api/v1/content/notices",
                json={
                    "title": "新公告",
                    "type": 2,
                    "content": "created notice",
                    "status": 1,
                    "is_top": 0,
                },
            )
            created_id = create_response.json()["data"]["id"]
            update_response = await async_client.put(
                f"/api/v1/content/notices/{created_id}",
                json={
                    "title": "更新后的公告",
                    "type": 2,
                    "content": "updated notice",
                    "status": 1,
                    "is_top": 1,
                },
            )
            delete_response = await async_client.delete(f"/api/v1/content/notices/{created_id}")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert list_response.status_code == 200
    assert list_response.json()["data"][0]["title"] == "种子公告"

    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["id"] == seeded_notice.id

    assert create_response.status_code == 200
    assert create_response.json()["data"]["title"] == "新公告"

    assert update_response.status_code == 200
    assert update_response.json()["data"]["title"] == "更新后的公告"
    assert update_response.json()["data"]["is_top"] == 1

    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["message"] == "删除成功"


@pytest.mark.asyncio
async def test_content_banner_crud_endpoints(async_client, db_session):
    seeded_banner = Banner(
        id=str(uuid4()),
        title="种子轮播图",
        image_url="https://example.com/original.png",
        position="home",
        status=1,
        sort_order=1,
    )
    db_session.add(seeded_banner)
    await db_session.commit()

    app.dependency_overrides[deps.get_current_admin] = _override_get_current_admin
    try:
        with patch("app.tasks.operation_log_task.save_operation_log") as mock_task:
            mock_task.delay.return_value = None
            list_response = await async_client.get("/api/v1/content/banners")
            create_response = await async_client.post(
                "/api/v1/content/banners",
                json={
                    "title": "新轮播图",
                    "image_url": "https://example.com/new.png",
                    "position": "home",
                    "status": 1,
                    "sort_order": 2,
                    "link_type": 0,
                },
            )
            created_id = create_response.json()["data"]["id"]
            update_response = await async_client.put(
                f"/api/v1/content/banners/{created_id}",
                json={
                    "title": "更新后的轮播图",
                    "image_url": "https://example.com/updated.png",
                    "position": "home",
                    "status": 1,
                    "sort_order": 3,
                    "link_type": 1,
                    "link_url": "https://example.com/jump",
                },
            )
            delete_response = await async_client.delete(f"/api/v1/content/banners/{created_id}")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert list_response.status_code == 200
    assert list_response.json()["data"][0]["title"] == "种子轮播图"

    assert create_response.status_code == 200
    assert create_response.json()["data"]["title"] == "新轮播图"

    assert update_response.status_code == 200
    assert update_response.json()["data"]["title"] == "更新后的轮播图"
    assert update_response.json()["data"]["link_type"] == 1

    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["message"] == "删除成功"
