from datetime import datetime
from uuid import uuid4

import pytest

from app.models.content import Banner, News, Notice


@pytest.mark.asyncio
async def test_content_public_endpoints(async_client, db_session):
    news = News(
        id=str(uuid4()),
        title="已发布新闻",
        type=1,
        content="news content",
        status=1,
        publish_time=datetime.now(),
    )
    notice = Notice(
        id=str(uuid4()),
        title="已发布公告",
        type=1,
        content="notice content",
        status=1,
        publish_time=datetime.now(),
    )
    banner = Banner(
        id=str(uuid4()),
        title="首页轮播",
        image_url="https://example.com/banner.png",
        position="home",
        status=1,
        sort_order=1,
    )
    db_session.add_all([news, notice, banner])
    await db_session.commit()

    news_response = await async_client.get("/api/v1/content/news/published")
    notice_response = await async_client.get("/api/v1/content/notices/published")
    banner_response = await async_client.get("/api/v1/content/banners/active")

    assert news_response.status_code == 200
    assert news_response.json()["data"][0]["title"] == "已发布新闻"

    assert notice_response.status_code == 200
    assert notice_response.json()["data"][0]["title"] == "已发布公告"

    assert banner_response.status_code == 200
    assert banner_response.json()["data"][0]["title"] == "首页轮播"
