"""操作指引单元测试

覆盖范围：
- GuideTourService: get_active_tours, get_progress, update_progress
- AdminGuideTourService: CRUD + 状态更新
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


class TestGuideTourService:
    """用户端指引服务测试。"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.add = MagicMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        from app.modules.guide_tours.service import GuideTourService
        return GuideTourService(mock_db)

    @pytest.mark.asyncio
    async def test_get_active_tours(self, service, mock_db):
        """获取已发布指引列表。"""
        mock_row = MagicMock()
        mock_row.id = "tour-1"
        mock_row.code = "dashboard"
        mock_row.title = {"zh": "仪表盘引导", "en": "Dashboard Guide"}
        mock_row.description = {"zh": "说明", "en": "Description"}
        mock_row.steps = [{"target": ".card", "route": "/dashboard", "title": {"zh": "步骤1", "en": "Step 1"}}]
        mock_row.current_step = 0
        mock_row.progress_status = None

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_db.execute.return_value = mock_result

        items = await service.get_active_tours(admin_id="admin-1")

        assert len(items) == 1
        assert items[0]["id"] == "tour-1"
        assert items[0]["code"] == "dashboard"
        assert items[0]["currentStep"] == 0
        assert items[0]["progressStatus"] == 0

    @pytest.mark.asyncio
    async def test_get_active_tours_empty(self, service, mock_db):
        """无已发布指引时返回空列表。"""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result

        items = await service.get_active_tours(admin_id="admin-1")
        assert items == []

    @pytest.mark.asyncio
    async def test_get_progress_exists(self, service, mock_db):
        """获取已有进度。"""
        mock_progress = MagicMock()
        mock_progress.current_step = 2
        mock_progress.status = 0

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_progress
        mock_db.execute.return_value = mock_result

        progress = await service.get_progress(tour_id="tour-1", admin_id="admin-1")
        assert progress is not None
        assert progress.current_step == 2

    @pytest.mark.asyncio
    async def test_get_progress_not_exists(self, service, mock_db):
        """无进度时返回 None。"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        progress = await service.get_progress(tour_id="tour-1", admin_id="admin-1")
        assert progress is None

    @pytest.mark.asyncio
    async def test_update_progress_create_new(self, service, mock_db):
        """首次更新进度时创建新记录。"""
        from app.modules.guide_tours.schemas import ProgressUpdate

        # get_progress 返回 None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        mock_progress = MagicMock()
        mock_progress.current_step = 1
        mock_progress.status = 0
        mock_db.refresh.return_value = mock_progress

        data = ProgressUpdate(currentStep=1)
        result = await service.update_progress(tour_id="tour-1", admin_id="admin-1", data=data)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_progress_existing(self, service, mock_db):
        """更新已有进度。"""
        from app.modules.guide_tours.schemas import ProgressUpdate

        mock_progress = MagicMock()
        mock_progress.current_step = 1
        mock_progress.status = 0

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_progress
        mock_db.execute.return_value = mock_result

        data = ProgressUpdate(currentStep=3, status=1)
        result = await service.update_progress(tour_id="tour-1", admin_id="admin-1", data=data)

        assert mock_progress.current_step == 3
        assert mock_progress.status == 1
        mock_db.commit.assert_called_once()


class TestAdminGuideTourService:
    """管理端指引 CRUD 服务测试。"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.add = MagicMock()
        db.delete = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        from app.modules.guide_tours.service import AdminGuideTourService
        return AdminGuideTourService(mock_db)

    @pytest.mark.asyncio
    async def test_create_tour(self, service, mock_db):
        """创建指引。"""
        from app.modules.guide_tours.schemas import GuideTourCreate, TourStep

        data = GuideTourCreate(
            code="test_tour",
            title={"zh": "测试", "en": "Test"},
            description={"zh": "描述", "en": "Desc"},
            steps=[
                TourStep(
                    target=".card",
                    placement="bottom",
                    route="/dashboard",
                    title={"zh": "步骤1", "en": "Step 1"},
                    description={"zh": "说明", "en": "Desc"},
                )
            ],
            sortOrder=0,
        )

        result = await service.create(data=data, created_by="admin-1")

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        # 验证创建的对象属性
        added_tour = mock_db.add.call_args[0][0]
        assert added_tour.code == "test_tour"
        assert added_tour.title == {"zh": "测试", "en": "Test"}
        assert added_tour.created_by == "admin-1"

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, service, mock_db):
        """根据 ID 获取指引。"""
        mock_tour = MagicMock()
        mock_tour.id = "tour-1"
        mock_tour.code = "test"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tour
        mock_db.execute.return_value = mock_result

        result = await service.get_by_id("tour-1")
        assert result is not None
        assert result.id == "tour-1"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service, mock_db):
        """ID 不存在时返回 None。"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_by_id("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_tour(self, service, mock_db):
        """更新指引。"""
        from app.modules.guide_tours.schemas import GuideTourUpdate

        mock_tour = MagicMock()
        mock_tour.id = "tour-1"
        mock_tour.code = "old_code"
        mock_tour.title = {"zh": "旧标题", "en": "Old"}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tour
        mock_db.execute.return_value = mock_result

        data = GuideTourUpdate(code="new_code", title={"zh": "新标题", "en": "New"})
        result = await service.update(tour_id="tour-1", data=data, updated_by="admin-1")

        assert mock_tour.code == "new_code"
        assert mock_tour.title == {"zh": "新标题", "en": "New"}
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_tour_not_found(self, service, mock_db):
        """更新不存在的指引返回 None。"""
        from app.modules.guide_tours.schemas import GuideTourUpdate

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        data = GuideTourUpdate(code="new_code")
        result = await service.update(tour_id="nonexistent", data=data, updated_by="admin-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_status(self, service, mock_db):
        """更新指引发布状态。"""
        mock_tour = MagicMock()
        mock_tour.id = "tour-1"
        mock_tour.status = 0

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tour
        mock_db.execute.return_value = mock_result

        result = await service.update_status(tour_id="tour-1", status=1, updated_by="admin-1")

        assert mock_tour.status == 1
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_tour(self, service, mock_db):
        """删除指引。"""
        mock_tour = MagicMock()
        mock_tour.id = "tour-1"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tour
        mock_db.execute.return_value = mock_result

        deleted = await service.delete(tour_id="tour-1")

        assert deleted is True
        mock_db.delete.assert_called_once_with(mock_tour)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_tour_not_found(self, service, mock_db):
        """删除不存在的指引返回 False。"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        deleted = await service.delete(tour_id="nonexistent")
        assert deleted is False


class TestGuideTourSchemas:
    """Schema 测试。"""

    def test_tour_step_alias(self):
        """TourStep 的 highlightPadding 别名正确。"""
        from app.modules.guide_tours.schemas import TourStep

        step = TourStep(
            target=".card",
            placement="bottom",
            route="/dashboard",
            title={"zh": "标题", "en": "Title"},
            highlightPadding=12,
        )
        dumped = step.model_dump(by_alias=True)
        assert dumped["highlightPadding"] == 12

    def test_guide_tour_item_defaults(self):
        """GuideTourItem 默认值正确。"""
        from app.modules.guide_tours.schemas import GuideTourItem

        item = GuideTourItem(
            id="1",
            code="test",
            title={"zh": "测试", "en": "Test"},
            steps=[],
        )
        assert item.current_step == 0
        assert item.progress_status == 0

    def test_progress_update_partial(self):
        """ProgressUpdate 支持部分更新。"""
        from app.modules.guide_tours.schemas import ProgressUpdate

        data = ProgressUpdate(currentStep=5)
        assert data.current_step == 5
        assert data.status is None

    def test_locale_map(self):
        """LocaleMap 结构正确。"""
        from app.modules.guide_tours.schemas import LocaleMap

        lm = LocaleMap(zh="中文", en="English")
        assert lm.zh == "中文"
        assert lm.en == "English"
