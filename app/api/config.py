from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()


class AppConfig(BaseModel):
    app_env: str
    log_level: str
    allow_online_api: bool


class SecretState(BaseModel):
    configured: bool


class ProviderConfig(BaseModel):
    geekai_base_url: str
    geekai_api_key: SecretState
    openai_api_key: SecretState
    anthropic_api_key: SecretState


class DatabaseConfig(BaseModel):
    enabled: bool
    database_url: SecretState


class EmbeddingConfig(BaseModel):
    provider: str
    backend: str
    model: str
    version: str
    dim: int
    device: str
    api_base: Optional[str] = None
    api_key: SecretState


class RagConfig(BaseModel):
    faiss_index_path: str
    chunk_size: int
    chunk_overlap: int
    retrieval_top_k: int


class MockConfig(BaseModel):
    rag_enabled: bool
    rag_query: str
    rag_source: str
    chat_enabled: bool


class ModelRoutingConfig(BaseModel):
    default_model: str
    reasoning_model: str
    long_context_model: str
    fallback_model: str


class RuntimeConfigResponse(BaseModel):
    app: AppConfig
    providers: ProviderConfig
    database: DatabaseConfig
    embedding: EmbeddingConfig
    rag: RagConfig
    mock: MockConfig
    routing: ModelRoutingConfig
    notes: list[str]


def _secret_state(value: str) -> SecretState:
    return SecretState(configured=bool(value.strip()))


@router.get("/config", response_model=RuntimeConfigResponse)
async def get_runtime_config():
    notes = [
        "当前接口只读，不会修改 .env。",
        "密钥和数据库连接串只返回是否已配置。",
        "修改 .env 后需要重启 API 才会生效。",
    ]

    return RuntimeConfigResponse(
        app=AppConfig(
            app_env=settings.app_env,
            log_level=settings.log_level,
            allow_online_api=settings.allow_online_api,
        ),
        providers=ProviderConfig(
            geekai_base_url=settings.geekai_base_url,
            geekai_api_key=_secret_state(settings.geekai_api_key),
            openai_api_key=_secret_state(settings.openai_api_key),
            anthropic_api_key=_secret_state(settings.anthropic_api_key),
        ),
        database=DatabaseConfig(
            enabled=settings.database_enabled,
            database_url=_secret_state(settings.database_url),
        ),
        embedding=EmbeddingConfig(
            provider=settings.embedding_provider,
            backend=settings.embedding_backend,
            model=settings.embedding_model,
            version=settings.effective_embedding_version,
            dim=settings.embedding_dim,
            device=settings.embedding_device,
            api_base=settings.embedding_api_base or None,
            api_key=_secret_state(settings.embedding_api_key),
        ),
        rag=RagConfig(
            faiss_index_path=settings.faiss_index_path,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            retrieval_top_k=settings.retrieval_top_k,
        ),
        mock=MockConfig(
            rag_enabled=settings.mock_rag_enabled,
            rag_query=settings.mock_rag_query,
            rag_source=settings.mock_rag_source,
            chat_enabled=settings.mock_chat_enabled,
        ),
        routing=ModelRoutingConfig(
            default_model=settings.default_model,
            reasoning_model=settings.reasoning_model,
            long_context_model=settings.long_context_model,
            fallback_model=settings.fallback_model,
        ),
        notes=notes,
    )
