from typing import Optional


def retrieve_context(query: str, top_k: Optional[int] = None) -> str:
    """
    根据用户问题检索相关上下文，拼成字符串返回。

    TODO Phase 2: 用 get_index().as_retriever(similarity_top_k=...) 检索。
    """
    raise NotImplementedError("Phase 2: 在 rag/retrieve.py 中实现检索")
