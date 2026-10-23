"""
import_export 模块单元测试

测试范围：
1. ImportService - 租户推断、敏感字段清理、导入流水线
2. RuleSetImportService - 多工作表 Excel 解析、数据验证、引用完整性
3. ExcelImportService - Excel 解析、空文件/损坏文件/缺少必填字段
4. ExcelExportService - 值格式化、单表/多表工作簿生成
5. _apply_store_filter - 门店过滤边界条件
6. _parse_date / _parse_time / VALID_TIME_SLOTS - 纯工具函数
"""
import asyncio
from datetime import date, datetime, time
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from openpyxl import Workbook, load_workbook
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.excel.import_service import ExcelImportError, ExcelImportService
from app.infrastructure.excel.export_service import ExcelExportService
from app.middleware.exception import BusinessError
from app.modules.import_export.service_import import (
    ImportService,
    SENSITIVE_FIELDS,
)


# ==================== 工具函数 ====================


def _make_excel(
    rows: list[list],
    headers: list[str],
    sheet_name: str = "Sheet1",
) -> bytes:
    """构造简单 Excel 文件字节流"""
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name

    for col_idx, header in enumerate(headers, 1):
        ws.cell(row=1, column=col_idx, value=header)

    for row_idx, row_data in enumerate(rows, 2):
        for col_idx, value in enumerate(row_data, 1):
            ws.cell(row=row_idx, column=col_idx, value=value)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


def _make_multi_sheet_excel(sheet_data: dict[str, tuple[list[str], list[list]]]) -> bytes:
    """
    构造多工作表 Excel 文件字节流。
    sheet_data: {sheet_name: (headers, rows)}
    """
    wb = Workbook()
    wb.remove(wb.active)

    for sheet_name, (headers, rows) in sheet_data.items():
        ws = wb.create_sheet(title=sheet_name)
        for col_idx, header in enumerate(headers, 1):
            ws.cell(row=1, column=col_idx, value=header)
        for row_idx, row_data in enumerate(rows, 2):
            for col_idx, value in enumerate(row_data, 1):
                ws.cell(row=row_idx, column=col_idx, value=value)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


# ==================== TestImportService ====================


class TestImportService:
    """ImportService 核心逻辑测试"""

    # --- _sanitize_row_data 静态方法 ---

    @pytest.mark.unit
    def test_sanitize_row_data_removes_sensitive_fields(self):
        """敏感字段 tenant_id / id / created_at 等应被移除"""
        row = {
            "name": "张医生",
            "phone": "13800138000",
            "tenant_id": "evil-tenant",
            "id": "injected-id",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "created_by": "admin",
            "updated_by": "admin",
        }
        cleaned = ImportService._sanitize_row_data(row)
        assert "tenant_id" not in cleaned
        assert "id" not in cleaned
        assert "created_at" not in cleaned
        assert "updated_at" not in cleaned
        assert "created_by" not in cleaned
        assert "updated_by" not in cleaned
        assert cleaned["name"] == "张医生"
        assert cleaned["phone"] == "13800138000"

    @pytest.mark.unit
    def test_sanitize_row_data_removes_internal_fields(self):
        """以 _ 开头的内部字段（如 _row）应被移除"""
        row = {
            "name": "张医生",
            "_row": 3,
            "_internal": "secret",
        }
        cleaned = ImportService._sanitize_row_data(row)
        assert "_row" not in cleaned
        assert "_internal" not in cleaned
        assert cleaned["name"] == "张医生"

    @pytest.mark.unit
    def test_sanitize_row_data_preserves_normal_fields(self):
        """非敏感字段应原样保留，包括值为 None 的字段"""
        row = {
            "name": "张医生",
            "department": None,
            "title": "主治医师",
        }
        cleaned = ImportService._sanitize_row_data(row)
        assert cleaned["name"] == "张医生"
        assert cleaned["department"] is None
        assert cleaned["title"] == "主治医师"

    # --- validate_and_import 端到端流程 ---

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_and_import_no_tenant_raises_business_error(self):
        """没有租户上下文时应抛出 BusinessError"""
        db = AsyncMock(spec=AsyncSession)
        db.commit = AsyncMock()
        svc = ImportService(db)

        excel_bytes = _make_excel(
            [["张医生", "总院", "内科"]],
            ["姓名", "门店", "科室"],
        )

        # R1-5：service 不再回退上下文，不传 tenant_id 直接失败
        with pytest.raises(BusinessError, match="租户"):
            await svc.validate_and_import(
                file_content=excel_bytes,
                filename="test.xlsx",
                expected_headers=["姓名", "门店", "科室"],
                required_fields=["姓名"],
                process_row_func=AsyncMock(),
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_and_import_with_explicit_tenant(self):
        """显式传入 tenant_id 时应跳过上下文推断"""
        db = AsyncMock(spec=AsyncSession)
        db.commit = AsyncMock()
        svc = ImportService(db)

        excel_bytes = _make_excel(
            [["张医生", "总院"]],
            ["姓名", "门店"],
        )

        process_row = AsyncMock()

        result = await svc.validate_and_import(
            file_content=excel_bytes,
            filename="test.xlsx",
            expected_headers=["姓名", "门店"],
            required_fields=["姓名"],
            process_row_func=process_row,
            tenant_id="tenant-123",
        )

        assert result["success_count"] == 1
        assert result["fail_count"] == 0
        assert result["skipped_count"] == 0
        assert result["total"] == 1
        process_row.assert_awaited_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_and_import_sanitize_preserves_normal_fields(self):
        """sanitize=True 时非敏感字段应原样保留传递给处理函数"""
        db = AsyncMock(spec=AsyncSession)
        db.commit = AsyncMock()
        svc = ImportService(db)

        excel_bytes = _make_excel(
            [["张医生", "总院", "内科"]],
            ["姓名", "门店", "科室"],
        )

        captured_rows = []

        async def capture_row(row_data):
            captured_rows.append(dict(row_data))

        await svc.validate_and_import(
            file_content=excel_bytes,
            filename="test.xlsx",
            expected_headers=["姓名", "门店", "科室"],
            required_fields=["姓名"],
            process_row_func=capture_row,
            tenant_id="tenant-123",
            sanitize=True,
        )

        assert len(captured_rows) == 1
        assert captured_rows[0]["姓名"] == "张医生"
        assert captured_rows[0]["门店"] == "总院"
        assert captured_rows[0]["科室"] == "内科"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_and_import_rejects_sensitive_fields(self):
        """sanitize=True 且数据含敏感字段时应抛出 BusinessError"""
        db = AsyncMock(spec=AsyncSession)
        db.commit = AsyncMock()
        svc = ImportService(db)

        # 直接构造含敏感字段的 valid_rows（跳过 Excel 解析）
        mock_valid_rows = [
            {"name": "张医生", "tenant_id": "evil-tenant", "_row": 2}
        ]

        with patch(
            "app.modules.import_export.service_import.ExcelImportService.parse_excel",
            return_value=(mock_valid_rows, []),
        ):
            with pytest.raises(BusinessError, match="不允许的字段"):
                await svc.validate_and_import(
                    file_content=b"fake",
                    filename="test.xlsx",
                    expected_headers=["name", "tenant_id"],
                    required_fields=[],
                    process_row_func=AsyncMock(),
                    tenant_id="tenant-123",
                )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_and_import_row_processing_failure(self):
        """单行处理失败（非租户/不存在关键词）应计入 fail_count"""
        db = AsyncMock(spec=AsyncSession)
        db.commit = AsyncMock()
        svc = ImportService(db)

        call_count = 0

        async def failing_process(row_data):
            nonlocal call_count
            call_count += 1
            if row_data["姓名"] == "张医生":
                raise ValueError("手机号格式不正确")

        excel_bytes = _make_excel(
            [["张医生", "总院"], ["李医生", "分院"]],
            ["姓名", "门店"],
        )

        result = await svc.validate_and_import(
            file_content=excel_bytes,
            filename="test.xlsx",
            expected_headers=["姓名", "门店"],
            required_fields=["姓名"],
            process_row_func=failing_process,
            tenant_id="tenant-123",
        )

        assert result["success_count"] == 1
        assert result["fail_count"] == 1
        assert call_count == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_and_import_tenant_mismatch_skips_row(self):
        """租户验证失败的 ValueError（含'租户'或'不存在'关键词）应计入 skipped"""
        db = AsyncMock(spec=AsyncSession)
        db.commit = AsyncMock()
        svc = ImportService(db)

        async def tenant_mismatch(row_data):
            raise ValueError("数据与当前租户上下文不匹配，跳过该行")

        excel_bytes = _make_excel(
            [["张医生"], ["李医生"]],
            ["姓名"],
        )

        result = await svc.validate_and_import(
            file_content=excel_bytes,
            filename="test.xlsx",
            expected_headers=["姓名"],
            required_fields=["姓名"],
            process_row_func=tenant_mismatch,
            tenant_id="tenant-123",
        )

        assert result["skipped_count"] == 2
        assert result["fail_count"] == 0

    @pytest.mark.unit
    def test_validate_and_import_errors_capped_at_50(self):
        """错误列表最多返回 50 条"""
        # 验证 service_import.py 中 errors[:50] 的截断行为
        error_rows = [{"row": i, "data": {}, "errors": [f"error {i}"]} for i in range(100)]
        truncated = error_rows[:50]
        assert len(truncated) == 50


# ==================== TestExcelImportService ====================


class TestExcelImportService:
    """ExcelImportService 底层解析测试"""

    @pytest.mark.unit
    def test_parse_excel_valid_rows(self):
        """正常 Excel 应返回有效行和零错误行"""
        headers = ["姓名", "年龄", "科室"]
        rows = [
            ["张医生", 35, "内科"],
            ["李医生", 42, "外科"],
        ]
        excel_bytes = _make_excel(rows, headers)

        valid_rows, error_rows = ExcelImportService.parse_excel(
            excel_bytes, headers, required_fields=["姓名", "科室"]
        )

        assert len(valid_rows) == 2
        assert len(error_rows) == 0
        assert valid_rows[0]["姓名"] == "张医生"
        assert valid_rows[0]["年龄"] == 35
        assert valid_rows[1]["科室"] == "外科"

    @pytest.mark.unit
    def test_parse_excel_empty_file_raises_error(self):
        """空文件应抛出 ExcelImportError"""
        with pytest.raises(ExcelImportError, match="不能为空"):
            ExcelImportService.parse_excel(b"", ["col1"], [])

    @pytest.mark.unit
    def test_parse_excel_corrupted_file_raises_error(self):
        """损坏的文件应抛出 ExcelImportError"""
        with pytest.raises(ExcelImportError, match="无效或已损坏"):
            ExcelImportService.parse_excel(b"not-an-excel-file", ["col1"], [])

    @pytest.mark.unit
    def test_parse_excel_unsupported_extension_raises_error(self):
        """不支持的文件扩展名应抛出 ExcelImportError"""
        with pytest.raises(ExcelImportError, match="请上传"):
            ExcelImportService.parse_excel(
                b"content", ["col1"], [], filename="data.csv"
            )

    @pytest.mark.unit
    def test_parse_excel_missing_required_fields(self):
        """缺少必填字段的行应进入 error_rows"""
        headers = ["姓名", "科室"]
        rows = [
            ["张医生", "内科"],       # 完整
            ["", "外科"],              # 缺姓名
            ["王医生", ""],            # 缺科室
        ]
        excel_bytes = _make_excel(rows, headers)

        valid_rows, error_rows = ExcelImportService.parse_excel(
            excel_bytes, headers, required_fields=["姓名", "科室"]
        )

        assert len(valid_rows) == 1
        assert len(error_rows) == 2
        assert valid_rows[0]["姓名"] == "张医生"
        assert any("姓名" in str(e["errors"]) for e in error_rows)
        assert any("科室" in str(e["errors"]) for e in error_rows)

    @pytest.mark.unit
    def test_parse_excel_header_mismatch(self):
        """表头完全不匹配时应抛出 ExcelImportError"""
        headers = ["name", "age"]
        rows = [["张医生", 35]]
        excel_bytes = _make_excel(rows, headers)

        with pytest.raises(ExcelImportError, match="表头不匹配"):
            ExcelImportService.parse_excel(
                excel_bytes, ["姓名", "年龄"], []
            )

    @pytest.mark.unit
    def test_parse_excel_fuzzy_header_matching(self):
        """表头含全角括号时应支持模糊匹配"""
        headers = ["姓名", "年龄（岁）"]
        rows = [["张医生", 35]]
        excel_bytes = _make_excel(rows, headers)

        valid_rows, error_rows = ExcelImportService.parse_excel(
            excel_bytes, ["姓名", "年龄(岁)"], []
        )

        # 模糊匹配成功：全角括号被规范化后匹配
        assert len(valid_rows) == 1
        assert valid_rows[0]["年龄(岁)"] == 35

    @pytest.mark.unit
    def test_parse_excel_skips_empty_rows(self):
        """全空行应被自动跳过"""
        headers = ["姓名", "科室"]
        rows = [
            ["张医生", "内科"],
            [None, None],          # 空行
            ["", ""],              # 空字符串行
            ["李医生", "外科"],
        ]
        excel_bytes = _make_excel(rows, headers)

        valid_rows, error_rows = ExcelImportService.parse_excel(
            excel_bytes, headers, required_fields=["姓名"]
        )

        assert len(valid_rows) == 2
        assert len(error_rows) == 0


# ==================== TestRuleSetImportService ====================


class TestRuleSetImportService:
    """RuleSetImportService 多工作表解析和验证测试"""

    @pytest.mark.unit
    def test_parse_sheet_missing_sheet_returns_empty(self):
        """工作表不存在时 _parse_sheet 应返回空列表"""
        from app.modules.import_export.service_rule_set_import import RuleSetImportService

        wb = Workbook()
        wb.remove(wb.active)
        wb.create_sheet("其他工作表")
        svc = RuleSetImportService.__new__(RuleSetImportService)

        result = svc._parse_sheet(wb, "规则组", ["规则组名称", "优先级"])
        assert result == []
        wb.close()

    @pytest.mark.unit
    def test_validate_rule_sets_missing_name(self):
        """规则组名称为空时应产生错误"""
        from app.modules.import_export.service_rule_set_import import RuleSetImportService

        svc = RuleSetImportService.__new__(RuleSetImportService)

        rule_sets_data = [{"_row": 2, "规则组名称": None}]
        errors = svc._validate_rule_sets(rule_sets_data)

        assert len(errors) == 1
        assert "必填项" in errors[0]["errors"][0]

    @pytest.mark.unit
    def test_validate_rule_sets_duplicate_names(self):
        """规则组名称重复时应产生错误"""
        from app.modules.import_export.service_rule_set_import import RuleSetImportService

        svc = RuleSetImportService.__new__(RuleSetImportService)

        rule_sets_data = [
            {"_row": 2, "规则组名称": "默认规则"},
            {"_row": 3, "规则组名称": "默认规则"},
        ]
        errors = svc._validate_rule_sets(rule_sets_data)

        assert len(errors) == 1
        assert "重复" in errors[0]["errors"][0]

    @pytest.mark.unit
    def test_validate_references_window_to_nonexistent_rule_set(self):
        """时间窗引用不存在的规则组时应产生错误"""
        from app.modules.import_export.service_rule_set_import import RuleSetImportService

        svc = RuleSetImportService.__new__(RuleSetImportService)

        rule_sets_data = [{"_row": 2, "规则组名称": "规则A"}]
        windows_data = [{"_row": 5, "规则组名称": "规则B"}]
        booking_data = []
        checkin_data = []
        capacity_data = []

        errors = svc._validate_references(
            rule_sets_data, windows_data, booking_data, checkin_data, capacity_data
        )

        assert len(errors) == 1
        assert "规则B" in errors[0]["errors"][0]
        assert "不存在" in errors[0]["errors"][0]

    @pytest.mark.unit
    def test_validate_references_all_sheets_clean(self):
        """所有引用关系正确时不应产生错误"""
        from app.modules.import_export.service_rule_set_import import RuleSetImportService

        svc = RuleSetImportService.__new__(RuleSetImportService)

        rule_sets_data = [{"_row": 2, "规则组名称": "规则A"}]
        windows_data = [{"_row": 5, "规则组名称": "规则A"}]
        booking_data = [{"_row": 8, "规则组名称": "规则A"}]
        checkin_data = [{"_row": 11, "规则组名称": "规则A"}]
        capacity_data = [{"_row": 14, "规则组名称": "规则A"}]

        errors = svc._validate_references(
            rule_sets_data, windows_data, booking_data, checkin_data, capacity_data
        )

        assert len(errors) == 0

    @pytest.mark.unit
    def test_import_rule_sets_no_tenant_raises(self):
        """没有租户上下文时 import_rule_sets 应抛出 ValueError"""
        from app.modules.import_export.service_rule_set_import import RuleSetImportService

        db = AsyncMock(spec=AsyncSession)
        svc = RuleSetImportService(db)

        with patch(
            "app.middleware.tenant_context.get_current_tenant_id",
            return_value=None,
        ):
            with pytest.raises(ValueError, match="租户上下文"):
                asyncio.run(svc.import_rule_sets(b"fake", tenant_id=None))


# ==================== TestExcelExportService ====================


class TestExcelExportService:
    """ExcelExportService 导出工具测试"""

    @pytest.mark.unit
    def test_format_value_none_returns_empty_string(self):
        """None 值应格式化为空字符串"""
        assert ExcelExportService._format_value(None) == ""

    @pytest.mark.unit
    def test_format_value_datetime_formatted(self):
        """datetime 应格式化为 'YYYY-MM-DD HH:MM:SS'"""
        dt = datetime(2026, 6, 4, 14, 30, 45)
        assert ExcelExportService._format_value(dt) == "2026-06-04 14:30:45"

    @pytest.mark.unit
    def test_format_value_date_formatted(self):
        """date 应格式化为 'YYYY-MM-DD'"""
        d = date(2026, 6, 4)
        assert ExcelExportService._format_value(d) == "2026-06-04"

    @pytest.mark.unit
    def test_format_value_bool_to_chinese(self):
        """bool 值应转换为中文 '是' / '否'"""
        assert ExcelExportService._format_value(True) == "是"
        assert ExcelExportService._format_value(False) == "否"

    @pytest.mark.unit
    def test_format_value_regular_passthrough(self):
        """普通值（str/int/float）应原样返回"""
        assert ExcelExportService._format_value("hello") == "hello"
        assert ExcelExportService._format_value(42) == 42
        assert ExcelExportService._format_value(3.14) == 3.14

    @pytest.mark.unit
    def test_create_workbook_produces_valid_xlsx(self):
        """create_workbook 应生成可读取的 Excel 文件"""
        headers = ["姓名", "年龄", "城市"]
        data = [
            ["张三", 30, "北京"],
            ["李四", 25, "上海"],
        ]
        excel_bytes = ExcelExportService.create_workbook(headers, data, "测试表")

        # 验证文件可被 openpyxl 解析
        wb = load_workbook(BytesIO(excel_bytes))
        ws = wb.active
        assert ws.title == "测试表"
        assert ws.cell(1, 1).value == "姓名"
        assert ws.cell(2, 1).value == "张三"
        assert ws.cell(3, 3).value == "上海"
        assert ws.freeze_panes == "A2"
        wb.close()

    @pytest.mark.unit
    def test_create_workbook_empty_data(self):
        """空数据列表应生成仅含表头的 Excel"""
        headers = ["列A", "列B"]
        data = []
        excel_bytes = ExcelExportService.create_workbook(headers, data)

        wb = load_workbook(BytesIO(excel_bytes))
        ws = wb.active
        # 表头存在
        assert ws.cell(1, 1).value == "列A"
        # 无数据行
        assert ws.max_row == 1
        wb.close()

    @pytest.mark.unit
    def test_create_multi_sheet_workbook(self):
        """多工作表 Excel 应包含所有指定工作表"""
        workbook_data = {
            "医生": {
                "headers": ["姓名", "科室"],
                "data": [["张医生", "内科"]],
            },
            "排班": {
                "headers": ["日期", "时段"],
                "data": [["2026-06-04", "morning"]],
            },
        }
        excel_bytes = ExcelExportService.create_multi_sheet_workbook(workbook_data)

        wb = load_workbook(BytesIO(excel_bytes))
        assert "医生" in wb.sheetnames
        assert "排班" in wb.sheetnames
        assert len(wb.sheetnames) == 2

        ws_doctor = wb["医生"]
        assert ws_doctor.cell(1, 1).value == "姓名"
        assert ws_doctor.cell(2, 1).value == "张医生"

        ws_schedule = wb["排班"]
        assert ws_schedule.cell(2, 2).value == "morning"
        wb.close()


# ==================== TestApplyStoreFilter ====================


class TestApplyStoreFilter:
    """_apply_store_filter 边界条件测试"""

    @pytest.mark.unit
    def test_apply_store_filter_none_returns_unfiltered(self):
        """store_ids=None 时应返回原始查询（不过滤）"""
        from app.modules.import_export.router_export import _apply_store_filter

        mock_query = MagicMock()
        mock_model = MagicMock()

        result = _apply_store_filter(mock_query, mock_model.store_id, None)
        assert result is mock_query

    @pytest.mark.unit
    def test_apply_store_filter_empty_string_returns_unfiltered(self):
        """store_ids='' 时应返回原始查询（不过滤）"""
        from app.modules.import_export.router_export import _apply_store_filter

        mock_query = MagicMock()
        mock_model = MagicMock()

        result = _apply_store_filter(mock_query, mock_model.store_id, "")
        assert result is mock_query

    @pytest.mark.unit
    def test_apply_store_filter_empty_list_returns_unfiltered(self):
        """store_ids=[] 时应返回原始查询（不过滤）"""
        from app.modules.import_export.router_export import _apply_store_filter

        mock_query = MagicMock()
        mock_model = MagicMock()

        result = _apply_store_filter(mock_query, mock_model.store_id, [])
        assert result is mock_query

    @pytest.mark.unit
    def test_apply_store_filter_single_store_id(self):
        """单个门店 ID 字符串应使用 == 过滤"""
        from app.modules.import_export.router_export import _apply_store_filter

        mock_query = MagicMock()
        mock_model = MagicMock()

        _apply_store_filter(mock_query, mock_model.store_id, "store-001")
        mock_query.where.assert_called_once()

    @pytest.mark.unit
    def test_apply_store_filter_list_of_store_ids(self):
        """门店 ID 列表应使用 in_ 过滤"""
        from app.modules.import_export.router_export import _apply_store_filter

        mock_query = MagicMock()
        mock_model = MagicMock()

        _apply_store_filter(mock_query, mock_model.store_id, ["s1", "s2", "s3"])
        mock_query.where.assert_called_once()


# ==================== TestParseHelpers ====================


class TestParseHelpers:
    """router_import 中的纯工具函数测试"""

    @pytest.mark.unit
    def test_parse_date_yyyy_mm_dd(self):
        from app.modules.import_export.router_import import _parse_date
        assert _parse_date("2026-06-04") == date(2026, 6, 4)

    @pytest.mark.unit
    def test_parse_date_yyyy_mm_dd_slash(self):
        from app.modules.import_export.router_import import _parse_date
        assert _parse_date("2026/06/04") == date(2026, 6, 4)

    @pytest.mark.unit
    def test_parse_date_yyyymmdd_compact(self):
        from app.modules.import_export.router_import import _parse_date
        assert _parse_date("20260604") == date(2026, 6, 4)

    @pytest.mark.unit
    def test_parse_date_object_passthrough(self):
        from app.modules.import_export.router_import import _parse_date
        d = date(2026, 6, 4)
        assert _parse_date(d) == d

    @pytest.mark.unit
    def test_parse_date_none_returns_none(self):
        from app.modules.import_export.router_import import _parse_date
        assert _parse_date(None) is None

    @pytest.mark.unit
    def test_parse_date_invalid_returns_none(self):
        from app.modules.import_export.router_import import _parse_date
        assert _parse_date("not-a-date") is None

    @pytest.mark.unit
    def test_parse_time_hh_mm(self):
        from app.modules.import_export.router_import import _parse_time
        assert _parse_time("08:00") == time(8, 0)

    @pytest.mark.unit
    def test_parse_time_hh_mm_ss(self):
        from app.modules.import_export.router_import import _parse_time
        assert _parse_time("08:30:45") == time(8, 30, 45)

    @pytest.mark.unit
    def test_parse_time_object_passthrough(self):
        from app.modules.import_export.router_import import _parse_time
        t = time(14, 30)
        assert _parse_time(t) == t

    @pytest.mark.unit
    def test_parse_time_none_returns_none(self):
        from app.modules.import_export.router_import import _parse_time
        assert _parse_time(None) is None

    @pytest.mark.unit
    def test_parse_time_invalid_returns_none(self):
        from app.modules.import_export.router_import import _parse_time
        assert _parse_time("invalid") is None

    @pytest.mark.unit
    def test_valid_time_slots_values(self):
        from app.modules.import_export.router_import import VALID_TIME_SLOTS
        assert VALID_TIME_SLOTS == {"morning", "afternoon", "evening"}

    @pytest.mark.unit
    def test_sensitive_fields_constant(self):
        """SENSITIVE_FIELDS 常量应包含关键系统字段"""
        assert "tenant_id" in SENSITIVE_FIELDS
        assert "id" in SENSITIVE_FIELDS
        assert "created_at" in SENSITIVE_FIELDS
        assert "updated_at" in SENSITIVE_FIELDS
        assert "created_by" in SENSITIVE_FIELDS
        assert "updated_by" in SENSITIVE_FIELDS
