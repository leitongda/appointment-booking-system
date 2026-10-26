"""切片器单元测试（纯函数，无 DB）"""
from app.infrastructure.document_parser.base import Block
from app.modules.knowledge.chunker import chunk_blocks


def test_aggregates_small_paragraphs_until_limit():
    blocks = [Block(text=f"段落{i}" * 20, page_no=1) for i in range(10)]  # 每段 60 字符
    chunks = chunk_blocks(blocks, max_chars=200, overlap=0)

    assert len(chunks) > 1
    assert [c.seq for c in chunks] == list(range(len(chunks)))
    assert all(len(c.content) <= 200 for c in chunks)
    assert all(c.page_no == 1 for c in chunks)
    # 不丢内容：所有段落都出现在某个切片里
    joined = "\n".join(c.content for c in chunks)
    assert all(block.text in joined for block in blocks)


def test_flushes_on_section_change():
    blocks = [
        Block(text="甲甲甲", section="第一章"),
        Block(text="乙乙乙", section="第一章"),
        Block(text="丙丙丙", section="第二章"),
    ]
    chunks = chunk_blocks(blocks, max_chars=800, overlap=0)

    assert [c.section for c in chunks] == ["第一章", "第二章"]
    assert chunks[0].content == "甲甲甲\n乙乙乙"
    assert chunks[1].content == "丙丙丙"


def test_long_paragraph_is_split_with_overlap():
    sentence = "这是一个用于测试的句子。"
    text = sentence * 100  # 1200 字符，远超上限
    chunks = chunk_blocks([Block(text=text, page_no=3)], max_chars=300, overlap=40)

    assert len(chunks) >= 4
    assert all(len(c.content) <= 300 for c in chunks)
    assert all(c.page_no == 3 for c in chunks)
    # 相邻片段存在重叠：后一片的开头出现在前一片的尾部
    for prev, nxt in zip(chunks, chunks[1:], strict=False):
        assert nxt.content[:10] in prev.content


def test_overlap_carries_tail_into_next_chunk():
    blocks = [Block(text="一" * 150), Block(text="二" * 150), Block(text="三" * 150)]
    chunks = chunk_blocks(blocks, max_chars=200, overlap=20)

    assert len(chunks) == 3
    assert chunks[1].content.startswith("一" * 20)
    assert chunks[2].content.startswith("二" * 20)


def test_ignores_empty_blocks_and_estimates_tokens():
    chunks = chunk_blocks([Block(text="   "), Block(text=""), Block(text="有效内容")], max_chars=800)

    assert len(chunks) == 1
    assert chunks[0].content == "有效内容"
    assert chunks[0].token_count >= 1


def test_page_no_taken_from_first_block_of_chunk():
    blocks = [Block(text="页一内容", page_no=1), Block(text="页二内容", page_no=2)]
    chunks = chunk_blocks(blocks, max_chars=800, overlap=0)

    assert len(chunks) == 1
    assert chunks[0].page_no == 1
