"""Apply the persisted active model selection to the in-process runtime."""

import os

from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.logger import logger
from app.db import postgres as db

_DEFAULT_CHAT_API_BASE = settings.geekai_base_url
_DEFAULT_GEEKAI_API_KEY = settings.geekai_api_key
_DEFAULT_OPENAI_API_KEY = settings.openai_api_key
_DEFAULT_EMBEDDING_API_BASE = settings.embedding_api_base
_DEFAULT_EMBEDDING_API_KEY = settings.embedding_api_key
_OPENAI_API_BASE = "https://api.openai.com/v1"
_active_chat_runtime_config: Dict[str, Any] = {}
_active_chat_from_catalog = False

CHAT_PROVIDERS = {"geekai", "openai", "xinference", "ollama"}
EMBEDDING_PROVIDERS = {"xinference", "tei", "ollama", "geekai", "openai", "mock"}


def _credential(model: Dict[str, Any], fallback: Optional[str]) -> Optional[str]:
    reference = str(model.get("credential_ref") or "").strip()
    return os.getenv(reference) if reference else fallback


def active_chat_completion_options() -> Dict[str, Any]:
    """Return only supported, non-sensitive Chat completion options."""
    allowed = {"temperature", "top_p", "max_tokens", "presence_penalty", "frequency_penalty"}
    return {
        key: value
        for key, value in _active_chat_runtime_config.items()
        if key in allowed and value is not None
    }


def active_chat_uses_catalog() -> bool:
    return _active_chat_from_catalog


def active_chat_is_online() -> bool:
    """A locally deployed OpenAI-compatible runtime must not depend on ALLOW_ONLINE_API."""
    return not _active_chat_from_catalog or _active_chat_runtime_config.get("source") != "local"


def validate_catalog_model(model: Dict[str, Any]) -> None:
    model_type = model["model_type"]
    provider = model["provider"].strip().lower()

    if model_type == "chat" and provider not in CHAT_PROVIDERS:
        raise ValueError("Chat runtime must be geekai, openai, xinference, or ollama")
    if model_type == "embedding" and provider not in EMBEDDING_PROVIDERS:
        raise ValueError("Embedding runtime must be xinference, tei, ollama, geekai, openai, or mock")


def validate_activatable_model(model: Dict[str, Any]) -> None:
    model_type = model["model_type"]
    provider = model["provider"].strip().lower()

    validate_catalog_model(model)
    if model_type == "vision":
        raise ValueError("Vision model switching is not supported yet")
    if model_type == "chat" and provider in {"xinference", "ollama"} and not model.get("endpoint"):
        raise ValueError("Xinference / Ollama chat model requires a service endpoint")
    if model_type == "embedding":
        if provider in {"xinference", "tei", "ollama"} and not model.get("endpoint"):
            raise ValueError("Xinference / TEI / Ollama embedding requires a service endpoint")


def apply_model(model: Dict[str, Any]) -> None:
    """Apply one active catalogue record without writing secrets to the database."""
    validate_activatable_model(model)
    model_type = model["model_type"]
    provider = model["provider"].strip().lower()

    if model_type == "chat":
        global _active_chat_runtime_config, _active_chat_from_catalog
        settings.default_model = model["model_name"]
        if provider == "geekai":
            settings.geekai_base_url = model["endpoint"].rstrip("/") if model.get("endpoint") else _DEFAULT_CHAT_API_BASE
            settings.geekai_api_key = _credential(model, _DEFAULT_GEEKAI_API_KEY)
        elif provider == "openai":
            settings.geekai_base_url = model["endpoint"].rstrip("/") if model.get("endpoint") else _OPENAI_API_BASE
            settings.geekai_api_key = _credential(model, _DEFAULT_OPENAI_API_KEY)
        else:
            settings.geekai_base_url = model["endpoint"].rstrip("/")
            settings.geekai_api_key = _DEFAULT_EMBEDDING_API_KEY or provider
        _active_chat_runtime_config = {
            **(model.get("runtime_config") or {}),
            "source": model.get("source") or "gateway",
        }
        _active_chat_from_catalog = True
        from app.core.llm_gateway import reset_client

        reset_client()
        return

    if model_type == "embedding":
        settings.embedding_model = model["model_name"]
        settings.embedding_version = f"catalog:{model['model_key']}"
        if model.get("dimension"):
            settings.embedding_dim = model["dimension"]

        if provider in {"xinference", "tei", "ollama"}:
            settings.embedding_provider = "local"
            settings.embedding_backend = "tei"
            settings.embedding_api_base = model["endpoint"].rstrip("/")
            settings.embedding_api_key = _credential(model, _DEFAULT_EMBEDDING_API_KEY) or provider
        elif provider == "geekai":
            settings.embedding_provider = "openai"
            settings.embedding_api_base = (
                model["endpoint"].rstrip("/")
                if model.get("endpoint")
                else (_DEFAULT_EMBEDDING_API_BASE or _DEFAULT_CHAT_API_BASE)
            )
            settings.embedding_api_key = _credential(model, _DEFAULT_GEEKAI_API_KEY)
        elif provider == "openai":
            settings.embedding_provider = "openai"
            settings.embedding_api_base = (
                model["endpoint"].rstrip("/") if model.get("endpoint") else _OPENAI_API_BASE
            )
            settings.embedding_api_key = _credential(model, _DEFAULT_OPENAI_API_KEY)
        else:
            settings.embedding_provider = "mock"

        from app.rag.index import reset_index_cache
        from app.rag.local_embedding import reset_local_embed_cache

        reset_local_embed_cache()
        reset_index_cache()


def apply_persisted_active_models() -> None:
    """Use the catalogue on process start; .env remains the fallback when empty."""
    if not settings.database_enabled:
        return

    for model_type in ("chat", "embedding"):
        model: Optional[Dict[str, Any]] = db.get_active_model_config(model_type)
        if model is None:
            continue
        try:
            apply_model(model)
            logger.info("Applied active %s model from catalogue: %s", model_type, model["model_key"])
        except ValueError as exc:
            logger.error("Cannot apply active %s model %s: %s", model_type, model["model_key"], exc)
