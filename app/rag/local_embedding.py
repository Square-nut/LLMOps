import asyncio
import json
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from llama_index.core.embeddings import BaseEmbedding

from app.core.config import settings

_embed_model: Optional[BaseEmbedding] = None


class XinferenceEmbedding(BaseEmbedding):
    """Minimal OpenAI-compatible embedding client for Xinference.

    LlamaIndex's OpenAIEmbedding validates ``model`` against its own enum,
    which rejects Xinference model UIDs such as ``bge-base-zh-v1.5``. This
    adapter keeps the LlamaIndex BaseEmbedding contract while sending the
    request directly to Xinference's ``/embeddings`` endpoint.
    """

    api_base: str
    api_key: str = "xinference"
    timeout: float = 60.0

    def _embed(self, inputs: str | List[str]) -> List[List[float]]:
        payload = json.dumps({"model": self.model_name, "input": inputs}).encode(
            "utf-8"
        )
        request = Request(
            f"{self.api_base.rstrip('/')}/embeddings",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(
                f"Xinference embedding request failed at {self.api_base}: {exc}"
            ) from exc

        data = sorted(body.get("data", []), key=lambda item: item.get("index", 0))
        embeddings = [item["embedding"] for item in data]
        if not embeddings:
            raise RuntimeError(f"Xinference returned no embeddings: {body}")
        return embeddings

    def _get_query_embedding(self, query: str) -> List[float]:
        return self._embed(query)[0]

    async def _aget_query_embedding(self, query: str) -> List[float]:
        return await asyncio.to_thread(self._get_query_embedding, query)

    def _get_text_embedding(self, text: str) -> List[float]:
        return self._embed(text)[0]

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        return self._embed(texts)


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
        _embed_model = XinferenceEmbedding(
            model_name=settings.embedding_model,
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
