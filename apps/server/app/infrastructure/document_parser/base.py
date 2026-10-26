"""文档解析器抽象：统一产出带页码/章节的文本块"""
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")


class ParseError(Exception):
    """解析失败；message 必须是用户可读的中文原因（会直接落 error_message 展示给用户）"""


@dataclass
class Block:
    text: str
    page_no: int | None = None
    section: str | None = None


@dataclass
class ParseResult:
    blocks: list[Block] = field(default_factory=list)
    page_count: int | None = None


class BaseDocumentParser(ABC):
    @abstractmethod
    def parse(self, path: Path) -> ParseResult:
        """同步解析（在 Celery worker 内执行）；失败抛 ParseError"""


def split_paragraphs(text: str) -> list[str]:
    """按空行切段，去掉首尾空白与空段"""
    if not text:
        return []
    return [para.strip() for para in _PARAGRAPH_SPLIT.split(text) if para and para.strip()]
