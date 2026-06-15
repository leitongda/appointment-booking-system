"""Excel 导出基础服务"""
from datetime import date, datetime
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


class ExcelExportService:
    """Excel 导出基础服务"""

    # 表头样式
    HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
    HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # 单元格样式
    CELL_ALIGNMENT = Alignment(horizontal="left", vertical="center")
    CELL_BORDER = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )

    @classmethod
    def create_workbook(
        cls,
        headers: list[str],
        data: list[list[Any]],
        sheet_name: str = "数据",
        column_widths: list[int] | None = None
    ) -> bytes:
        """
        创建 Excel 工作簿

        Args:
            headers: 表头列表
            data: 数据列表（二维数组）
            sheet_name: 工作表名称
            column_widths: 列宽列表（可选）

        Returns:
            Excel 文件的二进制内容
        """
        wb = Workbook()
        ws = wb.active
        ws.title = sheet_name

        # 写入表头
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = cls.HEADER_FONT
            cell.fill = cls.HEADER_FILL
            cell.alignment = cls.HEADER_ALIGNMENT
            cell.border = cls.CELL_BORDER

        # 写入数据
        for row_idx, row_data in enumerate(data, 2):
            for col_idx, value in enumerate(row_data, 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=cls._format_value(value))
                cell.alignment = cls.CELL_ALIGNMENT
                cell.border = cls.CELL_BORDER

        # 设置列宽
        if column_widths:
            for col_idx, width in enumerate(column_widths, 1):
                ws.column_dimensions[get_column_letter(col_idx)].width = width
        else:
            # 自动调整列宽
            for col_idx, header in enumerate(headers, 1):
                max_length = len(str(header)) * 2  # 中文字符占2个宽度
                for row_data in data:
                    if col_idx <= len(row_data):
                        cell_value = str(row_data[col_idx - 1]) if row_data[col_idx - 1] else ""
                        # 计算字符宽度（中文2，英文1）
                        cell_length = sum(2 if ord(c) > 127 else 1 for c in cell_value)
                        max_length = max(max_length, cell_length)
                ws.column_dimensions[get_column_letter(col_idx)].width = min(max_length + 2, 50)

        # 冻结首行
        ws.freeze_panes = "A2"

        # 保存到内存
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()

    @classmethod
    def _format_value(cls, value: Any) -> Any:
        """格式化单元格值"""
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(value, date):
            return value.strftime("%Y-%m-%d")
        if isinstance(value, bool):
            return "是" if value else "否"
        return value

    @classmethod
    def create_multi_sheet_workbook(
        cls,
        workbook_data: dict[str, dict[str, Any]]
    ) -> bytes:
        """
        创建多工作表 Excel 工作簿

        Args:
            workbook_data: 工作簿数据，格式为 {工作表名: {"headers": [], "data": []}}

        Returns:
            Excel 文件的二进制内容
        """
        wb = Workbook()
        # 删除默认工作表
        if wb.active:
            wb.remove(wb.active)

        for sheet_name, sheet_data in workbook_data.items():
            ws = wb.create_sheet(title=sheet_name)
            headers = sheet_data["headers"]
            data = sheet_data["data"]

            # 写入表头
            for col_idx, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col_idx, value=header)
                cell.font = cls.HEADER_FONT
                cell.fill = cls.HEADER_FILL
                cell.alignment = cls.HEADER_ALIGNMENT
                cell.border = cls.CELL_BORDER

            # 写入数据
            for row_idx, row_data in enumerate(data, 2):
                for col_idx, value in enumerate(row_data, 1):
                    cell = ws.cell(row=row_idx, column=col_idx, value=cls._format_value(value))
                    cell.alignment = cls.CELL_ALIGNMENT
                    cell.border = cls.CELL_BORDER

            # 自动调整列宽
            for col_idx, header in enumerate(headers, 1):
                max_length = len(str(header)) * 2
                for row_data in data:
                    if col_idx <= len(row_data):
                        cell_value = str(row_data[col_idx - 1]) if row_data[col_idx - 1] else ""
                        cell_length = sum(2 if ord(c) > 127 else 1 for c in cell_value)
                        max_length = max(max_length, cell_length)
                ws.column_dimensions[get_column_letter(col_idx)].width = min(max_length + 2, 50)

            # 冻结首行
            ws.freeze_panes = "A2"

        # 保存到内存
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()

    @classmethod
    def create_multi_sheet_template(
        cls,
        workbook_data: dict[str, dict[str, Any]]
    ) -> bytes:
        """
        创建多工作表 Excel 模板

        Args:
            workbook_data: 工作簿数据，格式为 {工作表名: {"headers": [], "data": [], "field_notes": {}}}

        Returns:
            Excel 模板文件的二进制内容
        """
        wb = Workbook()
        # 删除默认工作表
        if wb.active:
            wb.remove(wb.active)

        for sheet_name, sheet_data in workbook_data.items():
            ws = wb.create_sheet(title=sheet_name[:31])  # Excel 工作表名最多31字符
            headers = sheet_data["headers"]
            sample_data = sheet_data.get("data", [])
            field_notes = sheet_data.get("field_notes", {})

            required_fill = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")

            # 写入表头
            for col_idx, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col_idx, value=header)
                cell.font = cls.HEADER_FONT
                cell.fill = required_fill if header in field_notes else cls.HEADER_FILL
                cell.alignment = cls.HEADER_ALIGNMENT
                cell.border = cls.CELL_BORDER

            # 写入示例数据
            if sample_data:
                for row_idx, row_data in enumerate(sample_data, 2):
                    for col_idx, value in enumerate(row_data, 1):
                        cell = ws.cell(row=row_idx, column=col_idx, value=value)
                        cell.alignment = cls.CELL_ALIGNMENT
                        cell.border = cls.CELL_BORDER

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

            # 冻结首行
            ws.freeze_panes = "A2"

        # 保存到内存
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()
