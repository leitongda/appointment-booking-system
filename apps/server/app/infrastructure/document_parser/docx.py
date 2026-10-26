"""DOCX 解析（python-docx）：标题样式作为 section，表格按行拼接"""
from pathlib import Path

import docx

from app.infrastructure.document_parser.base import (
    BaseDocumentParser,
    Block,
    ParseError,
    ParseResult,
)


def _is_heading(style_name: str) -> bool:
    lowered = style_name.lower()
    return lowered.startswith("heading") or style_name.startswith("标题") or lowered == "title"


class DocxParser(BaseDocumentParser):
    def parse(self, path: Path) -> ParseResult:
        try:
            document = docx.Document(str(path))
        except Exception as exc:
            raise ParseError(f"Word 文档无法打开（{type(exc).__name__}）") from exc

        blocks: list[Block] = []
        section: str | None = None
        for para in document.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            style_name = para.style.name if para.style is not None and para.style.name else ""
            if _is_heading(style_name):
                section = text[:200]
            blocks.append(Block(text=text, section=section))

        for table in document.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                row_text = " | ".join(cell for cell in cells if cell)
                if row_text:
                    blocks.append(Block(text=row_text, section=section))

        if not blocks:
            raise ParseError("Word 文档未提取到任何文本")
        return ParseResult(blocks=blocks)
