from typing import Any, Dict, List

from app.core.config import settings
from app.core.llm_gateway import completion
from app.core.online_api import require_online_api
from app.db import postgres as db
from app.rag.chunker import chunk_text
from app.rag import index as rag_index
from app.rag.index import _uses_cloud_embedding
from app.rag.local_embedding import local_embedding_config_ready, probe_local_embedding


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
        if settings.embedding_backend == "tei" and not settings.embedding_api_base.strip():
            warnings.append(
                "本地 Embedding 使用 TEI 远程模式，请配置 EMBEDDING_API_BASE（Win PC 服务地址）"
            )
        elif settings.embedding_backend == "huggingface":
            warnings.append(
                "本地 Embedding 使用 HuggingFace 进程内加载，需在本机安装 sentence-transformers 与 PyTorch"
            )

    embedding_device = "cloud"
    if settings.embedding_provider == "local":
        embedding_device = (
            "remote" if settings.embedding_backend == "tei" else settings.embedding_device
        )

    embedding_ready = False
    if settings.embedding_provider == "mock":
        embedding_ready = True
    elif settings.embedding_provider == "openai":
        embedding_ready = settings.allow_online_api and bool(settings.geekai_api_key)
    elif settings.embedding_provider == "local":
        embedding_ready = local_embedding_config_ready()

    return {
        "status": status,
        "warnings": warnings,
        "chat_model": settings.default_model,
        "embedding": {
            "provider": settings.embedding_provider,
            "backend": settings.embedding_backend if settings.embedding_provider == "local" else None,
            "model": settings.embedding_model,
            "version": current_version,
            "dim": settings.embedding_dim,
            "device": embedding_device,
            "api_base": settings.embedding_api_base or None,
            "ready": embedding_ready,
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


def check_embedding() -> Dict[str, Any]:
    if settings.embedding_provider == "openai":
        require_online_api("embedding check")
        from app.rag.index import _get_embed_model

        embed_model = _get_embed_model()
        sample = "embedding health check"
        vector = embed_model._get_text_embedding(sample)
        return {
            "ok": True,
            "backend": "openai",
            "model": settings.embedding_model,
            "dim": len(vector),
            "device": "cloud",
            "api_base": settings.geekai_base_url,
            "sample": sample,
        }

    if settings.embedding_provider == "local":
        return probe_local_embedding()

    raise ValueError(
        f"Embedding check is not supported for provider={settings.embedding_provider!r}"
    )


def check_chat_model() -> Dict[str, Any]:
    input_text = "请只回复 ok"
    result = completion(
        input_text,
        system_prompt="你是系统状态检查助手。请只返回 ok。",
        use_mock=False,
    )
    db.log_chat(
        user_id="system:model-check",
        input_text=input_text,
        output_text=result["content"],
        model=result["model"],
        tokens=result["tokens"],
        latency_ms=result["latency_ms"],
    )
    return {
        "ok": True,
        "model": result["model"],
        "latency_ms": result["latency_ms"],
        "reply": result["content"],
    }
