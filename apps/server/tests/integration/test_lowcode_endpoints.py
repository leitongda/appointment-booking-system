"""低代码页面 API 集成测试。"""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def admin_headers(super_admin_token: str) -> dict:
    """鉴权头：复用 conftest 的 super_admin_token（仓内标准 auth fixture）。"""
    return {"Authorization": f"Bearer {super_admin_token}"}


@pytest.mark.integration
class TestLowCodePageEndpoints:
    """低代码页面端点集成测试。"""

    BASE_URL = "/api/v1/lowcode/pages"

    async def test_create_page(self, client: AsyncClient, admin_headers: dict):
        """测试创建页面。"""
        response = await client.post(
            self.BASE_URL,
            json={
                "name": "测试页面",
                "slug": "test-page",
                "description": "这是一个测试页面",
                "schemaData": {
                    "componentName": "Page",
                    "props": {"navigationBarTitleText": "测试"},
                    "children": [],
                },
            },
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "测试页面"
        assert data["data"]["slug"] == "test-page"
        assert data["data"]["status"] == 0

    async def test_create_page_duplicate_slug(
        self, client: AsyncClient, admin_headers: dict
    ):
        """测试创建页面时 slug 重复。"""
        # 先创建一个页面
        await client.post(
            self.BASE_URL,
            json={"name": "页面1", "slug": "duplicate-slug"},
            headers=admin_headers,
        )
        # 再用相同 slug 创建
        response = await client.post(
            self.BASE_URL,
            json={"name": "页面2", "slug": "duplicate-slug"},
            headers=admin_headers,
        )
        assert response.status_code == 400

    async def test_get_page_list(self, client: AsyncClient, admin_headers: dict):
        """测试获取页面列表。"""
        # 先创建一个页面
        await client.post(
            self.BASE_URL,
            json={"name": "列表测试", "slug": "list-test"},
            headers=admin_headers,
        )
        response = await client.get(self.BASE_URL, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "data" in data
        assert "total" in data

    async def test_get_page_detail(self, client: AsyncClient, admin_headers: dict):
        """测试获取页面详情。"""
        # 先创建
        create_resp = await client.post(
            self.BASE_URL,
            json={"name": "详情测试", "slug": "detail-test"},
            headers=admin_headers,
        )
        page_id = create_resp.json()["data"]["id"]

        response = await client.get(
            f"{self.BASE_URL}/{page_id}", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "详情测试"

    async def test_get_page_not_found(self, client: AsyncClient, admin_headers: dict):
        """测试获取不存在的页面。"""
        response = await client.get(
            f"{self.BASE_URL}/nonexistent-id", headers=admin_headers
        )
        assert response.status_code == 404

    async def test_update_page(self, client: AsyncClient, admin_headers: dict):
        """测试更新页面。"""
        create_resp = await client.post(
            self.BASE_URL,
            json={"name": "更新测试", "slug": "update-test"},
            headers=admin_headers,
        )
        page_id = create_resp.json()["data"]["id"]

        response = await client.put(
            f"{self.BASE_URL}/{page_id}",
            json={"name": "已更新", "schemaData": {"componentName": "Page", "props": {}, "children": []}},
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "已更新"

    async def test_delete_draft_page(self, client: AsyncClient, admin_headers: dict):
        """测试删除草稿页面。"""
        create_resp = await client.post(
            self.BASE_URL,
            json={"name": "删除测试", "slug": "delete-test"},
            headers=admin_headers,
        )
        page_id = create_resp.json()["data"]["id"]

        response = await client.delete(
            f"{self.BASE_URL}/{page_id}", headers=admin_headers
        )
        assert response.status_code == 200

    async def test_delete_published_page_fails(
        self, client: AsyncClient, admin_headers: dict
    ):
        """测试删除已发布页面应失败。"""
        create_resp = await client.post(
            self.BASE_URL,
            json={"name": "发布删除测试", "slug": "pub-delete-test"},
            headers=admin_headers,
        )
        page_id = create_resp.json()["data"]["id"]

        # 先发布
        await client.post(
            f"{self.BASE_URL}/{page_id}/publish", headers=admin_headers
        )

        # 尝试删除
        response = await client.delete(
            f"{self.BASE_URL}/{page_id}", headers=admin_headers
        )
        assert response.status_code == 400

    async def test_publish_page(self, client: AsyncClient, admin_headers: dict):
        """测试发布页面。"""
        create_resp = await client.post(
            self.BASE_URL,
            json={"name": "发布测试", "slug": "publish-test"},
            headers=admin_headers,
        )
        page_id = create_resp.json()["data"]["id"]

        response = await client.post(
            f"{self.BASE_URL}/{page_id}/publish", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == 1

    async def test_archive_page(self, client: AsyncClient, admin_headers: dict):
        """测试归档页面。"""
        create_resp = await client.post(
            self.BASE_URL,
            json={"name": "归档测试", "slug": "archive-test"},
            headers=admin_headers,
        )
        page_id = create_resp.json()["data"]["id"]

        response = await client.post(
            f"{self.BASE_URL}/{page_id}/archive", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == 2

    async def test_unauthorized_access(self, client: AsyncClient):
        """测试未授权访问。"""
        response = await client.get(self.BASE_URL)
        assert response.status_code in [401, 403]
