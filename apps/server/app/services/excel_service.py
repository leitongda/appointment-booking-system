"""Excel 导入导出基础服务"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
from io import BytesIO
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
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
        headers: List[str],
        data: List[List[Any]],
        sheet_name: str = "数据",
        column_widths: Optional[List[int]] = None
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
        workbook_data: Dict[str, Dict[str, Any]]
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
        workbook_data: Dict[str, Dict[str, Any]]
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


class ExcelImportService:
    """Excel 导入基础服务"""
    
    @classmethod
    def parse_excel(
        cls,
        file_content: bytes,
        expected_headers: List[str],
        required_fields: Optional[List[str]] = None,
        sheet_index: int = 0
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
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
        wb = load_workbook(filename=BytesIO(file_content), read_only=True)
        ws = wb.worksheets[sheet_index]
        
        # 读取表头
        headers = []
        for cell in ws[1]:
            headers.append(str(cell.value).strip() if cell.value else "")
        
        # 验证表头
        header_mapping = cls._validate_headers(headers, expected_headers)
        if not header_mapping:
            raise ValueError(f"表头不匹配，期望: {expected_headers}, 实际: {headers}")
        
        valid_rows = []
        error_rows = []
        required_fields = required_fields or []
        
        # 读取数据行
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
            if not any(row):  # 跳过空行
                continue
            
            row_data = {}
            errors = []
            
            for expected_header in expected_headers:
                col_idx = header_mapping.get(expected_header)
                if col_idx is not None and col_idx < len(row):
                    value = row[col_idx]
                    # 处理值
                    if isinstance(value, str):
                        value = value.strip()
                    row_data[expected_header] = value if value else None
                else:
                    row_data[expected_header] = None
            
            # 验证必填字段
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
        
        wb.close()
        return valid_rows, error_rows
    
    @classmethod
    def _validate_headers(
        cls,
        actual_headers: List[str],
        expected_headers: List[str]
    ) -> Optional[Dict[str, int]]:
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
        headers: List[str],
        sample_data: Optional[List[List[Any]]] = None,
        required_fields: Optional[List[str]] = None,
        field_notes: Optional[Dict[str, str]] = None,
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
                cell.comment = field_notes[header]
        
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

