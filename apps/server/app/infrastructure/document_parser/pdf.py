"""PDF 解析（pypdf，仅文本层；扫描件明确失败）"""
from pathlib import Path

from pypdf import PdfReader

from app.infrastructure.document_parser.base import (
    BaseDocumentParser,
    Block,
    ParseError,
    ParseResult,
    split_paragraphs,
)

SCANNED_PDF_MESSAGE = "PDF 无文本层（疑似扫描件），暂不支持 OCR"


class PdfParser(BaseDocumentParser):
    def parse(self, path: Path) -> ParseResult:
        try:
            reader = PdfReader(str(path))
        except Exception as exc:
            raise ParseError(f"PDF 无法打开（{type(exc).__name__}）") from exc

        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:
                raise ParseError("PDF 已加密，无法读取") from exc

        blocks: list[Block] = []
        for page_no, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            for para in split_paragraphs(text):
                blocks.append(Block(text=para, page_no=page_no))

        if not blocks:
            raise ParseError(SCANNED_PDF_MESSAGE)
        return ParseResult(blocks=blocks, page_count=len(reader.pages))
