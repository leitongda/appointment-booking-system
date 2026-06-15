"""Excel 导入基础服务"""
from datetime import datetime
from io import BytesIO
from typing import Any
from zipfile import BadZipFile

from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.utils.exceptions import InvalidFileException

try:
    from xlrd import XL_CELL_BOOLEAN, XL_CELL_DATE, XL_CELL_NUMBER, open_workbook
    from xlrd.biffh import XLRDError
    from xlrd.compdoc import CompDocError
    from xlrd.xldate import xldate_as_datetime
except ImportError:  # pragma: no cover - 依赖缺失时保留 .xlsx 能力
    XL_CELL_BOOLEAN = None
    XL_CELL_DATE = None
    XL_CELL_NUMBER = None
    CompDocError = None
    XLRDError = None
    open_workbook = None
    xldate_as_datetime = None


class ExcelImportError(ValueError):
    """Excel 导入解析异常"""


class ExcelImportService:
    """Excel 导入基础服务"""

    SUPPORTED_EXTENSIONS = (".xlsx", ".xls")

    @classmethod
    def _get_extension(cls, filename: str | None) -> str:
        if not filename:
            return ".xlsx"

        lowered = filename.lower()
        for extension in cls.SUPPORTED_EXTENSIONS:
            if lowered.endswith(extension):
                return extension

        raise ExcelImportError("请上传 .xlsx 或 .xls 格式的 Excel 文件")

    @classmethod
    def _load_xlsx_workbook(cls, file_content: bytes):
        """加载 .xlsx 工作簿并将底层解析异常转换为用户可理解的错误。"""
        if not file_content:
            raise ExcelImportError("导入文件不能为空，请重新上传")

        try:
            return load_workbook(filename=BytesIO(file_content), read_only=True)
        except BadZipFile as exc:
            raise ExcelImportError("Excel 文件无效或已损坏，请上传 .xlsx 或 .xls 格式的 Excel 文件") from exc
        except InvalidFileException as exc:
            raise ExcelImportError("Excel 文件无效或已损坏，请上传 .xlsx 或 .xls 格式的 Excel 文件") from exc

    @classmethod
    def _load_xls_workbook(cls, file_content: bytes):
        """加载 .xls 工作簿。"""
        if not file_content:
            raise ExcelImportError("导入文件不能为空，请重新上传")

        if open_workbook is None:
            raise ExcelImportError(".xls 解析依赖未安装，请先安装 xlrd")

        handled_errors = tuple(
            error_type
            for error_type in (XLRDError, CompDocError)
            if error_type is not None
        )

        try:
            return open_workbook(file_contents=file_content)
        except handled_errors as exc:
            raise ExcelImportError("Excel 文件无效或已损坏，请上传 .xlsx 或 .xls 格式的 Excel 文件") from exc

    @classmethod
    def _load_workbook(cls, file_content: bytes, filename: str | None = None):
        extension = cls._get_extension(filename)
        if extension == ".xls":
            return extension, cls._load_xls_workbook(file_content)
        return extension, cls._load_xlsx_workbook(file_content)

    @classmethod
    def _normalize_xls_value(cls, cell, datemode: int) -> Any:
        value = cell.value
        if value in ("", None):
            return None

        if XL_CELL_DATE is not None and cell.ctype == XL_CELL_DATE:
            converted = xldate_as_datetime(value, datemode)
            if converted.time() == datetime.min.time():
                return converted.date()
            return converted

        if XL_CELL_BOOLEAN is not None and cell.ctype == XL_CELL_BOOLEAN:
            return bool(value)

        if XL_CELL_NUMBER is not None and cell.ctype == XL_CELL_NUMBER and isinstance(value, float):
            return int(value) if value.is_integer() else value

        if isinstance(value, str):
            value = value.strip()
            return value or None

        return value

    @classmethod
    def _parse_xlsx(
        cls,
        workbook,
        expected_headers: list[str],
        required_fields: list[str] | None = None,
        sheet_index: int = 0
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        try:
            ws = workbook.worksheets[sheet_index]
        except IndexError as exc:
            raise ExcelImportError("Excel 工作表不存在，请使用系统提供的导入模板") from exc

        headers = []
        for cell in ws[1]:
            headers.append(str(cell.value).strip() if cell.value else "")

        header_mapping = cls._validate_headers(headers, expected_headers)
        if not header_mapping:
            raise ExcelImportError("导入模板表头不匹配，请使用系统提供的导入模板")

        valid_rows = []
        error_rows = []
        required_fields = required_fields or []

        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
            if not any(row):
                continue

            row_data = {}
            errors = []

            for expected_header in expected_headers:
                col_idx = header_mapping.get(expected_header)
                if col_idx is not None and col_idx < len(row):
                    value = row[col_idx]
                    if isinstance(value, str):
                        value = value.strip()
                    row_data[expected_header] = value if value else None
                else:
                    row_data[expected_header] = None

            for field in required_fields:
                if not row_data.get(field):
                    errors.append(f"'{field}' 为必填项")

            if errors:
                error_rows.append({
                    "row": row_idx,
                    "data": row_data,
                    "errors": errors
                })
            else:
                row_data["_row"] = row_idx
                valid_rows.append(row_data)

        return valid_rows, error_rows

    @classmethod
    def _parse_xls(
        cls,
        workbook,
        expected_headers: list[str],
        required_fields: list[str] | None = None,
        sheet_index: int = 0
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        try:
            sheet = workbook.sheet_by_index(sheet_index)
        except IndexError as exc:
            raise ExcelImportError("Excel 工作表不存在，请使用系统提供的导入模板") from exc

        if sheet.nrows == 0:
            raise ExcelImportError("导入模板表头不匹配，请使用系统提供的导入模板")

        headers = []
        for cell in sheet.row(0):
            value = cell.value.strip() if isinstance(cell.value, str) else cell.value
            headers.append(str(value).strip() if value else "")

        header_mapping = cls._validate_headers(headers, expected_headers)
        if not header_mapping:
            raise ExcelImportError("导入模板表头不匹配，请使用系统提供的导入模板")

        valid_rows = []
        error_rows = []
        required_fields = required_fields or []

        for row_idx in range(1, sheet.nrows):
            row = sheet.row(row_idx)
            row_values = [cls._normalize_xls_value(cell, workbook.datemode) for cell in row]
            if not any(value not in (None, "") for value in row_values):
                continue

            row_data = {}
            errors = []

            for expected_header in expected_headers:
                col_idx = header_mapping.get(expected_header)
                if col_idx is not None and col_idx < len(row):
                    row_data[expected_header] = row_values[col_idx]
                else:
                    row_data[expected_header] = None

            for field in required_fields:
                if not row_data.get(field):
                    errors.append(f"'{field}' 为必填项")

            if errors:
                error_rows.append({
                    "row": row_idx + 1,
                    "data": row_data,
                    "errors": errors,
                })
            else:
                row_data["_row"] = row_idx + 1
                valid_rows.append(row_data)

        return valid_rows, error_rows

    @classmethod
    def _close_workbook(cls, extension: str, workbook) -> None:
        if extension == ".xlsx" and hasattr(workbook, "close"):
            workbook.close()
            return
        if extension == ".xls" and hasattr(workbook, "release_resources"):
            workbook.release_resources()

    @classmethod
    def parse_excel(
        cls,
        file_content: bytes,
        expected_headers: list[str],
        required_fields: list[str] | None = None,
        sheet_index: int = 0,
        filename: str | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        解析 Excel 文件

        Args:
            file_content: Excel 文件二进制内容
            expected_headers: 期望的表头列表
            required_fields: 必填字段列表
            sheet_index: 工作表索引

        Returns:
            (valid_rows, error_rows) - 有效数据行和错误数据行
        """
        extension, workbook = cls._load_workbook(file_content, filename=filename)
        try:
            if extension == ".xls":
                return cls._parse_xls(workbook, expected_headers, required_fields, sheet_index)
            return cls._parse_xlsx(workbook, expected_headers, required_fields, sheet_index)
        finally:
            cls._close_workbook(extension, workbook)

    @classmethod
    def _validate_headers(
        cls,
        actual_headers: list[str],
        expected_headers: list[str]
    ) -> dict[str, int] | None:
        """
        验证表头并返回映射关系

        Returns:
            表头到列索引的映射，如果验证失败返回 None
        """
        mapping = {}
        for expected in expected_headers:
            for idx, actual in enumerate(actual_headers):
                if actual == expected:
                    mapping[expected] = idx
                    break

        # 检查是否所有期望的表头都找到了
        if len(mapping) == len(expected_headers):
            return mapping

        # 尝试模糊匹配（去除空格、括号等）
        def normalize(s: str) -> str:
            return s.replace(" ", "").replace("（", "(").replace("）", ")").lower()

        mapping = {}
        for expected in expected_headers:
            for idx, actual in enumerate(actual_headers):
                if normalize(actual) == normalize(expected):
                    mapping[expected] = idx
                    break

        if len(mapping) == len(expected_headers):
            return mapping

        return None

    @classmethod
    def create_template(
        cls,
        headers: list[str],
        sample_data: list[list[Any]] | None = None,
        required_fields: list[str] | None = None,
        field_notes: dict[str, str] | None = None,
        sheet_name: str = "导入模板"
    ) -> bytes:
        """
        创建导入模板

        Args:
            headers: 表头列表
            sample_data: 示例数据
            required_fields: 必填字段列表
            field_notes: 字段说明
            sheet_name: 工作表名称

        Returns:
            Excel 模板文件的二进制内容
        """
        wb = Workbook()
        ws = wb.active
        ws.title = sheet_name

        required_fields = required_fields or []
        field_notes = field_notes or {}

        # 表头样式
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        required_fill = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")

        # 写入表头
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = required_fill if header in required_fields else header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

            # 添加批注说明
            if header in field_notes:
                cell.comment = Comment(field_notes[header], "system")

        # 写入示例数据
        if sample_data:
            for row_idx, row_data in enumerate(sample_data, 2):
                for col_idx, value in enumerate(row_data, 1):
                    cell = ws.cell(row=row_idx, column=col_idx, value=value)
                    cell.alignment = Alignment(horizontal="left", vertical="center")

        # 设置列宽
        for col_idx, header in enumerate(headers, 1):
            max_length = len(str(header)) * 2
            if sample_data:
                for row_data in sample_data:
                    if col_idx <= len(row_data) and row_data[col_idx - 1]:
                        cell_value = str(row_data[col_idx - 1])
                        cell_length = sum(2 if ord(c) > 127 else 1 for c in cell_value)
                        max_length = max(max_length, cell_length)
            ws.column_dimensions[get_column_letter(col_idx)].width = min(max_length + 4, 40)

        # 添加说明工作表
        ws_notes = wb.create_sheet("填写说明")
        notes = [
            ["字段名", "是否必填", "说明"],
        ]
        for header in headers:
            notes.append([
                header,
                "是" if header in required_fields else "否",
                field_notes.get(header, "")
            ])

        for row_idx, row_data in enumerate(notes, 1):
            for col_idx, value in enumerate(row_data, 1):
                cell = ws_notes.cell(row=row_idx, column=col_idx, value=value)
                if row_idx == 1:
                    cell.font = Font(bold=True)
                    cell.fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")

        ws_notes.column_dimensions["A"].width = 20
        ws_notes.column_dimensions["B"].width = 12
        ws_notes.column_dimensions["C"].width = 50

        # 保存到内存
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()
