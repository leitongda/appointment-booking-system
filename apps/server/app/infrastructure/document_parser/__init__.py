"""文档解析器装配：按扩展名选择解析器；类型白名单与 MIME 映射供上传校验复用"""
from app.infrastructure.document_parser.base import (
    BaseDocumentParser,
    Block,
    ParseError,
    ParseResult,
)

__all__ = [
    "SUPPORTED_EXTENSIONS",
    "BaseDocumentParser",
    "Block",
    "ParseError",
    "ParseResult",
    "file_extension",
    "get_parser",
]

# 扩展名 → 规范 MIME（上传时以扩展名为准，不信任客户端 Content-Type）
SUPPORTED_EXTENSIONS: dict[str, str] = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "txt": "text/plain",
    "md": "text/markdown",
}


def file_extension(filename: str) -> str:
    """取小写扩展名（不含点）；无扩展名返回空串"""
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def get_parser(ext: str) -> BaseDocumentParser:
    ext = (ext or "").lower().lstrip(".")
    if ext == "pdf":
        from app.infrastructure.document_parser.pdf import PdfParser

        return PdfParser()
    if ext == "docx":
        from app.infrastructure.document_parser.docx import DocxParser

        return DocxParser()
    if ext == "xlsx":
        from app.infrastructure.document_parser.xlsx import XlsxParser

        return XlsxParser()
    if ext in ("txt", "md"):
        from app.infrastructure.document_parser.text import TextParser

        return TextParser()
    raise ParseError(f"不支持的文件类型: .{ext or '?'}")
