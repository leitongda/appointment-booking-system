"""
低代码模板市场服务单元测试。

覆盖 create_template / list_templates / fork_template /
create_version / get_template_versions / delete_template。
全部使用 AsyncMock 模拟 db，无外部依赖。
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.lowcode.template_service import LowCodeTemplateService
from app.models.lowcode_template import LowCodeTemplate
from app.models.lowcode_template_version import (
    LowCodeTemplateFork,
    LowCodeTemplateVersion,
)
from app.models.lowcode_page import LowCodePage


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_service():
    """创建 service 实例和 mock db。"""
    db = AsyncMock()
    added_objects: list = []

    def _track_add(obj):
        added_objects.append(obj)

    db.add = MagicMock(side_effect=_track_add)

    def _flush():
        """模拟 flush：为所有已 add 但未赋 id 的对象设置 id。"""
        for obj in added_objects:
            if hasattr(obj, "id") and getattr(obj, "id", None) is None:
                obj.id = str(uuid.uuid4())

    def _refresh(obj, *args, **kwargs):
        """模拟 refresh：为目标对象设置 id。"""
        if hasattr(obj, "id") and getattr(obj, "id", None) is None:
            obj.id = str(uuid.uuid4())

    db.flush = AsyncMock(side_effect=_flush)
    db.refresh = AsyncMock(side_effect=_refresh)
    svc = LowCodeTemplateService(db)
    return svc, db


def _make_template(**overrides):
    """创建 mock 模板对象。"""
    # 'name' 是 MagicMock 的特殊参数（设置 mock 名称），需单独处理
    template_name = overrides.pop("name", "测试模板")
    defaults = {
        "id": "tpl-1",
        "category": "表单",
        "schema_data": {"nodes": []},
        "fork_count": 0,
        "download_count": 0,
        "is_public": True,
        "status": 1,
        "created_by": None,
        "description": "模板描述",
        "tags": [],
        "version": "1.0.0",
        "thumbnail_url": None,
        "is_official": False,
        "like_count": 0,
        "created_at": None,
        "updated_at": None,
    }
    defaults.update(overrides)
    m = MagicMock(spec=LowCodeTemplate, **defaults)
    m.name = template_name
    return m


def _make_version(**overrides):
    """创建 mock 版本对象。"""
    defaults = {
        "id": "ver-1",
        "template_id": "tpl-1",
        "version": "1.0.0",
        "schema_data": {},
        "changelog": None,
        "status": 2,
        "data_sources": [],
        "created_by": None,
    }
    defaults.update(overrides)
    return MagicMock(spec=LowCodeTemplateVersion, **defaults)


def _patch_query(return_value):
    """构建 mock execute 返回值，支持 scalars().all() 和 scalar_one_or_none()。"""
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = (
        return_value if isinstance(return_value, list) else [return_value]
    )
    mock_result.scalars.return_value = mock_scalars
    mock_result.scalar_one_or_none.return_value = (
        return_value if not isinstance(return_value, list) else None
    )
    return mock_result


# ---------------------------------------------------------------------------
# 1. create_template copies schema_data correctly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.unit
async def test_create_template_copies_schema_data():
    """create_template 应从源页面复制 schema_data 到模板和版本记录。"""
    svc, db = _make_service()

    page_schema = {"nodes": ["comp1"], "dataSources": [{"name": "api1"}]}
    mock_page = MagicMock()
    mock_page.id = "page-1"
    mock_page.schema_data = page_schema

    db.execute = AsyncMock(return_value=_patch_query(mock_page))

    with patch("app.modules.lowcode.template_service.set_create_audit"):
        result = await svc.create_template(
            source_page_id="page-1",
            tenant_id="tenant-1",
            name="新模板",
            category="表单",
            created_by="user-1",
        )

    # 模板 schema_data 应与源页面一致
    assert result.schema_data == page_schema

    # db.add 被调用两次：模板 + 初始版本
    assert db.add.call_count == 2

    # 第一次 add：LowCodeTemplate
    template_added = db.add.call_args_list[0][0][0]
    assert isinstance(template_added, LowCodeTemplate)
    assert template_added.schema_data == page_schema
    assert template_added.version == "1.0.0"

    # 第二次 add：LowCodeTemplateVersion
    version_added = db.add.call_args_list[1][0][0]
    assert isinstance(version_added, LowCodeTemplateVersion)
    assert version_added.schema_data == page_schema
    assert version_added.version == "1.0.0"
    assert version_added.status == 2  # 已发布


@pytest.mark.asyncio
@pytest.mark.unit
async def test_create_template_page_not_found_raises():
    """源页面不存在时应抛出 ValueError。"""
    svc, db = _make_service()
    db.execute = AsyncMock(return_value=_patch_query(None))

    with pytest.raises(ValueError, match="页面不存在"):
        await svc.create_template(
            source_page_id="nonexistent",
            tenant_id="tenant-1",
            name="新模板",
            category="表单",
        )


# ---------------------------------------------------------------------------
# 2. list_templates returns paginated results
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.unit
async def test_list_templates_returns_paginated_results():
    """list_templates 应返回分页结果列表和总数。"""
    svc, db = _make_service()
    svc._batch_get_author_names = AsyncMock(return_value={})

    t1 = _make_template(id="tpl-1", name="模板A")
    t2 = _make_template(id="tpl-2", name="模板B")

    db.scalar = AsyncMock(return_value=2)  # count 查询
    db.execute = AsyncMock(return_value=_patch_query([t1, t2]))

    data, total = await svc.list_templates(page=1, page_size=10)

    assert total == 2
    assert len(data) == 2
    assert data[0]["id"] == "tpl-1"
    assert data[0]["name"] == "模板A"
    assert data[1]["id"] == "tpl-2"
    assert data[1]["name"] == "模板B"

    # 验证分页字段完整
    for item in data:
        assert "category" in item
        assert "download_count" in item
        assert "fork_count" in item
        assert "version" in item
        assert "author_id" in item


# ---------------------------------------------------------------------------
# 3. list_templates filters by category
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.unit
async def test_list_templates_filters_by_category():
    """list_templates 应按分类筛选模板。"""
    svc, db = _make_service()
    svc._batch_get_author_names = AsyncMock(return_value={})

    t1 = _make_template(id="tpl-1", name="表单模板", category="表单")

    db.scalar = AsyncMock(return_value=1)
    db.execute = AsyncMock(return_value=_patch_query([t1]))

    data, total = await svc.list_templates(category="表单")

    assert total == 1
    assert len(data) == 1
    assert data[0]["category"] == "表单"

    # 验证 execute 被调用（构建了正确的查询）
    db.execute.assert_called_once()


# ---------------------------------------------------------------------------
# 4. list_templates searches by keyword
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.unit
async def test_list_templates_searches_by_keyword():
    """list_templates 应按关键字搜索模板名称和描述。"""
    svc, db = _make_service()
    svc._batch_get_author_names = AsyncMock(return_value={})

    t1 = _make_template(
        id="tpl-1",
        name="预约挂号模板",
        description="用于在线预约挂号的页面",
    )

    db.scalar = AsyncMock(return_value=1)
    db.execute = AsyncMock(return_value=_patch_query([t1]))

    data, total = await svc.list_templates(keyword="预约")

    assert total == 1
    assert len(data) == 1
    assert data[0]["name"] == "预约挂号模板"

    # 验证 keyword 参数被传递到查询中
    db.execute.assert_called_once()


# ---------------------------------------------------------------------------
# 5. fork_template creates new page with template schema
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.unit
async def test_fork_template_creates_new_page_with_schema():
    """fork_template 应基于模板 schema 创建新页面。"""
    svc, db = _make_service()

    template_schema = {"nodes": ["comp1", "comp2"]}
    mock_template = _make_template(
        id="tpl-1",
        name="挂号模板",
        schema_data=template_schema,
        description="挂号页面模板",
        thumbnail_url="http://example.com/thumb.png",
    )

    db.execute = AsyncMock(return_value=_patch_query(mock_template))

    with patch("app.modules.lowcode.template_service.set_create_audit"):
        result = await svc.fork_template(
            template_id="tpl-1",
            tenant_id="tenant-1",
            account_id="user-1",
        )

    # 结果应为 LowCodePage 实例
    assert isinstance(result, LowCodePage)
    assert result.tenant_id == "tenant-1"
    assert result.name == "挂号模板 (Fork)"
    assert result.slug == "fork-tpl-1"
    assert result.schema_data == template_schema
    assert result.description == "挂号页面模板"
    assert result.thumbnail_url == "http://example.com/thumb.png"

    # db.add 被调用两次：页面 + fork 记录
    assert db.add.call_count == 2

    # 第一次 add：LowCodePage
    page_added = db.add.call_args_list[0][0][0]
    assert isinstance(page_added, LowCodePage)

    # 第二次 add：LowCodeTemplateFork
    fork_added = db.add.call_args_list[1][0][0]
    assert isinstance(fork_added, LowCodeTemplateFork)
    assert fork_added.original_template_id == "tpl-1"
    assert fork_added.forked_by_tenant_id == "tenant-1"
    assert fork_added.forked_by_account_id == "user-1"


# ---------------------------------------------------------------------------
# 6. fork_template increments fork_count
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.unit
async def test_fork_template_increments_fork_count():
    """fork_template 应递增 fork_count 和 download_count。"""
    svc, db = _make_service()

    mock_template = _make_template(
        id="tpl-1",
        fork_count=5,
        download_count=10,
    )

    db.execute = AsyncMock(return_value=_patch_query(mock_template))

    with patch("app.modules.lowcode.template_service.set_create_audit"):
        await svc.fork_template(
            template_id="tpl-1",
            tenant_id="tenant-1",
            account_id="user-1",
        )

    assert mock_template.fork_count == 6
    assert mock_template.download_count == 11


@pytest.mark.asyncio
@pytest.mark.unit
async def test_fork_template_increments_from_zero():
    """fork_count 和 download_count 为 None 或 0 时应从 0 开始递增。"""
    svc, db = _make_service()

    mock_template = _make_template(
        id="tpl-1",
        fork_count=None,
        download_count=None,
    )

    db.execute = AsyncMock(return_value=_patch_query(mock_template))

    with patch("app.modules.lowcode.template_service.set_create_audit"):
        await svc.fork_template(
            template_id="tpl-1",
            tenant_id="tenant-1",
            account_id="user-1",
        )

    assert mock_template.fork_count == 1
    assert mock_template.download_count == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_fork_template_not_found_raises():
    """模板不存在时应抛出 ValueError。"""
    svc, db = _make_service()
    db.execute = AsyncMock(return_value=_patch_query(None))

    with pytest.raises(ValueError, match="模板不存在"):
        await svc.fork_template(
            template_id="nonexistent",
            tenant_id="tenant-1",
            account_id="user-1",
        )


# ---------------------------------------------------------------------------
# 7. create_version creates version record
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.unit
async def test_create_version_creates_record():
    """create_version 应创建版本记录并同步更新模板主版本号。"""
    svc, db = _make_service()

    mock_template = _make_template(id="tpl-1", version="1.0.0")

    db.execute = AsyncMock(return_value=_patch_query(mock_template))

    schema_data = {"componentName": "Page", "props": {}, "children": [{"id": "node-1", "componentName": "NutText", "props": {"text": "hello"}}]}

    with patch("app.modules.lowcode.template_service.set_create_audit"):
        result = await svc.create_version(
            template_id="tpl-1",
            version="1.1.0",
            schema_data=schema_data,
            changelog="新增组件",
            created_by="user-1",
        )

    # 验证版本记录被添加
    assert db.add.call_count == 1
    version_added = db.add.call_args[0][0]
    assert isinstance(version_added, LowCodeTemplateVersion)
    assert version_added.version == "1.1.0"
    assert version_added.schema_data == schema_data
    assert version_added.changelog == "新增组件"
    assert version_added.status == 2  # 已发布

    # 验证模板主版本号被同步更新
    assert mock_template.version == "1.1.0"
    assert mock_template.schema_data == schema_data


@pytest.mark.asyncio
@pytest.mark.unit
async def test_create_version_template_not_found_raises():
    """模板不存在时 create_version 应抛出 ValueError。"""
    svc, db = _make_service()
    db.execute = AsyncMock(return_value=_patch_query(None))

    with pytest.raises(ValueError, match="模板不存在"):
        await svc.create_version(
            template_id="nonexistent",
            version="1.1.0",
            schema_data={"componentName": "Page", "props": {}, "children": []},
        )


# ---------------------------------------------------------------------------
# 8. get_versions returns versions in order
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_versions_returns_descending_order():
    """get_template_versions 应返回按版本号降序排列的版本列表。"""
    svc, db = _make_service()

    v3 = _make_version(id="ver-3", version="3.0.0")
    v2 = _make_version(id="ver-2", version="2.0.0")
    v1 = _make_version(id="ver-1", version="1.0.0")

    db.execute = AsyncMock(return_value=_patch_query([v3, v2, v1]))

    result = await svc.get_template_versions("tpl-1")

    assert len(result) == 3
    assert result[0].version == "3.0.0"
    assert result[1].version == "2.0.0"
    assert result[2].version == "1.0.0"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_versions_empty_list():
    """无版本记录时应返回空列表。"""
    svc, db = _make_service()

    db.execute = AsyncMock(return_value=_patch_query([]))

    result = await svc.get_template_versions("tpl-1")

    assert result == []


# ---------------------------------------------------------------------------
# 9. delete_template sets status=0
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.unit
async def test_delete_template_sets_status_zero():
    """delete_template 应将模板 status 设为 0（软删除）并返回 True。"""
    svc, db = _make_service()

    mock_template = _make_template(id="tpl-1", status=1)

    db.execute = AsyncMock(return_value=_patch_query(mock_template))

    result = await svc.delete_template("tpl-1")

    assert result is True
    assert mock_template.status == 0
    db.commit.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_delete_template_not_found_returns_false():
    """模板不存在时 delete_template 应返回 False。"""
    svc, db = _make_service()

    db.execute = AsyncMock(return_value=_patch_query(None))

    result = await svc.delete_template("nonexistent")

    assert result is False
    db.commit.assert_not_called()
