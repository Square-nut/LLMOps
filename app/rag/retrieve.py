from typing import Optional

from app.core.config import settings
from app.rag.index import get_index


def retrieve_context(query: str, top_k: Optional[int] = None) -> str:
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
