from typing import Any, Dict, Optional

from llama_index.core.embeddings import BaseEmbedding

from app.core.config import settings

_embed_model: Optional[BaseEmbedding] = None


def reset_local_embed_cache() -> None:
    global _embed_model
    _embed_model = None


def validate_local_embedding_config() -> None:
    backend = settings.embedding_backend
    if backend not in ("huggingface", "tei"):
        raise ValueError(
            f"Unknown EMBEDDING_BACKEND={backend!r}. Use huggingface or tei."
        )
    if backend == "tei" and not settings.embedding_api_base.strip():
        raise ValueError(
            "EMBEDDING_API_BASE is required when EMBEDDING_BACKEND=tei "
            "(Win PC TEI / OpenAI-compatible embedding service)."
        )
    if not settings.embedding_model.strip():
        raise ValueError("EMBEDDING_MODEL is required for local embedding.")


def get_local_embed_model() -> BaseEmbedding:
    global _embed_model
    if _embed_model is not None:
        return _embed_model

    validate_local_embedding_config()
    backend = settings.embedding_backend

    if backend == "tei":
        from llama_index.embeddings.openai import OpenAIEmbedding

        _embed_model = OpenAIEmbedding(
            model=settings.embedding_model,
            api_key=settings.embedding_api_key or "tei",
            api_base=settings.embedding_api_base.rstrip("/"),
        )
        return _embed_model

    try:
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    except ImportError as exc:
        raise ImportError(
            "In-process HuggingFace embedding requires: "
            "pip install llama-index-embeddings-huggingface sentence-transformers"
        ) from exc

    _embed_model = HuggingFaceEmbedding(
        model_name=settings.embedding_model,
        device=settings.embedding_device,
    )
    return _embed_model


def local_embedding_config_ready() -> bool:
    if settings.embedding_provider != "local":
        return False
    try:
        validate_local_embedding_config()
    except ValueError:
        return False
    return True


def probe_local_embedding() -> Dict[str, Any]:
    validate_local_embedding_config()
    embed_model = get_local_embed_model()
    sample = "embedding health check"
    vector = embed_model._get_text_embedding(sample)
    dim = len(vector)
    if dim != settings.embedding_dim:
        raise ValueError(
            f"Embedding service returned dim={dim}, "
            f"but EMBEDDING_DIM={settings.embedding_dim}. Update .env and reindex."
        )
    return {
        "ok": True,
        "backend": settings.embedding_backend,
        "model": settings.embedding_model,
        "dim": dim,
        "device": _device_label(),
        "api_base": settings.embedding_api_base or None,
        "sample": sample,
    }


def _device_label() -> str:
    if settings.embedding_backend == "tei":
        return "remote"
    return settings.embedding_device
