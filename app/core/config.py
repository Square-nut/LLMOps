from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"

    openai_api_key: str = ""
    anthropic_api_key: str = ""

    geekai_api_key: str = ""
    geekai_base_url: str = "https://geekai.co/api/v1"

    database_url: str = ""

    faiss_index_path: str = "./data/faiss_index"
    embedding_model: str = "text-embedding-3-small"
    embedding_version: str = "v1"

    chunk_size: int = 512
    chunk_overlap: int = 64
    retrieval_top_k: int = 4

    default_model: str = "deepseek-v4-flash"
    reasoning_model: str = "bytedance-asset-v1"
    long_context_model: str = "bytedance-asset-v1"
    fallback_model: str = "bytedance-asset-v1"

    @property
    def database_enabled(self) -> bool:
        return bool(self.database_url)


settings = Settings()
