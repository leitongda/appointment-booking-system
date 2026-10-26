"""TXT / Markdown 解析：按空行切段，Markdown 的 # 标题作 section"""
from pathlib import Path

from app.infrastructure.document_parser.base import (
    BaseDocumentParser,
    Block,
    ParseError,
    ParseResult,
    split_paragraphs,
)

_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030")


def _decode(raw: bytes) -> str:
    for encoding in _ENCODINGS:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


class TextParser(BaseDocumentParser):
    def parse(self, path: Path) -> ParseResult:
        try:
            text = _decode(path.read_bytes())
        except OSError as exc:
            raise ParseError(f"文本文件无法读取（{type(exc).__name__}）") from exc

        is_markdown = path.suffix.lower() == ".md"
        blocks: list[Block] = []
        section: str | None = None
        for para in split_paragraphs(text):
            if is_markdown and para.lstrip().startswith("#"):
                heading = para.lstrip().lstrip("#").strip()
                if heading:
                    section = heading[:200]
                    blocks.append(Block(text=heading, section=section))
                continue
            blocks.append(Block(text=para, section=section))

        if not blocks:
            raise ParseError("文档为空，未提取到任何文本")
        return ParseResult(blocks=blocks)
