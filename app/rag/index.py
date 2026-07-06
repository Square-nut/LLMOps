from pathlib import Path
from typing import Optional

import faiss
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.faiss import FaissVectorStore

from app.core.config import settings
from app.core.logger import logger

_index: Optional[VectorStoreIndex] = None
EMBEDDING_DIM = 1536


def _get_embed_model() -> OpenAIEmbedding:
    return OpenAIEmbedding(
        model=settings.embedding_model,
        api_key=settings.geekai_api_key,
        api_base=settings.geekai_base_url,
    )


def _index_dir() -> Path:
    path = Path(settings.faiss_index_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_or_create_index() -> VectorStoreIndex:
    global _index
    if _index is not None:
        return _index

    embed_model = _get_embed_model()
    index_dir = _index_dir()
    faiss_path = index_dir / "default__vector_store.json"

    if faiss_path.exists():
        vector_store = FaissVectorStore.from_persist_dir(str(index_dir))
        storage_context = StorageContext.from_defaults(
            vector_store=vector_store,
            persist_dir=str(index_dir),
        )
        _index = VectorStoreIndex.from_vector_store(
            vector_store,
            storage_context=storage_context,
            embed_model=embed_model,
        )
        logger.info("Loaded FAISS index from %s", index_dir)
    else:
        faiss_index = faiss.IndexFlatL2(EMBEDDING_DIM)
        vector_store = FaissVectorStore(faiss_index=faiss_index)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        _index = VectorStoreIndex([], storage_context=storage_context, embed_model=embed_model)
        logger.info("Created new FAISS index at %s", index_dir)

    return _index


def add_documents(documents: list[Document]) -> int:
    if not documents:
        return 0

    index = _load_or_create_index()
    for doc in documents:
        index.insert(doc)

    index.storage_context.persist(persist_dir=str(_index_dir()))
    logger.info("Indexed %d chunks into FAISS", len(documents))
    return len(documents)


def get_index() -> VectorStoreIndex:
    return _load_or_create_index()
