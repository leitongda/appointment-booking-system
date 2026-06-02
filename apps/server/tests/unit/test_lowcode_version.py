"""
低代码页面版本管理服务单元测试

覆盖 create_snapshot / get_versions / rollback_to_version / get_latest_version。
全部使用 AsyncMock 模拟 db，无外部依赖。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.lowcode.version_service import LowCodePageVersionService
from app.models.lowcode_page import LowCodePage
from app.models.lowcode_page_version import LowCodePageVersion


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_page(
    page_id: str = "page-1",
    tenant_id: str = "tenant-1",
    schema_data: dict | None = None,
    current_version: int = 0,
    publish_count: int = 0,
) -> LowCodePage:
    page = MagicMock(spec=LowCodePage)
    page.id = page_id
    page.tenant_id = tenant_id
    page.schema_data = schema_data or {"nodes": []}
    page.current_version = current_version
    page.publish_count = publish_count
    return page


def _make_version(
    version_id: str = "ver-1",
    page_id: str = "page-1",
    tenant_id: str = "tenant-1",
    version: int = 1,
    schema_data: dict | None = None,
    data_sources: list | None = None,
    snapshot_label: str | None = None,
) -> MagicMock:
    v = MagicMock(spec=LowCodePageVersion)
    v.id = version_id
    v.page_id = page_id
    v.tenant_id = tenant_id
    v.version = version
    v.schema_data = schema_data or {"nodes": []}
    v.data_sources = data_sources or []
    v.snapshot_label = snapshot_label
    return v


def _patch_query(return_value):
    """返回一个 patch 后的 db.execute，使 result.scalars().all() / scalar_one_or_none() / scalar() 返回指定值。"""
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = return_value if isinstance(return_value, list) else [return_value]
    mock_result.scalars.return_value = mock_scalars
    mock_result.scalar_one_or_none.return_value = (
        return_value if not isinstance(return_value, list) else None
    )
    mock_result.scalar.return_value = return_value
    return mock_result


def _make_service() -> tuple[LowCodePageVersionService, AsyncMock]:
    db = AsyncMock()
    # db.add is sync on AsyncSession; avoid unused-coroutine warnings
    db.add = MagicMock()
    svc = LowCodePageVersionService(db)
    return svc, db


# ---------------------------------------------------------------------------
# 1. create_snapshot creates version record with correct version number
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.unit
async def test_create_snapshot_version_number():
    """create_snapshot 应创建版本号为 max_version + 1 的版本记录。"""
    svc, db = _make_service()

    page = _make_page(schema_data={"nodes": ["a"]})

    # _get_page 返回 page, _get_max_version 返回 0 (无已有版本)
    db.execute = AsyncMock(side_effect=[
        _patch_query(page),       # _get_page
        _patch_query(0),          # _get_max_version (func.max returns 0)
    ])

    with patch("app.modules.lowcode.version_service.set_create_audit"):
        result = await svc.create_snapshot("page-1", "tenant-1", label="v1", created_by="user-1")

    assert result.version == 1  # 0 + 1
    db.add.assert_called_once()


# ---------------------------------------------------------------------------
# 2. create_snapshot increments page current_version
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.unit
async def test_create_snapshot_increments_current_version():
    """create_snapshot 应将 page.current_version 更新为新版本号。"""
    svc, db = _make_service()

    page = _make_page(current_version=3, publish_count=2)

    db.execute = AsyncMock(side_effect=[
        _patch_query(page),       # _get_page
        _patch_query(3),          # _get_max_version -> 3
    ])

    with patch("app.modules.lowcode.version_service.set_create_audit"):
        await svc.create_snapshot("page-1", "tenant-1")

    assert page.current_version == 4


# ---------------------------------------------------------------------------
# 3. create_snapshot increments page publish_count
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.unit
async def test_create_snapshot_increments_publish_count():
    """create_snapshot 应将 page.publish_count + 1。"""
    svc, db = _make_service()

    page = _make_page(current_version=0, publish_count=5)

    db.execute = AsyncMock(side_effect=[
        _patch_query(page),
        _patch_query(0),
    ])

    with patch("app.modules.lowcode.version_service.set_create_audit"):
        await svc.create_snapshot("page-1", "tenant-1")

    assert page.publish_count == 6


# ---------------------------------------------------------------------------
# 4. get_versions returns versions in descending order
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_versions_descending():
    """get_versions 应返回按版本号降序排列的列表。"""
    svc, db = _make_service()

    v3 = _make_version(version=3, snapshot_label="v3")
    v2 = _make_version(version=2, snapshot_label="v2")
    v1 = _make_version(version=1, snapshot_label="v1")

    # 模拟 execute 返回降序结果 (已经在 mock 中排好序)
    db.execute = AsyncMock(return_value=_patch_query([v3, v2, v1]))

    result = await svc.get_versions("page-1", "tenant-1")

    assert len(result) == 3
    assert [r.version for r in result] == [3, 2, 1]


# ---------------------------------------------------------------------------
# 5. rollback_to_version restores schema_data from target version
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.unit
async def test_rollback_restores_schema_data():
    """rollback_to_version 应将 page.schema_data 替换为目标版本的 schema_data。"""
    svc, db = _make_service()

    old_schema = {"nodes": ["old"]}
    target_schema = {"nodes": ["restored"]}

    page = _make_page(schema_data=old_schema, current_version=5, publish_count=10)
    target_ver = _make_version(
        version_id="ver-target",
        version=2,
        schema_data=target_schema,
        data_sources=["ds1"],
    )

    db.execute = AsyncMock(side_effect=[
        _patch_query(page),       # _get_page
        _patch_query(target_ver), # get_version
        _patch_query(5),          # _get_max_version -> 5
    ])

    with patch("app.modules.lowcode.version_service.set_create_audit"):
        result = await svc.rollback_to_version("page-1", "ver-target", "tenant-1")

    assert result.schema_data == target_schema


# ---------------------------------------------------------------------------
# 6. rollback_to_version creates a new version record (rollback itself is versioned)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.unit
async def test_rollback_creates_new_version_record():
    """rollback_to_version 应创建一条新的版本记录，版本号为 max_version + 1。"""
    svc, db = _make_service()

    page = _make_page(current_version=5, publish_count=10)
    target_ver = _make_version(
        version_id="ver-target",
        version=3,
        schema_data={"nodes": ["v3"]},
        data_sources=["ds-x"],
    )

    db.execute = AsyncMock(side_effect=[
        _patch_query(page),
        _patch_query(target_ver),
        _patch_query(5),  # max version = 5
    ])

    with patch("app.modules.lowcode.version_service.set_create_audit"):
        await svc.rollback_to_version("page-1", "ver-target", "tenant-1")

    # db.add 被调用一次 (新的 rollback 版本记录)
    db.add.assert_called_once()
    added_obj = db.add.call_args[0][0]
    assert added_obj.version == 6  # 5 + 1
    assert added_obj.snapshot_label == "回滚至 v3"


# ---------------------------------------------------------------------------
# 7. get_latest_version returns the most recent version
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_latest_version():
    """get_latest_version 应返回版本号最大的那条记录。"""
    svc, db = _make_service()

    latest = _make_version(version=7, snapshot_label="latest")

    db.execute = AsyncMock(return_value=_patch_query(latest))

    result = await svc.get_latest_version("page-1")

    assert result is not None
    assert result.version == 7


# ---------------------------------------------------------------------------
# edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.unit
async def test_create_snapshot_page_not_found_raises():
    """页面不存在时应抛出 ValueError。"""
    svc, db = _make_service()

    db.execute = AsyncMock(return_value=_patch_query(None))

    with pytest.raises(ValueError, match="页面不存在"):
        await svc.create_snapshot("nonexistent", "tenant-1")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_rollback_version_not_found_raises():
    """目标版本不存在时应抛出 ValueError。"""
    svc, db = _make_service()

    page = _make_page()
    db.execute = AsyncMock(side_effect=[
        _patch_query(page),
        _patch_query(None),  # version not found
    ])

    with pytest.raises(ValueError, match="版本不存在"):
        await svc.rollback_to_version("page-1", "ver-missing", "tenant-1")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_rollback_version_wrong_page_raises():
    """目标版本不属于当前页面时应抛出 ValueError。"""
    svc, db = _make_service()

    page = _make_page(page_id="page-1")
    wrong_page_ver = _make_version(page_id="page-2", version=1)

    db.execute = AsyncMock(side_effect=[
        _patch_query(page),
        _patch_query(wrong_page_ver),
    ])

    with pytest.raises(ValueError, match="版本不存在"):
        await svc.rollback_to_version("page-1", "ver-wrong", "tenant-1")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_version_by_id():
    """get_version 应根据 ID 返回对应版本记录。"""
    svc, db = _make_service()

    ver = _make_version(version_id="ver-42", version=42)
    db.execute = AsyncMock(return_value=_patch_query(ver))

    result = await svc.get_version("ver-42")

    assert result is not None
    assert result.version == 42


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_version_not_found_returns_none():
    """版本不存在时 get_version 应返回 None。"""
    svc, db = _make_service()
    db.execute = AsyncMock(return_value=_patch_query(None))

    result = await svc.get_version("nonexistent")

    assert result is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_create_snapshot_with_existing_versions():
    """已有版本时版本号应从最大值递增。"""
    svc, db = _make_service()

    page = _make_page(schema_data={"nodes": ["x"]})

    db.execute = AsyncMock(side_effect=[
        _patch_query(page),
        _patch_query(10),  # max existing version = 10
    ])

    with patch("app.modules.lowcode.version_service.set_create_audit"):
        result = await svc.create_snapshot("page-1", "tenant-1")

    assert result.version == 11
    assert page.current_version == 11


@pytest.mark.asyncio
@pytest.mark.unit
async def test_create_snapshot_schema_data_from_page():
    """快照应从 page.schema_data 复制 schema_data 和 dataSources。"""
    svc, db = _make_service()

    page_schema = {"nodes": ["comp1"], "dataSources": [{"name": "api1"}]}
    page = _make_page(schema_data=page_schema)

    db.execute = AsyncMock(side_effect=[
        _patch_query(page),
        _patch_query(0),
    ])

    with patch("app.modules.lowcode.version_service.set_create_audit"):
        result = await svc.create_snapshot("page-1", "tenant-1")

    assert result.schema_data == page_schema
    assert result.data_sources == [{"name": "api1"}]
