"""
导入服务租户隔离测试

测试用例覆盖：
1. 导入服务必须验证租户上下文
2. 导入数据不能包含 tenant_id 字段（防止注入）
3. 行级别的租户验证
4. 跨租户关联数据验证
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.import_export.service_import import ImportService, SENSITIVE_FIELDS
from app.middleware.exception import BusinessError
from app.models.store import Store


class TestImportServiceTenantIsolation:
    """导入服务租户隔离测试"""

    def test_sanitize_row_data_removes_tenant_id(self):
        """测试 _sanitize_row_data 移除 tenant_id 等敏感字段"""
        row_data = {
            "name": "测试",
            "phone": "13800138000",
            "tenant_id": "malicious-tenant-id",  # 应该被移除
            "id": "malicious-id",  # 应该被移除
            "created_at": "2024-01-01",  # 应该被移除
            "updated_at": "2024-01-01",  # 应该被移除
            "created_by": "admin",  # 应该被移除
            "updated_by": "admin",  # 应该被移除
            "_internal": "value",  # 应该被移除（下划线开头）
            "valid_field": "value",  # 应该保留
        }

        cleaned = ImportService._sanitize_row_data(row_data)

        # 验证敏感字段被移除
        assert "tenant_id" not in cleaned
        assert "id" not in cleaned
        assert "created_at" not in cleaned
        assert "updated_at" not in cleaned
        assert "created_by" not in cleaned
        assert "updated_by" not in cleaned
        assert "_internal" not in cleaned

        # 验证有效字段保留
        assert cleaned["name"] == "测试"
        assert cleaned["phone"] == "13800138000"
        assert cleaned["valid_field"] == "value"

    def test_sensitive_fields_constant(self):
        """测试 SENSITIVE_FIELDS 常量包含所有必要的敏感字段"""
        expected_fields = {
            "tenant_id", "id", "created_at", "updated_at",
            "created_by", "updated_by"
        }
        assert SENSITIVE_FIELDS == expected_fields

    def test_infer_tenant_id_from_context(self):
        """测试从上下文推断租户 ID"""
        db_mock = MagicMock(spec=AsyncSession)
        service = ImportService(db_mock)

        # 模拟租户上下文
        with patch(
            "app.modules.import_export.service_import.get_tenant_id_for_create",
            return_value="tenant-123"
        ):
            tenant_id = service._infer_tenant_id()
            assert tenant_id == "tenant-123"
            # 验证缓存
            assert service._tenant_id == "tenant-123"

    def test_infer_tenant_id_explicit(self):
        """测试显式指定租户 ID"""
        db_mock = MagicMock(spec=AsyncSession)
        service = ImportService(db_mock)

        with patch(
            "app.modules.import_export.service_import.get_tenant_id_for_create",
            return_value="explicit-tenant"
        ):
            tenant_id = service._infer_tenant_id(tenant_id="explicit-tenant")
            assert tenant_id == "explicit-tenant"

    def test_infer_tenant_id_raises_on_missing(self):
        """测试缺少租户上下文时抛出异常"""
        db_mock = MagicMock(spec=AsyncSession)
        service = ImportService(db_mock)

        with patch(
            "app.modules.import_export.service_import.get_tenant_id_for_create",
            return_value=None
        ):
            with patch(
                "app.modules.import_export.service_import.get_current_tenant_id",
                return_value=None
            ):
                with pytest.raises(ValueError) as exc_info:
                    service._infer_tenant_id()

                assert "必须指定租户" in str(exc_info.value)

    def test_infer_tenant_id_uses_cache(self):
        """测试使用缓存的租户 ID"""
        db_mock = MagicMock(spec=AsyncSession)
        service = ImportService(db_mock)
        service._tenant_id = "cached-tenant"

        # 不应该调用 get_tenant_id_for_create
        tenant_id = service._infer_tenant_id()
        assert tenant_id == "cached-tenant"

    @pytest.mark.asyncio
    async def test_validate_row_tenant_without_model(self):
        """测试没有模型类时的租户验证"""
        db_mock = MagicMock(spec=AsyncSession)
        service = ImportService(db_mock)
        service._tenant_id = "tenant-123"

        row_data = {"name": "测试"}
        result = await service._validate_row_tenant(row_data, 1)

        assert result == "tenant-123"

    @pytest.mark.asyncio
    async def test_validate_row_tenant_with_matching_tenant(self):
        """测试关联数据属于当前租户"""
        db_mock = MagicMock(spec=AsyncSession)

        # 模拟查询结果
        mock_result = MagicMock()
        mock_related_obj = MagicMock()
        mock_related_obj.tenant_id = "tenant-123"
        mock_result.scalar_one_or_none.return_value = mock_related_obj
        db_mock.execute.return_value = mock_result

        service = ImportService(db_mock)
        service._tenant_id = "tenant-123"

        row_data = {"store_id": "store-456"}
        result = await service._validate_row_tenant(
            row_data, 1,
            model_class=Store,
            id_field="store_id"
        )

        assert result == "tenant-123"

    @pytest.mark.asyncio
    async def test_validate_row_tenant_with_mismatched_tenant(self):
        """测试关联数据不属于当前租户（应跳过）"""
        db_mock = MagicMock(spec=AsyncSession)

        # 模拟查询结果
        mock_result = MagicMock()
        mock_related_obj = MagicMock()
        mock_related_obj.tenant_id = "other-tenant"  # 不同的租户
        mock_result.scalar_one_or_none.return_value = mock_related_obj
        db_mock.execute.return_value = mock_result

        service = ImportService(db_mock)
        service._tenant_id = "tenant-123"

        row_data = {"store_id": "store-456"}
        result = await service._validate_row_tenant(
            row_data, 1,
            model_class=Store,
            id_field="store_id"
        )

        # 应该返回 None（跳过该行）
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_row_tenant_with_nonexistent_related(self):
        """测试关联数据不存在（应跳过）"""
        db_mock = MagicMock(spec=AsyncSession)

        # 模拟查询结果 - 不存在
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db_mock.execute.return_value = mock_result

        service = ImportService(db_mock)
        service._tenant_id = "tenant-123"

        row_data = {"store_id": "nonexistent-store"}
        result = await service._validate_row_tenant(
            row_data, 1,
            model_class=Store,
            id_field="store_id"
        )

        # 应该返回 None（跳过该行）
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_and_import_rejects_sensitive_fields(self):
        """测试导入包含敏感字段的数据被拒绝"""
        db_mock = MagicMock(spec=AsyncSession)

        service = ImportService(db_mock)

        # 模拟 Excel 解析返回包含 tenant_id 的数据
        with patch(
            "app.modules.import_export.service_import.ExcelImportService.parse_excel",
            return_value=(
                [{"name": "测试", "tenant_id": "malicious-tenant"}],  # 包含敏感字段
                []
            )
        ):
            with patch(
                "app.modules.import_export.service_import.get_current_tenant_id",
                return_value="tenant-123"
            ):
                with pytest.raises(BusinessError) as exc_info:
                    await service.validate_and_import(
                        file_content=b"fake-excel",
                        filename="test.xlsx",
                        expected_headers=["姓名"],
                        required_fields=["姓名"],
                        process_row_func=AsyncMock(),
                    )

                assert "不允许的字段" in str(exc_info.value.message)
                assert "tenant_id" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_validate_and_import_requires_tenant_context(self):
        """测试导入必须有租户上下文"""
        db_mock = MagicMock(spec=AsyncSession)
        service = ImportService(db_mock)

        with patch(
            "app.modules.import_export.service_import.get_tenant_id_for_create",
            return_value=None
        ):
            with patch(
                "app.modules.import_export.service_import.get_current_tenant_id",
                return_value=None
            ):
                with pytest.raises(BusinessError) as exc_info:
                    await service.validate_and_import(
                        file_content=b"fake-excel",
                        filename="test.xlsx",
                        expected_headers=["姓名"],
                        required_fields=["姓名"],
                        process_row_func=AsyncMock(),
                    )

                assert "必须指定租户" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_validate_and_import_skips_tenant_validation(self):
        """测试可以跳过租户验证（用于平台管理员）"""
        db_mock = MagicMock(spec=AsyncSession)
        db_mock.commit = AsyncMock()

        service = ImportService(db_mock)

        async def process_row(row_data):
            pass

        with patch(
            "app.modules.import_export.service_import.ExcelImportService.parse_excel",
            return_value=(
                [{"name": "测试"}],
                []
            )
        ):
            result = await service.validate_and_import(
                file_content=b"fake-excel",
                filename="test.xlsx",
                expected_headers=["姓名"],
                required_fields=["姓名"],
                process_row_func=process_row,
                validate_tenant=False,  # 跳过租户验证
            )

            assert result["success_count"] == 1
            assert result["fail_count"] == 0

    @pytest.mark.asyncio
    async def test_validate_and_import_returns_skipped_count(self):
        """测试导入结果包含跳过计数"""
        db_mock = MagicMock(spec=AsyncSession)
        db_mock.commit = AsyncMock()

        service = ImportService(db_mock)
        service._tenant_id = "tenant-123"

        async def process_row(row_data):
            if row_data.get("name") == "跳过":
                raise ValueError("租户数据不存在，跳过")
            # 正常处理

        with patch(
            "app.modules.import_export.service_import.ExcelImportService.parse_excel",
            return_value=(
                [
                    {"name": "正常"},
                    {"name": "跳过"},
                    {"name": "正常2"},
                ],
                []
            )
        ):
            result = await service.validate_and_import(
                file_content=b"fake-excel",
                filename="test.xlsx",
                expected_headers=["姓名"],
                required_fields=["姓名"],
                process_row_func=process_row,
            )

            assert result["success_count"] == 2
            assert result["skipped_count"] == 1
            assert result["total"] == 3

    def test_tenant_id_property(self):
        """测试 tenant_id 属性"""
        db_mock = MagicMock(spec=AsyncSession)
        service = ImportService(db_mock)

        assert service.tenant_id is None

        service._tenant_id = "tenant-123"
        assert service.tenant_id == "tenant-123"


class TestRuleSetImportTenantIsolation:
    """规则组导入服务租户隔离测试"""

    @pytest.mark.asyncio
    async def test_import_rule_sets_requires_tenant_id(self):
        """测试导入规则组必须有租户上下文"""
        from app.modules.import_export.service_rule_set_import import RuleSetImportService

        db_mock = MagicMock(spec=AsyncSession)
        service = RuleSetImportService(db_mock)

        with patch(
            "app.middleware.tenant_context.get_current_tenant_id",
            return_value=None
        ):
            with pytest.raises(ValueError) as exc_info:
                await service.import_rule_sets(b"fake-content")

            assert "租户上下文" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_import_rule_sets_uses_explicit_tenant_id(self):
        """测试显式传入 tenant_id 优先于上下文"""
        from app.modules.import_export.service_rule_set_import import RuleSetImportService

        db_mock = MagicMock(spec=AsyncSession)
        db_mock.commit = AsyncMock()
        service = RuleSetImportService(db_mock)

        # 模拟 Excel 解析返回空数据（不需要真正解析）
        with patch("app.modules.import_export.service_rule_set_import.load_workbook"):
            with patch.object(service, '_parse_sheet', return_value=[]):
                with patch.object(service, '_validate_rule_sets', return_value=[]):
                    with patch.object(service, '_validate_references', return_value=[]):
                        result = await service.import_rule_sets(
                            b"fake-content", tenant_id="explicit-tenant"
                        )

                        assert result["success_count"] == 0

    @pytest.mark.asyncio
    async def test_import_rule_set_filters_by_tenant_on_duplicate_check(self):
        """测试导入时重名检查添加了租户过滤（防跨租户名称冲突）"""
        from app.modules.import_export.service_rule_set_import import RuleSetImportService
        from app.models.rule_set import RuleSet

        db_mock = MagicMock(spec=AsyncSession)
        service = RuleSetImportService(db_mock)

        # 模拟：同名规则组在另一租户存在，当前租户不存在
        mock_result = MagicMock()
        mock_result.scalar.return_value = None  # 当前租户不存在同名
        db_mock.execute = AsyncMock(return_value=mock_result)
        db_mock.add = MagicMock()
        db_mock.flush = AsyncMock()

        rs_data = {
            "_row": 2,
            "规则组名称": "测试规则组",
            "优先级": 100,
            "是否启用": "是",
        }

        # 调用 _import_rule_set
        await service._import_rule_set(
            rs_data, [], [], [], [], tenant_id="tenant-A"
        )

        # 验证查询中包含 tenant_id 过滤
        call_args = db_mock.execute.call_args_list[0]
        from sqlalchemy import select
        query = call_args[0][0]
        # 验证查询条件包含 tenant_id
        query_str = str(query)
        assert "tenant_id" in query_str

    @pytest.mark.asyncio
    async def test_import_rule_set_sets_tenant_id_on_create(self):
        """测试创建规则组时设置了 tenant_id"""
        from app.modules.import_export.service_rule_set_import import RuleSetImportService

        db_mock = MagicMock(spec=AsyncSession)
        service = RuleSetImportService(db_mock)

        # 模拟查询结果：不存在同名规则组
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        db_mock.execute = AsyncMock(return_value=mock_result)
        db_mock.add = MagicMock()
        db_mock.flush = AsyncMock()

        rs_data = {
            "_row": 2,
            "规则组名称": "测试规则组",
            "优先级": 100,
            "是否启用": "是",
        }

        await service._import_rule_set(
            rs_data, [], [], [], [], tenant_id="tenant-ABC"
        )

        # 验证 db.add 被调用，且传入的对象有正确的 tenant_id
        assert db_mock.add.called
        added_obj = db_mock.add.call_args[0][0]
        assert added_obj.tenant_id == "tenant-ABC"


class TestExportServiceTenantIsolation:
    """旧导出服务租户隔离测试"""

    @pytest.mark.asyncio
    async def test_export_appointments_filters_by_tenant(self):
        """测试导出预约记录时添加了租户过滤"""
        from app.modules.export.service import ExportService

        db_mock = MagicMock(spec=AsyncSession)

        # 模拟查询结果
        mock_result = MagicMock()
        mock_result.unique = MagicMock(return_value=mock_result)
        mock_result.scalars.return_value.all.return_value = []
        db_mock.execute = AsyncMock(return_value=mock_result)

        service = ExportService(db_mock)
        await service.export_appointments(tenant_id="tenant-A")

        # 验证 db.execute 被调用
        assert db_mock.execute.called
        # 验证查询包含 tenant_id 条件
        call_args = db_mock.execute.call_args_list[0]
        query = call_args[0][0]
        query_str = str(query)
        assert "tenant_id" in query_str

    @pytest.mark.asyncio
    async def test_export_patients_filters_by_tenant(self):
        """测试导出患者列表时添加了租户过滤"""
        from app.modules.export.service import ExportService

        db_mock = MagicMock(spec=AsyncSession)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db_mock.execute = AsyncMock(return_value=mock_result)

        service = ExportService(db_mock)
        await service.export_patients(tenant_id="tenant-A")

        assert db_mock.execute.called
        call_args = db_mock.execute.call_args_list[0]
        query = call_args[0][0]
        query_str = str(query)
        assert "tenant_id" in query_str

    @pytest.mark.asyncio
    async def test_export_schedules_filters_by_tenant(self):
        """测试导出排班记录时添加了租户过滤"""
        from app.modules.export.service import ExportService

        db_mock = MagicMock(spec=AsyncSession)

        mock_result = MagicMock()
        mock_result.unique = MagicMock(return_value=mock_result)
        mock_result.scalars.return_value.all.return_value = []
        db_mock.execute = AsyncMock(return_value=mock_result)

        service = ExportService(db_mock)
        await service.export_schedules(tenant_id="tenant-A")

        assert db_mock.execute.called
        call_args = db_mock.execute.call_args_list[0]
        query = call_args[0][0]
        query_str = str(query)
        assert "tenant_id" in query_str

    @pytest.mark.asyncio
    async def test_export_appointments_without_tenant_id(self):
        """测试不传 tenant_id 时导出预约记录不添加租户过滤（WHERE 子句）"""
        from app.modules.export.service import ExportService

        db_mock = MagicMock(spec=AsyncSession)

        mock_result = MagicMock()
        mock_result.unique = MagicMock(return_value=mock_result)
        mock_result.scalars.return_value.all.return_value = []
        db_mock.execute = AsyncMock(return_value=mock_result)

        service = ExportService(db_mock)
        await service.export_appointments()

        call_args = db_mock.execute.call_args_list[0]
        query = call_args[0][0]
        query_str = str(query)
        # 没有 tenant_id 过滤时，查询字符串中不应出现 WHERE 子句
        assert "WHERE" not in query_str
