"""低代码页面单元测试。"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestLowCodePageService:
    """LowCodePageService 单元测试。"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话。"""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.add = MagicMock()
        db.delete = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        """创建 service 实例。"""
        from app.modules.lowcode.service import LowCodePageService
        return LowCodePageService(mock_db)

    @pytest.mark.asyncio
    async def test_create_page(self, service, mock_db):
        """测试创建页面。"""
        # 执行
        page = await service.create(
            tenant_id="tenant-1",
            name="测试页面",
            slug="test-page",
            description="这是一个测试页面",
            schema_data={"componentName": "Page", "props": {}, "children": []},
        )

        # 验证 - add 会被调用两次（页面 + 审计日志）
        assert mock_db.add.call_count >= 1
        mock_db.commit.assert_called()
        mock_db.refresh.assert_called()
        assert page.name == "测试页面"
        assert page.slug == "test-page"
        assert page.tenant_id == "tenant-1"

    @pytest.mark.asyncio
    async def test_get_by_id(self, service, mock_db):
        """测试根据ID获取页面。"""
        # 准备
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            id="page-1",
            tenant_id="tenant-1",
            name="测试页面",
            slug="test-page",
        )
        mock_db.execute.return_value = mock_result

        # 执行
        page = await service.get_by_id("tenant-1", "page-1")

        # 验证
        assert page is not None
        assert page.id == "page-1"

    @pytest.mark.asyncio
    async def test_delete_draft_page(self, service, mock_db):
        """测试删除草稿页面。"""
        # 准备
        mock_page = MagicMock(id="page-1", status=0, tenant_id="tenant-1")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_page
        mock_db.execute.return_value = mock_result

        # 执行
        deleted = await service.delete("tenant-1", "page-1")

        # 验证
        assert deleted is True
        mock_db.delete.assert_called_once_with(mock_page)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_published_page_fails(self, service, mock_db):
        """测试删除已发布页面应失败。"""
        # 准备
        mock_page = MagicMock(id="page-1", status=1, tenant_id="tenant-1")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_page
        mock_db.execute.return_value = mock_result

        # 执行
        deleted = await service.delete("tenant-1", "page-1")

        # 验证
        assert deleted is False
        mock_db.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_slug_unique(self, service, mock_db):
        """测试 slug 唯一性检查。"""
        # 准备: 无冲突
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # 执行
        is_unique = await service.check_slug_unique("tenant-1", "new-slug")

        # 验证
        assert is_unique is True

    @pytest.mark.asyncio
    async def test_check_slug_not_unique(self, service, mock_db):
        """测试 slug 唯一性检查(有冲突)。"""
        # 准备: 有冲突
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "existing-id"
        mock_db.execute.return_value = mock_result

        # 执行
        is_unique = await service.check_slug_unique("tenant-1", "existing-slug")

        # 验证
        assert is_unique is False

    @pytest.mark.asyncio
    async def test_update_page(self, service, mock_db):
        """测试更新页面。"""
        # 准备
        mock_page = MagicMock(
            id="page-1",
            tenant_id="tenant-1",
            name="旧名称",
            slug="old-slug",
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_page
        mock_db.execute.return_value = mock_result

        # 执行
        updated = await service.update(
            tenant_id="tenant-1",
            page_id="page-1",
            name="新名称",
            schema_data={"componentName": "Page", "props": {}, "children": []},
        )

        # 验证
        assert updated is not None
        assert updated.name == "新名称"
        mock_db.commit.assert_called_once()


class TestLowCodePageSchema:
    """Schema 数据结构测试。"""

    def test_schema_structure(self):
        """测试 Schema 基本结构。"""
        schema = {
            "componentName": "Page",
            "props": {
                "navigationBarTitleText": "测试页面",
                "navigationBarBackgroundColor": "#ffffff",
                "navigationBarTextStyle": "black",
            },
            "children": [
                {
                    "id": "node_001",
                    "componentName": "NutText",
                    "props": {
                        "text": "Hello World",
                        "fontSize": "16px",
                        "color": "#333",
                    },
                    "children": [],
                }
            ],
        }

        # 验证根节点
        assert schema["componentName"] == "Page"
        assert "props" in schema
        assert "children" in schema
        assert len(schema["children"]) == 1

        # 验证子节点
        child = schema["children"][0]
        assert child["id"] == "node_001"
        assert child["componentName"] == "NutText"
        assert child["props"]["text"] == "Hello World"


class TestSSRFProtection:
    """SSRF 防护测试。"""

    def test_validate_url_allowed(self):
        """允许的 URL 格式。"""
        from app.modules.lowcode.service import _validate_url_for_ssrf

        # 正常的外部 URL 不应抛出异常
        _validate_url_for_ssrf("https://api.example.com/data")
        _validate_url_for_ssrf("http://example.com/api/users")

    def test_validate_url_blocked_protocol(self):
        """阻止非 http/https 协议。"""
        from app.modules.lowcode.service import _validate_url_for_ssrf, SSRFError

        with pytest.raises(SSRFError, match="不允许的协议"):
            _validate_url_for_ssrf("ftp://example.com/file.txt")

        with pytest.raises(SSRFError, match="不允许的协议"):
            _validate_url_for_ssrf("file:///etc/passwd")

    def test_validate_url_blocked_localhost(self):
        """阻止访问 localhost。"""
        from app.modules.lowcode.service import _validate_url_for_ssrf, SSRFError

        with pytest.raises(SSRFError, match="禁止访问的主机"):
            _validate_url_for_ssrf("http://localhost/admin")

        with pytest.raises(SSRFError, match="禁止访问的主机"):
            _validate_url_for_ssrf("http://127.0.0.1/admin")

    def test_validate_url_blocked_private_ip(self):
        """阻止访问私有 IP。"""
        from app.modules.lowcode.service import _validate_url_for_ssrf, SSRFError

        with pytest.raises(SSRFError, match="禁止访问的 IP"):
            _validate_url_for_ssrf("http://192.168.1.1/admin")

        with pytest.raises(SSRFError, match="禁止访问的 IP"):
            _validate_url_for_ssrf("http://10.0.0.1/admin")

        with pytest.raises(SSRFError, match="禁止访问的 IP"):
            _validate_url_for_ssrf("http://172.16.0.1/admin")

    def test_validate_url_blocked_metadata(self):
        """阻止访问云服务 metadata 端点。"""
        from app.modules.lowcode.service import _validate_url_for_ssrf, SSRFError

        with pytest.raises(SSRFError, match="禁止访问的主机"):
            _validate_url_for_ssrf("http://169.254.169.254/latest/meta-data/")

        with pytest.raises(SSRFError, match="禁止访问的主机"):
            _validate_url_for_ssrf("http://metadata.google.internal/")

    def test_validate_url_missing_hostname(self):
        """缺少主机名的 URL。"""
        from app.modules.lowcode.service import _validate_url_for_ssrf, SSRFError

        with pytest.raises(SSRFError, match="缺少主机名"):
            _validate_url_for_ssrf("http:///path")

    def test_validate_url_invalid_format(self):
        """格式错误的 URL。"""
        from app.modules.lowcode.service import _validate_url_for_ssrf, SSRFError

        with pytest.raises(SSRFError):
            _validate_url_for_ssrf("not-a-url")

    @pytest.mark.asyncio
    async def test_data_source_ssrf_blocked(self):
        """test_data_source 阻止 SSRF 请求。"""
        from app.modules.lowcode.service import LowCodePageService

        result = await LowCodePageService.test_data_source(
            url="http://169.254.169.254/latest/meta-data/",
            method="GET",
        )

        assert result["success"] is False
        assert "安全检查失败" in result["error"] or "禁止访问" in result["error"]

    @pytest.mark.asyncio
    async def test_data_source_ssrf_localhost_blocked(self):
        """test_data_source 阻止访问 localhost。"""
        from app.modules.lowcode.service import LowCodePageService

        result = await LowCodePageService.test_data_source(
            url="http://localhost:6379/",
            method="GET",
        )

        assert result["success"] is False
        assert "安全检查失败" in result["error"] or "禁止访问" in result["error"]
