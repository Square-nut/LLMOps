import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import faiss
from llama_index.core import (
    Document,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.faiss import FaissVectorStore

from app.core.config import settings
from app.core.logger import logger
from app.core.online_api import require_online_api
from app.rag.local_embedding import get_local_embed_model
from app.rag.mock_embedding import MockEmbedding

_index: Optional[VectorStoreIndex] = None
_META_FILE = "meta.json"


def _uses_cloud_embedding() -> bool:
    return settings.embedding_provider == "openai"


def _get_embed_model():
    if settings.embedding_provider == "mock":
        return MockEmbedding(embed_dim=settings.embedding_dim)
    if settings.embedding_provider == "local":
        return get_local_embed_model()
    return OpenAIEmbedding(
        model=settings.embedding_model,
        api_key=settings.geekai_api_key,
        api_base=settings.geekai_base_url,
    )


def _index_dir() -> Path:
    path = Path(settings.faiss_index_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _meta_path() -> Path:
    return _index_dir() / _META_FILE


def _read_index_meta() -> Optional[Dict[str, Any]]:
    path = _meta_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read index meta: %s", exc)
        return None


def _write_index_meta(vector_count: int) -> None:
    meta = {
        "embedding_model": settings.embedding_model,
        "embedding_provider": settings.embedding_provider,
        "embedding_dim": settings.embedding_dim,
        "embedding_version": settings.effective_embedding_version,
        "vector_count": vector_count,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _meta_path().write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _faiss_store_exists() -> bool:
    return (_index_dir() / "default__vector_store.json").exists()


def _read_vector_count() -> int:
    meta = _read_index_meta()
    if meta is not None and "vector_count" in meta:
        return int(meta["vector_count"])

    if not _faiss_store_exists():
        return 0

    try:
        vector_store = FaissVectorStore.from_persist_dir(str(_index_dir()))
        faiss_index = vector_store.client
        return int(getattr(faiss_index, "ntotal", 0) or 0)
    except Exception as exc:
        logger.warning("Failed to read FAISS vector count: %s", exc)
        return 0


def _read_stored_dim() -> Optional[int]:
    meta = _read_index_meta()
    if meta is not None and meta.get("embedding_dim") is not None:
        return int(meta["embedding_dim"])

    if not _faiss_store_exists():
        return None

    try:
        vector_store = FaissVectorStore.from_persist_dir(str(_index_dir()))
        faiss_index = vector_store.client
        return int(getattr(faiss_index, "d", 0) or 0) or None
    except Exception as exc:
        logger.warning("Failed to read FAISS dimension: %s", exc)
        return None


def reset_index_cache() -> None:
    global _index
    _index = None


def clear_index() -> None:
    reset_index_cache()
    index_dir = _index_dir()
    if index_dir.exists():
        shutil.rmtree(index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Cleared FAISS index at %s", index_dir)


def get_index_status() -> Dict[str, Any]:
    meta = _read_index_meta()
    exists = _faiss_store_exists()
    stored_dim = _read_stored_dim()
    vector_count = _read_vector_count() if exists else 0

    return {
        "exists": exists,
        "path": str(_index_dir()),
        "vector_count": vector_count,
        "stored_embedding_model": meta.get("embedding_model") if meta else None,
        "stored_embedding_provider": meta.get("embedding_provider") if meta else None,
        "stored_embedding_version": meta.get("embedding_version") if meta else None,
        "stored_dim": stored_dim,
        "updated_at": meta.get("updated_at") if meta else None,
    }


def _load_or_create_index() -> VectorStoreIndex:
    global _index
    if _index is not None:
        return _index

    embed_model = _get_embed_model()
    index_dir = _index_dir()

    if _faiss_store_exists():
        stored_dim = _read_stored_dim()
        if stored_dim and stored_dim != settings.embedding_dim:
            raise ValueError(
                f"FAISS index dimension ({stored_dim}) does not match EMBEDDING_DIM ({settings.embedding_dim}). Reindex required."
            )
        vector_store = FaissVectorStore.from_persist_dir(str(index_dir))
        storage_context = StorageContext.from_defaults(
            vector_store=vector_store,
            persist_dir=str(index_dir),
        )
        # FAISS stores vectors only. The text nodes and index metadata live in
        # docstore.json/index_store.json, so restore the complete persisted
        # index instead of rebuilding from the vector store alone.
        _index = load_index_from_storage(
            storage_context,
            embed_model=embed_model,
        )
        logger.info("Loaded FAISS index from %s", index_dir)
    else:
        faiss_index = faiss.IndexFlatL2(settings.embedding_dim)
        vector_store = FaissVectorStore(faiss_index=faiss_index)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        _index = VectorStoreIndex([], storage_context=storage_context, embed_model=embed_model)
        logger.info("Created new FAISS index at %s", index_dir)

    return _index


def add_documents(documents: list[Document]) -> int:
    if not documents:
        return 0

    if _uses_cloud_embedding():
        require_online_api("document embedding")
    index = _load_or_create_index()
    for doc in documents:
        index.insert(doc)

    index.storage_context.persist(persist_dir=str(_index_dir()))
    vector_count = _read_vector_count()
    _write_index_meta(vector_count)
    logger.info("Indexed %d chunks into FAISS", len(documents))
    return len(documents)


def get_index() -> VectorStoreIndex:
    return _load_or_create_index()
