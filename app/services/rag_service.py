from typing import Any, Dict, List

from app.core.config import settings
from app.core.online_api import require_online_api
from app.db import postgres as db
from app.rag.chunker import chunk_text
from app.rag import index as rag_index
from app.rag.index import _uses_cloud_embedding


def get_rag_status() -> Dict[str, Any]:
    index_status = rag_index.get_index_status()
    chunk_stats = db.get_chunk_version_stats()
    usage = db.get_usage_summary()
    document_count = usage.get("document_count", 0)
    current_version = settings.effective_embedding_version
    warnings: List[str] = []

    if settings.database_enabled and document_count > 0:
        if not index_status["exists"] or index_status["vector_count"] == 0:
            warnings.append("数据库有文档但 FAISS 索引为空，需要重建索引")

    if index_status["exists"]:
        stored_dim = index_status.get("stored_dim")
        if stored_dim and stored_dim != settings.embedding_dim:
            warnings.append(
                f"索引维度 ({stored_dim}) 与当前配置 ({settings.embedding_dim}) 不一致，需要重建索引"
            )

        stored_version = index_status.get("stored_embedding_version")
        if stored_version and stored_version != current_version:
            warnings.append(
                f"索引版本 ({stored_version}) 与当前配置 ({current_version}) 不一致，需要重建索引"
            )

        stored_model = index_status.get("stored_embedding_model")
        if stored_model and stored_model != settings.embedding_model:
            warnings.append(
                f"索引模型 ({stored_model}) 与当前配置 ({settings.embedding_model}) 不一致，需要重建索引"
            )

        db_total = chunk_stats["total"]
        index_total = index_status["vector_count"]
        if db_total > 0 and index_total == 0:
            warnings.append("数据库有分块记录，但 FAISS 索引为空，需要重建索引")
        elif db_total > 0 and index_total > 0 and db_total != index_total:
            warnings.append(
                f"数据库分块数 ({db_total}) 与索引向量数 ({index_total}) 不一致，建议重建索引"
            )

    version_counts = chunk_stats.get("versions", {})
    if version_counts:
        stale_versions = [v for v in version_counts if v != current_version]
        if stale_versions:
            warnings.append(
                f"数据库存在旧 embedding 版本 ({', '.join(stale_versions)})，当前为 {current_version}"
            )

    if not index_status["exists"] and chunk_stats["total"] == 0:
        status = "empty"
    elif warnings:
        status = "needs_reindex"
    else:
        status = "ok"

    if settings.embedding_provider == "mock":
        warnings.append("当前使用 mock embedding（本地伪向量），仅用于流程联调，检索语义不可靠")

    if not settings.allow_online_api and settings.embedding_provider == "openai":
        warnings.append("在线 API 已禁用（ALLOW_ONLINE_API=false），openai embedding / 对话不会调用 GeekAI")

    if settings.embedding_provider == "local":
        warnings.append("本地 Embedding 尚未接入，请使用 EMBEDDING_PROVIDER=mock 或 openai")

    return {
        "status": status,
        "warnings": warnings,
        "chat_model": settings.default_model,
        "embedding": {
            "provider": settings.embedding_provider,
            "model": settings.embedding_model,
            "version": current_version,
            "dim": settings.embedding_dim,
            "device": settings.embedding_device if settings.embedding_provider == "local" else "cloud",
            "ready": settings.embedding_provider == "mock"
            or (
                settings.allow_online_api
                and settings.embedding_provider == "openai"
                and bool(settings.geekai_api_key)
            ),
        },
        "index": index_status,
        "database": {
            "enabled": settings.database_enabled,
            "document_count": document_count,
            "chunk_count": chunk_stats["total"],
            "chunk_versions": version_counts,
        },
    }


def reindex_all() -> Dict[str, Any]:
    if _uses_cloud_embedding():
        require_online_api("reindex embedding")
    if not settings.database_enabled:
        raise ValueError("Database not configured, cannot reindex from stored documents")

    documents = db.list_all_documents()
    rag_index.clear_index()

    documents_processed = 0
    chunks_indexed = 0

    for doc in documents:
        document_id = str(doc["id"])
        source = doc.get("source") or "upload"
        content = doc["content"]

        db.delete_chunks_for_document(document_id=document_id)
        chunks = chunk_text(content, source=source)
        chunk_texts = [item.text for item in chunks]

        if chunks:
            chunks_indexed += rag_index.add_documents(chunks)
            db.save_chunks(
                document_id=document_id,
                chunks=chunk_texts,
                embedding_version=settings.effective_embedding_version,
            )

        documents_processed += 1

    final_status = rag_index.get_index_status()
    return {
        "documents_processed": documents_processed,
        "chunks_indexed": chunks_indexed,
        "vector_count": final_status["vector_count"],
        "embedding_version": settings.effective_embedding_version,
    }
