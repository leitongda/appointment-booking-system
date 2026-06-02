"""codegen_service.py 单元测试。

测试 CodegenService 的公开方法及内部解析逻辑。
由于实际代码生成依赖 Node.js subprocess，测试通过 mock 隔离外部依赖，
重点验证:
  - 数据流转 (schema -> subprocess input -> CodegenResult)
  - 结果解析 (_parse_result 的类型映射和边界处理)
  - 错误处理 (无效 schema、空 schema、subprocess 失败等)

注意: app.modules.lowcode.__init__.py 导入 router 会触发 app.db.session 模块加载，
后者在 import 时创建 PostgreSQL 连接池。单元测试中需要预先 mock 该模块以避免
SQLite 不支持 pool_size 等参数的错误。
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# 在导入 codegen_service 之前，mock 掉 app.db.session 以避免创建真实连接池
_db_session_mock = MagicMock()
_db_session_mock.get_db = AsyncMock()
_db_session_mock.get_sync_db_session = MagicMock()
sys.modules.setdefault("app.db.session", _db_session_mock)

from app.modules.lowcode.codegen_service import (
    CodegenError,
    CodegenResult,
    CodegenService,
    GeneratedFile,
    GeneratedFileType,
    _count_nodes,
    _get_codegen_bin,
    _get_node_cmd,
    _get_timeout,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db():
    """Mock 数据库会话。"""
    return AsyncMock()


@pytest.fixture
def service(mock_db):
    """创建 CodegenService 实例。"""
    return CodegenService(db=mock_db)


def _make_page(schema_data: dict | None = None, **overrides) -> SimpleNamespace:
    """构造模拟的 LowCodePage 对象。"""
    defaults = {
        "id": str(uuid4()),
        "tenant_id": str(uuid4()),
        "name": "测试页面",
        "slug": "test-page",
        "schema_data": schema_data or {},
        "status": 0,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_taro_schema(
    title: str = "测试页面",
    children: list | None = None,
    data_sources: list | None = None,
    state: dict | None = None,
) -> dict:
    """构造 Taro 目标平台的 schema。"""
    schema: dict = {
        "componentName": "View",
        "props": {"navigationBarTitleText": title},
        "children": children or [],
    }
    if data_sources:
        schema["dataSources"] = data_sources
    if state:
        schema["state"] = state
    return schema


def _make_subprocess_output(
    files: list[dict] | None = None,
    warnings: list | None = None,
    dependencies: list | None = None,
    metadata: dict | None = None,
) -> bytes:
    """构造 Node.js codegen 的标准 JSON 输出。"""
    result = {
        "files": files or [
            {
                "path": "pages/test_page/index.tsx",
                "content": "export default function TestPage() { return <View>Hello</View>; }",
                "type": "tsx",
            }
        ],
        "warnings": warnings or [],
        "dependencies": dependencies or [],
        "metadata": metadata or {"target": "taro"},
    }
    return json.dumps(result, ensure_ascii=False).encode("utf-8")


# ---------------------------------------------------------------------------
# test_generate_taro_page
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_taro_page(service, mock_db):
    """测试基本页面代码生成 — 从数据库加载 schema 并调用 codegen。"""
    page = _make_page(schema_data=_make_taro_schema())
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = page
    mock_db.execute.return_value = mock_result

    fake_output = _make_subprocess_output()

    with patch.object(service, "_run_codegen", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = CodegenResult(
            files=[GeneratedFile(path="pages/test_page/index.tsx", content="code", type=GeneratedFileType.TSX)],
            warnings=[],
            dependencies=["@tarojs/components"],
            metadata={"target": "taro"},
        )

        result = await service.generate_taro(page.id, page.tenant_id)

        # 验证 _run_codegen 被正确调用
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        assert call_kwargs[1]["target"] == "taro"
        assert call_kwargs[1]["schema"]["componentName"] == "View"

        # 验证返回值结构
        assert isinstance(result, CodegenResult)
        assert len(result.files) == 1
        assert result.files[0].type == GeneratedFileType.TSX
        assert "@tarojs/components" in result.dependencies


@pytest.mark.asyncio
async def test_generate_taro_page_with_children(service, mock_db):
    """测试带子组件的页面生成。"""
    children = [
        {"componentName": "NutText", "props": {"text": "标题"}},
        {"componentName": "NutButton", "props": {"text": "提交"}},
    ]
    schema = _make_taro_schema(children=children)
    page = _make_page(schema_data=schema)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = page
    mock_db.execute.return_value = mock_result

    with patch.object(service, "_run_codegen", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = CodegenResult(
            files=[GeneratedFile(path="pages/test_page/index.tsx", content="code", type=GeneratedFileType.TSX)],
        )

        result = await service.generate_taro(page.id, page.tenant_id)

        # 验证 schema 中包含 children
        call_schema = mock_run.call_args[1]["schema"]
        assert len(call_schema["children"]) == 2
        assert call_schema["children"][0]["componentName"] == "NutText"


# ---------------------------------------------------------------------------
# test_generate_taro_component
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_taro_component(service, mock_db):
    """测试组件代码生成 — 通过 preview_codegen 直接传入组件 schema。"""
    component_schema = {
        "componentName": "NutButton",
        "props": {"text": "点击我", "type": "primary"},
    }

    with patch.object(service, "_run_codegen", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = CodegenResult(
            files=[
                GeneratedFile(path="components/button/index.tsx", content="component code", type=GeneratedFileType.TSX),
                GeneratedFile(path="components/button/index.module.css", content=".btn {}", type=GeneratedFileType.CSS),
            ],
            metadata={"target": "taro", "components": ["NutButton"]},
        )

        result = await service.preview_codegen(component_schema, data_sources=[], target="taro")

        assert len(result.files) == 2
        assert result.files[0].type == GeneratedFileType.TSX
        assert result.files[1].type == GeneratedFileType.CSS

        # 验证 preview 模式传入 options
        call_options = mock_run.call_args[1]["options"]
        assert call_options.get("preview") is True


# ---------------------------------------------------------------------------
# test_generate_with_data_binding
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_with_data_binding(service, mock_db):
    """测试数据绑定表达式生成 — 含 dataSources 和 state。"""
    data_sources = [
        {"id": "userInfo", "url": "/api/user", "method": "GET", "dataPath": "result"},
    ]
    state = {
        "loading": {"defaultValue": True},
        "count": {"defaultValue": 0},
    }
    schema = _make_taro_schema(data_sources=data_sources, state=state)
    page = _make_page(schema_data=schema)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = page
    mock_db.execute.return_value = mock_result

    with patch.object(service, "_run_codegen", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = CodegenResult(
            files=[GeneratedFile(path="pages/test_page/index.tsx", content="bound code", type=GeneratedFileType.TSX)],
            dependencies=["@tarojs/taro"],
            metadata={"target": "taro", "dataSources": ["userInfo"]},
        )

        result = await service.generate_taro(page.id, page.tenant_id)

        # 验证 dataSources 和 state 被传递给 codegen
        call_kwargs = mock_run.call_args[1]
        assert len(call_kwargs["data_sources"]) == 1
        assert call_kwargs["data_sources"][0]["id"] == "userInfo"
        assert "loading" in call_kwargs["state"]
        assert call_kwargs["state"]["count"]["defaultValue"] == 0

        assert "@tarojs/taro" in result.dependencies
        assert "userInfo" in result.metadata["dataSources"]


# ---------------------------------------------------------------------------
# test_generate_with_events
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_with_events(service, mock_db):
    """测试事件处理代码生成 — 含 onClick 等事件绑定的 schema。"""
    children = [
        {
            "componentName": "NutButton",
            "props": {"text": "提交"},
            "events": {"onClick": {"type": "navigate", "url": "/pages/result"}},
        }
    ]
    schema = _make_taro_schema(children=children)
    page = _make_page(schema_data=schema)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = page
    mock_db.execute.return_value = mock_result

    with patch.object(service, "_run_codegen", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = CodegenResult(
            files=[GeneratedFile(path="pages/test_page/index.tsx", content="event code", type=GeneratedFileType.TSX)],
            warnings=[{"level": "info", "message": "Event handler generated for onClick"}],
        )

        result = await service.generate_taro(page.id, page.tenant_id)

        call_schema = mock_run.call_args[1]["schema"]
        button_node = call_schema["children"][0]
        assert "events" in button_node
        assert button_node["events"]["onClick"]["type"] == "navigate"

        assert len(result.warnings) == 1
        assert result.warnings[0]["level"] == "info"


# ---------------------------------------------------------------------------
# test_generate_with_loop
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_with_loop(service, mock_db):
    """测试循环渲染代码生成 — 含 for 循环绑定的 schema。"""
    children = [
        {
            "componentName": "NutView",
            "loop": {"dataSource": "listItems", "itemVar": "item"},
            "children": [
                {
                    "componentName": "NutText",
                    "props": {"text": "{{item.name}}"},
                }
            ],
        }
    ]
    schema = _make_taro_schema(children=children)
    page = _make_page(schema_data=schema)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = page
    mock_db.execute.return_value = mock_result

    with patch.object(service, "_run_codegen", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = CodegenResult(
            files=[GeneratedFile(path="pages/test_page/index.tsx", content="loop code", type=GeneratedFileType.TSX)],
        )

        result = await service.generate_taro(page.id, page.tenant_id)

        call_schema = mock_run.call_args[1]["schema"]
        loop_node = call_schema["children"][0]
        assert "loop" in loop_node
        assert loop_node["loop"]["dataSource"] == "listItems"
        assert loop_node["loop"]["itemVar"] == "item"
        assert len(loop_node["children"]) == 1


# ---------------------------------------------------------------------------
# test_invalid_schema
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_schema(service, mock_db):
    """测试无效 schema 的错误处理 — codegen 返回非 JSON 输出。"""
    page = _make_page(schema_data={"broken": True})
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = page
    mock_db.execute.return_value = mock_result

    # 直接 mock _run_codegen 以避免触发 _NODEJS_WRAPPER.format() 的大括号问题
    with patch.object(service, "_run_codegen", new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = CodegenError(
            "代码生成失败 (exit=1): SyntaxError",
            details={"returncode": 1, "error": "SyntaxError"},
        )

        with pytest.raises(CodegenError) as exc_info:
            await service.generate_taro(page.id, page.tenant_id)

        assert "代码生成失败" in str(exc_info.value)
        assert exc_info.value.details["returncode"] == 1


@pytest.mark.asyncio
async def test_codegen_bin_not_found(service, mock_db):
    """测试 codegen 入口文件不存在时的错误。"""
    page = _make_page(schema_data=_make_taro_schema())
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = page
    mock_db.execute.return_value = mock_result

    with patch(
        "app.modules.lowcode.codegen_service._get_codegen_bin",
        return_value="/nonexistent/path/index.js",
    ):
        with pytest.raises(CodegenError) as exc_info:
            await service.generate_taro(page.id, page.tenant_id)

        assert "未构建" in str(exc_info.value)
        assert "codegen_bin" in exc_info.value.details


@pytest.mark.asyncio
async def test_codegen_timeout(service, mock_db):
    """测试 codegen subprocess 超时。"""
    page = _make_page(schema_data=_make_taro_schema())
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = page
    mock_db.execute.return_value = mock_result

    # 直接 mock _run_codegen 以验证超时错误传播
    with patch.object(service, "_run_codegen", new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = CodegenError(
            "代码生成超时 (30秒)",
            details={"timeout": 30, "target": "taro"},
        )

        with pytest.raises(CodegenError) as exc_info:
            await service.generate_taro(page.id, page.tenant_id)

        assert "超时" in str(exc_info.value)
        assert exc_info.value.details["timeout"] == 30


@pytest.mark.asyncio
async def test_page_not_found(service, mock_db):
    """测试页面不存在时的错误。"""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    with pytest.raises(CodegenError) as exc_info:
        await service.generate_taro("nonexistent-page-id", "tenant-123")

    assert "页面不存在" in str(exc_info.value)
    assert exc_info.value.details["page_id"] == "nonexistent-page-id"
    assert exc_info.value.details["tenant_id"] == "tenant-123"


# ---------------------------------------------------------------------------
# test_empty_schema
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_schema(service, mock_db):
    """测试空 schema 的边界情况 — schema_data 为 {}。"""
    page = _make_page(schema_data={})
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = page
    mock_db.execute.return_value = mock_result

    with patch.object(service, "_run_codegen", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = CodegenResult(
            files=[GeneratedFile(path="pages/page/index.tsx", content="", type=GeneratedFileType.TSX)],
            warnings=[],
        )

        result = await service.generate_taro(page.id, page.tenant_id)

        # 空 schema 应被正常处理，dataSources 和 state 为空列表/dict
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["schema"] == {}
        assert call_kwargs["data_sources"] == []
        assert call_kwargs["state"] == {}

        assert len(result.files) == 1


@pytest.mark.asyncio
async def test_schema_with_none_children(service, mock_db):
    """测试 schema children 为 None 的情况。"""
    schema = {"componentName": "View", "props": {}, "children": None}
    page = _make_page(schema_data=schema)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = page
    mock_db.execute.return_value = mock_result

    with patch.object(service, "_run_codegen", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = CodegenResult(
            files=[GeneratedFile(path="pages/page/index.tsx", content="code", type=GeneratedFileType.TSX)],
        )

        result = await service.generate_taro(page.id, page.tenant_id)
        assert len(result.files) == 1


# ---------------------------------------------------------------------------
# _parse_result 静态方法测试
# ---------------------------------------------------------------------------


class TestParseResult:
    """测试 _parse_result 静态方法的各种输入。"""

    def test_parse_standard_output(self):
        """标准输出解析。"""
        output = {
            "files": [
                {"path": "pages/home/index.tsx", "content": "<View />", "type": "tsx"},
                {"path": "pages/home/index.module.css", "content": ".root {}", "type": "css"},
            ],
            "warnings": [{"level": "warn", "message": "unused prop"}],
            "dependencies": ["@tarojs/components", "react"],
            "metadata": {"target": "taro", "generatedAt": "2026-01-01T00:00:00Z"},
        }

        result = CodegenService._parse_result(output)

        assert isinstance(result, CodegenResult)
        assert len(result.files) == 2
        assert result.files[0].type == GeneratedFileType.TSX
        assert result.files[1].type == GeneratedFileType.CSS
        assert len(result.warnings) == 1
        assert result.dependencies == ["@tarojs/components", "react"]
        assert result.metadata["target"] == "taro"

    def test_parse_native_file_types(self):
        """原生小程序文件类型解析。"""
        output = {
            "files": [
                {"path": "pages/home.wxml", "content": "<view></view>", "type": "wxml"},
                {"path": "pages/home.wxss", "content": ".page {}", "type": "wxss"},
                {"path": "pages/home.js", "content": "Page({})", "type": "js"},
                {"path": "pages/home.json", "content": "{}", "type": "json"},
            ],
        }

        result = CodegenService._parse_result(output)

        assert len(result.files) == 4
        assert result.files[0].type == GeneratedFileType.WXML
        assert result.files[1].type == GeneratedFileType.WXSS
        assert result.files[2].type == GeneratedFileType.JS
        assert result.files[3].type == GeneratedFileType.JSON

    def test_parse_unknown_file_type_falls_back_to_tsx(self):
        """未知文件类型回退为 TSX。"""
        output = {
            "files": [{"path": "test.xyz", "content": "data", "type": "unknown_type"}],
        }

        result = CodegenService._parse_result(output)

        assert len(result.files) == 1
        assert result.files[0].type == GeneratedFileType.TSX  # fallback

    def test_parse_missing_fields(self):
        """缺失字段使用默认值。"""
        output = {
            "files": [{}],  # 所有字段缺失
        }

        result = CodegenService._parse_result(output)

        assert len(result.files) == 1
        assert result.files[0].path == "unknown"
        assert result.files[0].content == ""
        assert result.files[0].type == GeneratedFileType.TSX

    def test_parse_empty_output(self):
        """空输出。"""
        result = CodegenService._parse_result({})

        assert isinstance(result, CodegenResult)
        assert result.files == []
        assert result.warnings == []
        assert result.dependencies == []
        assert result.metadata == {}

    def test_parse_no_files_key(self):
        """输出中无 files 字段。"""
        result = CodegenService._parse_result({"warnings": ["just a warning"]})

        assert result.files == []
        assert result.warnings == ["just a warning"]


# ---------------------------------------------------------------------------
# GeneratedFile / CodegenResult 数据类测试
# ---------------------------------------------------------------------------


class TestDataClasses:
    """测试数据类的序列化。"""

    def test_generated_file_to_dict(self):
        f = GeneratedFile(path="test.tsx", content="code", type=GeneratedFileType.TSX)
        d = f.to_dict()
        assert d == {"path": "test.tsx", "content": "code", "type": "tsx"}

    def test_codegen_result_to_dict(self):
        result = CodegenResult(
            files=[GeneratedFile(path="a.tsx", content="x", type=GeneratedFileType.TSX)],
            warnings=[{"msg": "warn"}],
            dependencies=["react"],
            metadata={"target": "taro"},
        )
        d = result.to_dict()
        assert len(d["files"]) == 1
        assert d["files"][0]["type"] == "tsx"
        assert d["warnings"] == [{"msg": "warn"}]
        assert d["dependencies"] == ["react"]

    def test_codegen_result_defaults(self):
        result = CodegenResult()
        assert result.files == []
        assert result.warnings == []
        assert result.dependencies == []
        assert result.metadata == {}


# ---------------------------------------------------------------------------
# _count_nodes 辅助函数测试
# ---------------------------------------------------------------------------


class TestCountNodes:
    """测试 schema 节点计数。"""

    def test_single_node(self):
        assert _count_nodes({"componentName": "View"}) == 1

    def test_nested_children(self):
        schema = {
            "componentName": "View",
            "children": [
                {"componentName": "Text"},
                {"componentName": "Button", "children": [{"componentName": "Icon"}]},
            ],
        }
        assert _count_nodes(schema) == 4  # View + Text + Button + Icon

    def test_empty_children(self):
        assert _count_nodes({"children": []}) == 1

    def test_no_children_key(self):
        assert _count_nodes({}) == 1

    def test_deeply_nested(self):
        schema = {
            "children": [
                {
                    "children": [
                        {"children": [{"children": []}]}
                    ]
                }
            ]
        }
        assert _count_nodes(schema) == 4


# ---------------------------------------------------------------------------
# 环境变量配置测试
# ---------------------------------------------------------------------------


class TestConfigHelpers:
    """测试配置读取函数。"""

    def test_get_codegen_bin_default(self):
        with patch.dict(os.environ, {}, clear=True):
            result = _get_codegen_bin()
            assert result.endswith("packages/codegen/dist/index.js")

    def test_get_codegen_bin_custom(self):
        with patch.dict(os.environ, {"CODEGEN_BIN": "/custom/path.js"}):
            assert _get_codegen_bin() == "/custom/path.js"

    def test_get_node_cmd_default(self):
        with patch.dict(os.environ, {}, clear=True):
            assert _get_node_cmd() == "node"

    def test_get_node_cmd_custom(self):
        with patch.dict(os.environ, {"CODEGEN_NODE_CMD": "/usr/local/bin/node18"}):
            assert _get_node_cmd() == "/usr/local/bin/node18"

    def test_get_timeout_default(self):
        with patch.dict(os.environ, {}, clear=True):
            assert _get_timeout() == 30

    def test_get_timeout_custom(self):
        with patch.dict(os.environ, {"CODEGEN_TIMEOUT": "60"}):
            assert _get_timeout() == 60

    def test_get_timeout_invalid_falls_back(self):
        with patch.dict(os.environ, {"CODEGEN_TIMEOUT": "not_a_number"}):
            assert _get_timeout() == 30


# ---------------------------------------------------------------------------
# CodegenError 测试
# ---------------------------------------------------------------------------


class TestCodegenError:
    """测试自定义异常。"""

    def test_basic_message(self):
        err = CodegenError("something failed")
        assert str(err) == "something failed"
        assert err.details == {}

    def test_with_details(self):
        details = {"returncode": 1, "raw": "syntax error"}
        err = CodegenError("failed", details=details)
        assert err.details == details


# ---------------------------------------------------------------------------
# generate_native 测试
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_native(service, mock_db):
    """测试原生微信小程序代码生成。"""
    page = _make_page(schema_data=_make_taro_schema())
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = page
    mock_db.execute.return_value = mock_result

    with patch.object(service, "_run_codegen", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = CodegenResult(
            files=[
                GeneratedFile(path="pages/test_page.wxml", content="<view></view>", type=GeneratedFileType.WXML),
                GeneratedFile(path="pages/test_page.wxss", content=".page {}", type=GeneratedFileType.WXSS),
                GeneratedFile(path="pages/test_page.js", content="Page({})", type=GeneratedFileType.JS),
                GeneratedFile(path="pages/test_page.json", content="{}", type=GeneratedFileType.JSON),
            ],
            dependencies=["wx"],
            metadata={"target": "native"},
        )

        result = await service.generate_native(page.id, page.tenant_id)

        # 验证 target 为 native
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["target"] == "native"

        # 验证返回 4 个原生文件
        assert len(result.files) == 4
        file_types = {f.type for f in result.files}
        assert GeneratedFileType.WXML in file_types
        assert GeneratedFileType.WXSS in file_types
        assert GeneratedFileType.JS in file_types
        assert GeneratedFileType.JSON in file_types
        assert "wx" in result.dependencies
