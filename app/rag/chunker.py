from typing import Any


def chunk_text(text: str, source: str = "upload") -> list[Any]:
    """
    把长文本切成 300–800 token 左右的块。

    TODO Phase 2: 用 LlamaIndex SentenceSplitter，读 settings.chunk_size / chunk_overlap。
    返回带 metadata（如 source）的 Document 列表。
    """
    raise NotImplementedError("Phase 2: 在 rag/chunker.py 中实现分块")
