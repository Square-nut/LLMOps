from typing import Optional

from app.core.config import settings
from app.core.online_api import require_online_api
from app.rag.index import get_index, _uses_cloud_embedding


def _mock_context(query: str) -> str:
    if not settings.mock_rag_enabled or settings.embedding_provider != "mock":
        return ""

    if query.strip() != settings.mock_rag_query.strip():
        return ""

    return f"[1] (source: {settings.mock_rag_source})\n{settings.mock_rag_context}"


def retrieve_context(query: str, top_k: Optional[int] = None) -> str:
    context = _mock_context(query)
    if context:
        return context
    if settings.embedding_provider == "mock" and settings.mock_rag_enabled:
        return ""

    if _uses_cloud_embedding():
        require_online_api("RAG retrieval embedding")
    k = top_k or settings.retrieval_top_k
    index = get_index()
    retriever = index.as_retriever(similarity_top_k=k)
    nodes = retriever.retrieve(query)

    if not nodes:
        return ""

    parts = []
    for i, node in enumerate(nodes, start=1):
        source = node.metadata.get("source", "unknown")
        parts.append(f"[{i}] (source: {source})\n{node.get_content()}")

    return "\n\n".join(parts)
