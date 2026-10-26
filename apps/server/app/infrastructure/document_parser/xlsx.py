"""XLSX 解析（openpyxl，只读模式）：sheet 名作 section，每行拼成一段"""
from pathlib import Path

from openpyxl import load_workbook

from app.infrastructure.document_parser.base import (
    BaseDocumentParser,
    Block,
    ParseError,
    ParseResult,
)


class XlsxParser(BaseDocumentParser):
    def parse(self, path: Path) -> ParseResult:
        try:
            workbook = load_workbook(str(path), read_only=True, data_only=True)
        except Exception as exc:
            raise ParseError(f"Excel 文件无法打开（{type(exc).__name__}）") from exc

        blocks: list[Block] = []
        try:
            for sheet in workbook.worksheets:
                section = (sheet.title or "")[:200] or None
                for row in sheet.iter_rows(values_only=True):
                    cells = [str(value).strip() for value in row if value is not None and str(value).strip()]
                    if cells:
                        blocks.append(Block(text=" | ".join(cells), section=section))
        finally:
            workbook.close()

        if not blocks:
            raise ParseError("Excel 文件未提取到任何内容")
        return ParseResult(blocks=blocks)
