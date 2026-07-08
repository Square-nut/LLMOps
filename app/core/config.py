from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 运行环境标识；可选值：development / test / production，自定义字符串也可。
    app_env: str = "development"
    # 日志级别；可选值：DEBUG / INFO / WARNING / ERROR / CRITICAL。
    log_level: str = "INFO"

    # OpenAI 官方 API Key；当前主链路不用，保留给未来直连 OpenAI。
    openai_api_key: str = ""
    # Anthropic API Key；当前主链路不用，保留给未来模型 fallback。
    anthropic_api_key: str = ""

    # GeekAI 中转站 API Key；调用 chat completion / openai embedding 时必填。
    geekai_api_key: str = ""
    # GeekAI OpenAI-compatible base URL；一般不用改，除非换中转服务。
    geekai_base_url: str = "https://geekai.co/api/v1"
    # 是否允许调用在线 API；可选值：true / false，false 时禁止 chat / 云端 embedding。
    allow_online_api: bool = False

    # PostgreSQL 连接串；为空表示禁用数据库落库，例如 postgresql://user:pass@host:5432/db。
    database_url: str = ""

    # FAISS 索引持久化目录；建议放在项目 data 目录或外置盘。
    faiss_index_path: str = "./data/faiss_index"
    # Embedding 来源；可选值：mock / openai / local。local 目前预留未实现。
    embedding_provider: str = "openai"
    # Embedding 模型名；openai 模式常用 text-embedding-3-small。
    embedding_model: str = "text-embedding-3-small"
    # Embedding 版本标识；为空时使用 embedding_model，用于判断索引是否需要重建。
    embedding_version: str = ""
    # Embedding 向量维度；text-embedding-3-small 默认 1536，换模型需同步调整并重建索引。
    embedding_dim: int = 1536
    # 本地 embedding 设备；可选值：cuda / cpu / mps，当前 local 模式预留。
    embedding_device: str = "cuda"
    # 是否启用固定 mock RAG；可选值：true / false，仅 embedding_provider=mock 时生效。
    mock_rag_enabled: bool = True
    # 固定 mock RAG 的触发问题；完全匹配后直接返回 mock_rag_context。
    mock_rag_query: str = "年假几天？"
    # 固定 mock RAG 返回片段的 source 标识。
    mock_rag_source: str = "mock-hr"
    # 固定 mock RAG 返回的上下文内容；用于不调用 embedding 时验收 RAG 流程。
    mock_rag_context: str = "公司年假是15天。"

    # 文档切块大小；数值越大单个 chunk 越长，常见范围 256-1024。
    chunk_size: int = 512
    # 文档切块重叠长度；常见范围 32-128，需小于 chunk_size。
    chunk_overlap: int = 64
    # RAG 检索返回的 chunk 数量；常见范围 3-8。
    retrieval_top_k: int = 4

    # 默认对话模型；用于普通问题。
    default_model: str = "deepseek-v4-flash"
    # 推理任务模型；task_type=reasoning 时使用。
    reasoning_model: str = "bytedance-asset-v1"
    # 长上下文任务模型；task_type=long_context 或上下文很长时使用。
    long_context_model: str = "bytedance-asset-v1"
    # 兜底模型；默认模型调用失败后重试使用。
    fallback_model: str = "bytedance-asset-v1"

    @property
    def database_enabled(self) -> bool:
        return bool(self.database_url)

    @property
    def effective_embedding_version(self) -> str:
        return self.embedding_version or self.embedding_model


settings = Settings()
