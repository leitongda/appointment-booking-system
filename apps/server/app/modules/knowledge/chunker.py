"""切片：按段落聚合到目标字符数并带重叠；保留 page_no / section / seq 作为引用定位依据"""
from dataclasses import dataclass

from app.infrastructure.document_parser.base import Block

_SENTENCE_ENDS = "。！？；!?;\n"


@dataclass
class Chunk:
    seq: int
    content: str
    page_no: int | None
    section: str | None
    token_count: int


def estimate_tokens(text: str) -> int:
    """中文为主的文本约 1.3 字符 ≈ 1 token（智谱/通用分词器经验值）"""
    return max(1, round(len(text) / 1.3))


def _split_long(text: str, max_chars: int, overlap: int) -> list[str]:
    """超长段落：优先在后半段的句末标点处切，退化为硬切；相邻片段保留 overlap 重叠"""
    pieces: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + max_chars, length)
        if end < length:
            window_start = start + max_chars // 2
            cut = max(text.rfind(mark, window_start, end) for mark in _SENTENCE_ENDS)
            if cut > start:
                end = cut + 1
        piece = text[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return pieces


def chunk_blocks(blocks: list[Block], max_chars: int = 800, overlap: int = 80) -> list[Chunk]:
    """段落聚合切片。

    - 缓冲区满或 section 变化时落一片；片的 page_no/section 取首段落的值
    - 新片开头带上一片尾部 overlap 字符，保证跨片语义不断
    - 单段超过 max_chars 时单独按句切分（自带重叠）
    """
    max_chars = max(50, max_chars)
    overlap = max(0, min(overlap, max_chars // 2))

    chunks: list[Chunk] = []
    buffer: list[str] = []
    buffer_len = 0
    buffer_page: int | None = None
    buffer_section: str | None = None
    carry = ""

    def flush() -> None:
        nonlocal buffer, buffer_len, buffer_page, buffer_section, carry
        if buffer:
            content = "\n".join(buffer).strip()
            if content:
                chunks.append(
                    Chunk(
                        seq=len(chunks),
                        content=content,
                        page_no=buffer_page,
                        section=buffer_section,
                        token_count=estimate_tokens(content),
                    )
                )
                carry = content[-overlap:] if overlap and len(content) > overlap else ""
        buffer, buffer_len = [], 0
        buffer_page, buffer_section = None, None

    for block in blocks:
        text = (block.text or "").strip()
        if not text:
            continue

        if buffer and (buffer_len + len(text) + 1 > max_chars or block.section != buffer_section):
            flush()

        if len(text) > max_chars:
            flush()
            for piece in _split_long(text, max_chars, overlap):
                chunks.append(
                    Chunk(
                        seq=len(chunks),
                        content=piece,
                        page_no=block.page_no,
                        section=block.section,
                        token_count=estimate_tokens(piece),
                    )
                )
            carry = ""
            continue

        if not buffer:
            buffer_page, buffer_section = block.page_no, block.section
            if carry:
                buffer.append(carry)
                buffer_len = len(carry)
                carry = ""
        buffer.append(text)
        buffer_len += len(text) + 1

    flush()
    return chunks
