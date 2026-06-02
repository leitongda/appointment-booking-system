"""低代码模块 schemas 单元测试。"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.modules.lowcode.schemas import (
    CodegenPreviewRequest,
    CodegenResultSchema,
    DataSourceTestRequest,
    DataSourceTestResponse,
    DataPreviewResponse,
    DeployRollbackRequest,
    DeployResultResponse,
    RollbackRequest,
    VersionItem,
    VersionListResponse,
    WeChatAuditCallbackRequest,
    GeneratedFileSchema,
)
from app.schemas.lowcode import (
    LowCodePageCreate,
    LowCodePageUpdate,
    LowCodePageResponse,
)

VALID_COMPONENT_NODE = {
    "componentName": "View",
    "props": {"className": "container"},
    "children": [],
}


class TestPageCreateValid:
    """测试有效页面创建数据。"""

    def test_minimal_valid(self):
        """最小必填字段创建。"""
        page = LowCodePageCreate(name="首页", slug="home")
        assert page.name == "首页"
        assert page.slug == "home"
        assert page.description is None
        assert page.schema_data == {}
        assert page.thumbnail_url is None
        assert page.miniapp_instance_id is None

    def test_full_fields(self):
        """全部字段创建。"""
        page = LowCodePageCreate(
            name="预约页面",
            slug="booking",
            description="患者预约挂号页面",
            schema_data=VALID_COMPONENT_NODE,
            thumbnail_url="https://example.com/thumb.png",
            miniapp_instance_id="inst-001",
        )
        assert page.name == "预约页面"
        assert page.slug == "booking"
        assert page.description == "患者预约挂号页面"
        assert page.schema_data == VALID_COMPONENT_NODE
        assert page.thumbnail_url == "https://example.com/thumb.png"
        assert page.miniapp_instance_id == "inst-001"

    def test_name_max_length_boundary(self):
        """名称恰好 100 字符。"""
        name = "a" * 100
        page = LowCodePageCreate(name=name, slug="ok")
        assert page.name == name

    def test_slug_max_length_boundary(self):
        """slug 恰好 100 字符。"""
        slug = "x" * 100
        page = LowCodePageCreate(name="ok", slug=slug)
        assert page.slug == slug

    def test_camel_case_serialization(self):
        """camelCase 序列化。"""
        page = LowCodePageCreate(name="test", slug="t", schema_data=VALID_COMPONENT_NODE)
        dumped = page.model_dump(by_alias=True)
        assert "name" in dumped  # name 不含下划线，保持不变
        assert "slug" in dumped
        assert "schemaData" in dumped
        assert "thumbnailUrl" in dumped
        assert "miniappInstanceId" in dumped


class TestPageCreateInvalidSlug:
    """测试无效 slug 格式。"""

    def test_empty_slug(self):
        """空 slug 违反 min_length=1。"""
        with pytest.raises(ValidationError) as exc_info:
            LowCodePageCreate(name="test", slug="")
        assert "slug" in str(exc_info.value)

    def test_slug_too_long(self):
        """slug 超过 100 字符。"""
        with pytest.raises(ValidationError) as exc_info:
            LowCodePageCreate(name="test", slug="x" * 101)
        assert "slug" in str(exc_info.value)

    def test_empty_name(self):
        """空名称违反 min_length=1。"""
        with pytest.raises(ValidationError) as exc_info:
            LowCodePageCreate(name="", slug="ok")
        assert "name" in str(exc_info.value)

    def test_name_too_long(self):
        """名称超过 100 字符。"""
        with pytest.raises(ValidationError) as exc_info:
            LowCodePageCreate(name="a" * 101, slug="ok")
        assert "name" in str(exc_info.value)

    def test_description_too_long(self):
        """描述超过 500 字符。"""
        with pytest.raises(ValidationError) as exc_info:
            LowCodePageCreate(name="ok", slug="ok", description="x" * 501)
        assert "description" in str(exc_info.value)

    def test_missing_name(self):
        """缺少必填 name。"""
        with pytest.raises(ValidationError) as exc_info:
            LowCodePageCreate(slug="ok")
        assert "name" in str(exc_info.value)

    def test_missing_slug(self):
        """缺少必填 slug。"""
        with pytest.raises(ValidationError) as exc_info:
            LowCodePageCreate(name="ok")
        assert "slug" in str(exc_info.value)


class TestPageUpdatePartial:
    """测试部分更新（所有字段可选）。"""

    def test_empty_update(self):
        """空请求体合法。"""
        update = LowCodePageUpdate()
        dumped = update.model_dump(exclude_unset=True)
        assert len(dumped) == 0

    def test_partial_name_only(self):
        """只更新 name。"""
        update = LowCodePageUpdate(name="新名称")
        assert update.name == "新名称"
        assert update.slug is None
        assert update.schema_data is None

    def test_partial_status_only(self):
        """只更新 status。"""
        update = LowCodePageUpdate(status=1)
        assert update.status == 1

    def test_status_valid_values(self):
        """status 有效值: 0, 1, 2。"""
        for s in (0, 1, 2):
            update = LowCodePageUpdate(status=s)
            assert update.status == s

    def test_status_out_of_range(self):
        """status 超出 0-2 范围。"""
        with pytest.raises(ValidationError) as exc_info:
            LowCodePageUpdate(status=3)
        assert "status" in str(exc_info.value)

    def test_status_negative(self):
        """status 为负数。"""
        with pytest.raises(ValidationError) as exc_info:
            LowCodePageUpdate(status=-1)
        assert "status" in str(exc_info.value)

    def test_partial_schema_data(self):
        """只更新 schema_data。"""
        update = LowCodePageUpdate(schema_data=VALID_COMPONENT_NODE)
        assert update.schema_data == VALID_COMPONENT_NODE
        assert update.name is None

    def test_slug_update_respects_length(self):
        """slug 更新也受长度约束。"""
        with pytest.raises(ValidationError):
            LowCodePageUpdate(slug="x" * 101)


class TestSchemaDataValidation:
    """测试 schema_data 结构校验。"""

    def test_empty_schema_allowed(self):
        """空 schema_data 允许。"""
        page = LowCodePageCreate(name="ok", slug="ok", schema_data={})
        assert page.schema_data == {}

    def test_valid_component_node(self):
        """合法组件节点。"""
        schema = {
            "componentName": "View",
            "props": {"style": {"color": "red"}},
            "children": [],
        }
        page = LowCodePageCreate(name="ok", slug="ok", schema_data=schema)
        assert page.schema_data["componentName"] == "View"

    def test_missing_component_name(self):
        """缺少 componentName。"""
        schema = {"props": {}, "children": []}
        with pytest.raises(ValidationError, match="componentName"):
            LowCodePageCreate(name="ok", slug="ok", schema_data=schema)

    def test_component_name_not_string(self):
        """componentName 非字符串。"""
        schema = {"componentName": 123, "props": {}}
        with pytest.raises(ValidationError, match="componentName"):
            LowCodePageCreate(name="ok", slug="ok", schema_data=schema)

    def test_missing_props(self):
        """缺少 props。"""
        schema = {"componentName": "View"}
        with pytest.raises(ValidationError, match="props"):
            LowCodePageCreate(name="ok", slug="ok", schema_data=schema)

    def test_props_not_dict(self):
        """props 非对象。"""
        schema = {"componentName": "View", "props": "invalid"}
        with pytest.raises(ValidationError, match="props"):
            LowCodePageCreate(name="ok", slug="ok", schema_data=schema)

    def test_children_not_list(self):
        """children 非数组。"""
        schema = {"componentName": "View", "props": {}, "children": "bad"}
        with pytest.raises(ValidationError, match="children"):
            LowCodePageCreate(name="ok", slug="ok", schema_data=schema)

    def test_nested_component_validation(self):
        """子组件也需校验。"""
        schema = {
            "componentName": "Page",
            "props": {},
            "children": [
                {"componentName": "View", "props": {}},
                {"props": {}},  # 缺少 componentName
            ],
        }
        with pytest.raises(ValidationError, match="componentName"):
            LowCodePageCreate(name="ok", slug="ok", schema_data=schema)

    def test_max_depth_exceeded(self):
        """嵌套深度超过 10 层。"""
        # 构建 10 层嵌套
        node = {"componentName": "Leaf", "props": {}}
        for _ in range(10):
            node = {"componentName": "Wrapper", "props": {}, "children": [node]}
        with pytest.raises(ValidationError, match="嵌套深度"):
            LowCodePageCreate(name="ok", slug="ok", schema_data=node)

    def test_max_depth_exactly_allowed(self):
        """嵌套深度恰好 9 层（合法，< 10）。"""
        node = {"componentName": "Leaf", "props": {}}
        for _ in range(8):
            node = {"componentName": "Wrapper", "props": {}, "children": [node]}
        page = LowCodePageCreate(name="ok", slug="ok", schema_data=node)
        assert page.schema_data is not None

    def test_valid_data_sources(self):
        """合法 dataSources。"""
        schema = {
            "componentName": "Page",
            "props": {},
            "dataSources": [
                {"id": "ds1", "url": "https://api.example.com/list", "method": "GET"},
            ],
        }
        page = LowCodePageCreate(name="ok", slug="ok", schema_data=schema)
        assert len(page.schema_data["dataSources"]) == 1

    def test_data_sources_missing_id(self):
        """dataSources 缺少 id 字段。"""
        schema = {
            "componentName": "Page",
            "props": {},
            "dataSources": [
                {"url": "https://api.example.com/list", "method": "GET"},
            ],
        }
        with pytest.raises(ValidationError, match="缺少 id"):
            LowCodePageCreate(name="ok", slug="ok", schema_data=schema)

    def test_data_sources_invalid_method(self):
        """dataSources method 非法。"""
        schema = {
            "componentName": "Page",
            "props": {},
            "dataSources": [
                {"id": "ds1", "url": "https://api.example.com/list", "method": "PATCH"},
            ],
        }
        with pytest.raises(ValidationError, match="method"):
            LowCodePageCreate(name="ok", slug="ok", schema_data=schema)

    def test_data_sources_not_array(self):
        """dataSources 非数组。"""
        schema = {
            "componentName": "Page",
            "props": {},
            "dataSources": "invalid",
        }
        with pytest.raises(ValidationError, match="必须是数组"):
            LowCodePageCreate(name="ok", slug="ok", schema_data=schema)

    def test_valid_state(self):
        """合法 state 定义。"""
        schema = {
            "componentName": "Page",
            "props": {},
            "state": {
                "count": {"type": "number", "defaultValue": 0},
                "name": {"type": "string", "defaultValue": ""},
            },
        }
        page = LowCodePageCreate(name="ok", slug="ok", schema_data=schema)
        assert "count" in page.schema_data["state"]

    def test_state_missing_type(self):
        """state 变量缺少 type。"""
        schema = {
            "componentName": "Page",
            "props": {},
            "state": {"count": {"defaultValue": 0}},
        }
        with pytest.raises(ValidationError, match="缺少 type"):
            LowCodePageCreate(name="ok", slug="ok", schema_data=schema)

    def test_state_missing_default_value(self):
        """state 变量缺少 defaultValue。"""
        schema = {
            "componentName": "Page",
            "props": {},
            "state": {"count": {"type": "number"}},
        }
        with pytest.raises(ValidationError, match="缺少 defaultValue"):
            LowCodePageCreate(name="ok", slug="ok", schema_data=schema)

    def test_valid_data_binding(self):
        """合法 dataBinding。"""
        schema = {
            "componentName": "Page",
            "props": {},
            "dataBinding": {"title": "state.title", "list": "dataSources.ds1"},
        }
        page = LowCodePageCreate(name="ok", slug="ok", schema_data=schema)
        assert page.schema_data["dataBinding"]["title"] == "state.title"

    def test_data_binding_value_not_string(self):
        """dataBinding 值非字符串。"""
        schema = {
            "componentName": "Page",
            "props": {},
            "dataBinding": {"title": 123},
        }
        with pytest.raises(ValidationError, match="绑定表达式必须是字符串"):
            LowCodePageCreate(name="ok", slug="ok", schema_data=schema)

    def test_valid_events(self):
        """合法 events。"""
        schema = {
            "componentName": "Page",
            "props": {},
            "events": [
                {
                    "event": "onClick",
                    "actions": [{"type": "navigate", "url": "/detail"}],
                }
            ],
        }
        page = LowCodePageCreate(name="ok", slug="ok", schema_data=schema)
        assert len(page.schema_data["events"]) == 1

    def test_events_missing_event_field(self):
        """events 条目缺少 event 字段。"""
        schema = {
            "componentName": "Page",
            "props": {},
            "events": [{"actions": []}],
        }
        with pytest.raises(ValidationError, match="缺少 event"):
            LowCodePageCreate(name="ok", slug="ok", schema_data=schema)

    def test_events_missing_actions(self):
        """events 条目缺少 actions。"""
        schema = {
            "componentName": "Page",
            "props": {},
            "events": [{"event": "onClick"}],
        }
        with pytest.raises(ValidationError, match="缺少 actions"):
            LowCodePageCreate(name="ok", slug="ok", schema_data=schema)

    def test_events_actions_not_list(self):
        """events.actions 非数组。"""
        schema = {
            "componentName": "Page",
            "props": {},
            "events": [{"event": "onClick", "actions": "bad"}],
        }
        with pytest.raises(ValidationError, match="actions 必须是数组"):
            LowCodePageCreate(name="ok", slug="ok", schema_data=schema)

    def test_valid_loop(self):
        """合法 loop 配置。"""
        schema = {
            "componentName": "Page",
            "props": {},
            "loop": {"dataSource": "ds1"},
        }
        page = LowCodePageCreate(name="ok", slug="ok", schema_data=schema)
        assert page.schema_data["loop"]["dataSource"] == "ds1"

    def test_loop_missing_datasource(self):
        """loop 缺少 dataSource。"""
        schema = {
            "componentName": "Page",
            "props": {},
            "loop": {},
        }
        with pytest.raises(ValidationError, match="缺少 dataSource"):
            LowCodePageCreate(name="ok", slug="ok", schema_data=schema)

    def test_loop_datasource_not_string(self):
        """loop.dataSource 非字符串。"""
        schema = {
            "componentName": "Page",
            "props": {},
            "loop": {"dataSource": 123},
        }
        with pytest.raises(ValidationError, match="dataSource 必须是字符串"):
            LowCodePageCreate(name="ok", slug="ok", schema_data=schema)

    def test_update_schema_data_same_validation(self):
        """LowCodePageUpdate 的 schema_data 也执行相同校验。"""
        schema = {"props": {}}  # 缺少 componentName
        with pytest.raises(ValidationError, match="componentName"):
            LowCodePageUpdate(schema_data=schema)


class TestTemplateCreate:
    """测试模板创建相关 schema。

    当前 schemas.py 未定义独立 TemplateCreate schema，
    模板创建使用 LowCodePageCreate + 额外 metadata。
    以下测试 LowCodePageCreate 中模板场景的边界条件。
    """

    def test_template_with_full_schema(self):
        """含完整 schema_data 的模板创建。"""
        schema = {
            "componentName": "Page",
            "props": {"title": "模板"},
            "children": [
                {
                    "componentName": "View",
                    "props": {"className": "header"},
                    "children": [],
                }
            ],
            "dataSources": [
                {"id": "api1", "url": "https://api.example.com/data", "method": "GET"}
            ],
            "state": {"loading": {"type": "boolean", "defaultValue": False}},
        }
        page = LowCodePageCreate(name="挂号模板", slug="booking-template", schema_data=schema)
        assert page.name == "挂号模板"
        assert page.schema_data["componentName"] == "Page"
        assert len(page.schema_data["dataSources"]) == 1

    def test_template_description_max_length(self):
        """模板描述不超过 500 字符。"""
        page = LowCodePageCreate(
            name="模板", slug="tpl", description="d" * 500
        )
        assert len(page.description) == 500

    def test_template_empty_slug(self):
        """模板 slug 不能为空。"""
        with pytest.raises(ValidationError):
            LowCodePageCreate(name="模板", slug="")


class TestDeployRequest:
    """测试部署请求 schema。"""

    def test_rollback_request_valid(self):
        """合法的版本回滚请求。"""
        req = RollbackRequest(version_id="v-001")
        assert req.version_id == "v-001"

    def test_rollback_request_missing_version_id(self):
        """缺少 version_id。"""
        with pytest.raises(ValidationError):
            RollbackRequest()

    def test_deploy_rollback_request_empty(self):
        """部署回滚请求 — target_version 可选。"""
        req = DeployRollbackRequest()
        assert req.target_version is None

    def test_deploy_rollback_request_with_version(self):
        """部署回滚请求 — 指定目标版本。"""
        req = DeployRollbackRequest(target_version="v2")
        assert req.target_version == "v2"

    def test_wechat_audit_callback_valid(self):
        """合法的微信审核回调。"""
        cb = WeChatAuditCallbackRequest(auditid="audit-001", status=0)
        assert cb.auditid == "audit-001"
        assert cb.status == 0
        assert cb.reason is None

    def test_wechat_audit_callback_with_reason(self):
        """审核失败时带 reason。"""
        cb = WeChatAuditCallbackRequest(
            auditid="audit-002", status=1, reason="内容违规"
        )
        assert cb.reason == "内容违规"

    def test_wechat_audit_callback_missing_auditid(self):
        """缺少 auditid。"""
        with pytest.raises(ValidationError):
            WeChatAuditCallbackRequest(status=0)


class TestVersionListParams:
    """测试版本列表相关 schema。"""

    def test_version_item(self):
        """合法的版本项。"""
        item = VersionItem(id="v-1", version=3, snapshot_label="v3.0")
        assert item.id == "v-1"
        assert item.version == 3
        assert item.snapshot_label == "v3.0"

    def test_version_item_minimal(self):
        """仅必填字段。"""
        item = VersionItem(id="v-1", version=1)
        assert item.created_at is None
        assert item.created_by is None

    def test_version_list_response_defaults(self):
        """版本列表响应默认值。"""
        resp = VersionListResponse()
        assert resp.current_version == 0
        assert resp.versions == []

    def test_version_list_response_full(self):
        """完整版本列表响应。"""
        resp = VersionListResponse(
            current_version=5,
            versions=[
                VersionItem(id="v-5", version=5),
                VersionItem(id="v-4", version=4),
            ],
        )
        assert resp.current_version == 5
        assert len(resp.versions) == 2
        assert resp.versions[0].version == 5

    def test_version_item_requires_id(self):
        """缺少 id。"""
        with pytest.raises(ValidationError):
            VersionItem(version=1)

    def test_version_item_requires_version(self):
        """缺少 version。"""
        with pytest.raises(ValidationError):
            VersionItem(id="v-1")


class TestPageListParamsFilter:
    """测试列表过滤参数相关 schema。

    当前 schemas.py 未定义 PageListParams schema。
    以下测试 DataSourceTestRequest / DataPreviewResponse 等
    辅助 schema，覆盖列表查询场景中涉及的参数。
    """

    def test_data_source_test_request_minimal(self):
        """数据源测试 — 最小参数。"""
        req = DataSourceTestRequest(url="https://api.example.com")
        assert req.url == "https://api.example.com"
        assert req.method == "GET"
        assert req.headers is None
        assert req.params is None
        assert req.body is None
        assert req.response_path is None

    def test_data_source_test_request_post(self):
        """数据源测试 — POST 请求。"""
        req = DataSourceTestRequest(
            url="https://api.example.com/create",
            method="POST",
            headers={"Content-Type": "application/json"},
            params={"page": 1},
            body={"name": "test"},
            response_path="data.list",
        )
        assert req.method == "POST"
        assert req.body == {"name": "test"}
        assert req.response_path == "data.list"

    def test_data_source_test_request_invalid_method(self):
        """数据源测试 — 无 method 校验（schema 不限制 method 值）。"""
        # DataSourceTestRequest 的 method 字段是自由字符串
        req = DataSourceTestRequest(url="https://example.com", method="PATCH")
        assert req.method == "PATCH"

    def test_data_preview_response(self):
        """数据预览响应。"""
        resp = DataPreviewResponse(
            page_id="p-1",
            page_name="首页",
            data_sources=[],
        )
        assert resp.page_id == "p-1"
        assert resp.data_sources == []

    def test_codegen_preview_request_minimal(self):
        """代码生成预览 — 最小参数。"""
        req = CodegenPreviewRequest(schema_data={"componentName": "Page", "props": {}})
        assert req.target == "taro"
        assert req.data_sources == []

    def test_codegen_preview_request_full(self):
        """代码生成预览 — 完整参数。"""
        req = CodegenPreviewRequest(
            schema_data={"componentName": "Page", "props": {}},
            data_sources=[{"id": "ds1", "url": "https://api.test.com", "method": "GET"}],
            target="native",
        )
        assert req.target == "native"
        assert len(req.data_sources) == 1

    def test_codegen_result_schema_defaults(self):
        """代码生成结果 — 默认值。"""
        result = CodegenResultSchema()
        assert result.files == []
        assert result.warnings == []
        assert result.dependencies == []
        assert result.metadata == {}

    def test_codegen_result_with_files(self):
        """代码生成结果 — 含文件。"""
        result = CodegenResultSchema(
            files=[
                GeneratedFileSchema(
                    path="pages/home/index.tsx",
                    content="export default () => <View />",
                    type="tsx",
                )
            ],
            dependencies=["@tarojs/components"],
        )
        assert len(result.files) == 1
        assert result.files[0].path == "pages/home/index.tsx"
        assert result.files[0].type == "tsx"
        assert result.dependencies == ["@tarojs/components"]

    def test_deploy_result_response(self):
        """部署结果响应。"""
        resp = DeployResultResponse(
            build_job_id="job-001",
            deploy_status="building",
        )
        assert resp.build_job_id == "job-001"
        assert resp.deploy_status == "building"
        assert resp.audit_id is None
        assert resp.artifact_url is None

    def test_data_source_test_response(self):
        """数据源测试响应。"""
        resp = DataSourceTestResponse(
            success=True,
            status_code=200,
            sample_data=[{"id": 1}],
            fields=[],
            elapsed_ms=150,
        )
        assert resp.success is True
        assert resp.elapsed_ms == 150
        assert resp.error is None
