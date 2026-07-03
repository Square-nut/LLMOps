async def ingest_text(content: str, source: str = "upload") -> dict:
    """
    文档入库编排（ARCHITECTURE.md §7）。

    建议实现顺序：
    1. supabase.save_document
    2. rag.chunker.chunk_text
    3. rag.index.add_documents
    4. supabase.save_chunks
    """
    raise NotImplementedError("Phase 2+: 在 services/ingest_service.py 中实现 ingest 编排")
