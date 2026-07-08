from app.core.config import settings
from app.db import postgres as db
from app.rag.chunker import chunk_text
from app.rag.index import add_documents


async def ingest_text(content: str, source: str = "upload") -> dict:
    doc_record = db.save_document(content=content, source=source)
    document_id = doc_record["id"] if doc_record else None

    documents = chunk_text(content, source=source)
    chunk_texts = [doc.text for doc in documents]
    indexed_count = add_documents(documents)

    if document_id:
        db.save_chunks(
            document_id=document_id,
            chunks=chunk_texts,
            embedding_version=settings.effective_embedding_version,
        )

    return {
        "document_id": document_id,
        "source": source,
        "chunks_indexed": indexed_count,
        "embedding_version": settings.effective_embedding_version,
    }
