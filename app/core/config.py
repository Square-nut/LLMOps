from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App 基础配置 -------------------------------------------------
    # 运行环境：development / test / production（也可用自定义字符串）
    app_env: str = "development"
    # 日志级别：DEBUG / INFO / WARNING / ERROR / CRITICAL
    log_level: str = "INFO"

    # --- 模型供应商密钥 -----------------------------------------------
    # OpenAI 官方 Key：当前主链路未使用，预留给未来直连 OpenAI
    openai_api_key: str = ""
    # Anthropic Key：当前主链路未使用，预留给未来模型 fallback
    anthropic_api_key: str = ""

    # GeekAI Key：调用 chat completion / openai embedding 时必填
    geekai_api_key: str = ""
    # GeekAI Base URL：OpenAI-compatible 地址，换中转服务时修改
    geekai_base_url: str = "https://geekai.co/api/v1"
    # 在线 API 开关：true / false；false 时禁止 chat 和云端 embedding
    allow_online_api: bool = True

    # --- 数据库 -------------------------------------------------------
    # PostgreSQL 连接串：为空则禁用落库；示例 postgresql://user:pass@host:5432/db
    database_url: str = ""

    # --- RAG / Embedding ---------------------------------------------
    # FAISS 索引目录：建议放在项目 data 目录或外置盘
    faiss_index_path: str = "./data/faiss_index"
    # Embedding 来源：mock / openai / local；local 目前预留未实现
    embedding_provider: str = "openai"
    # Embedding 模型：openai 模式常用 text-embedding-3-small
    embedding_model: str = "text-embedding-3-small"
    # Embedding 版本：为空时使用 embedding_model；用于判断是否需要重建索引
    embedding_version: str = ""
    # 向量维度：text-embedding-3-small 默认 1536；换模型后需同步调整
    embedding_dim: int = 1536
    # 本地设备：cuda / cpu / mps；仅 local 模式使用，当前预留
    embedding_device: str = "cuda"

    # --- Mock RAG 固定夹具 -------------------------------------------
    # 是否启用：true / false；仅 embedding_provider=mock 时生效
    mock_rag_enabled: bool = True
    # 触发问题：完全匹配后直接返回 mock_rag_context
    mock_rag_query: str = "年假几天？"
    # 返回来源：展示在检索片段 source 字段中
    mock_rag_source: str = "mock-hr"
    # 返回上下文：用于不调用 embedding 时验收 RAG 流程
    mock_rag_context: str = "公司年假是15天。"
    # 是否启用 mock chat：true / false；用于不调用 LLM 时验收 /api/chat
    mock_chat_enabled: bool = True
    # mock chat 固定回复：仅在 embedding_provider=mock 且问题匹配时返回
    mock_chat_reply: str = "根据 mock 知识库，公司年假是15天。"

    # --- 检索参数 -----------------------------------------------------
    # 切块大小：常见范围 256-1024，越大单个 chunk 越长
    chunk_size: int = 512
    # 切块重叠：常见范围 32-128，需小于 chunk_size
    chunk_overlap: int = 64
    # 检索数量：返回 top-k 个 chunk，常见范围 3-8
    retrieval_top_k: int = 4

    # --- Chat 模型路由 -----------------------------------------------
    # 默认模型：普通问题使用
    default_model: str = "deepseek-v4-flash"
    # 推理模型：task_type=reasoning 时使用
    reasoning_model: str = "bytedance-asset-v1"
    # 长上下文模型：task_type=long_context 或上下文很长时使用
    long_context_model: str = "bytedance-asset-v1"
    # 兜底模型：默认模型调用失败后重试使用
    fallback_model: str = "bytedance-asset-v1"

    @property
    def database_enabled(self) -> bool:
        return bool(self.database_url)

    @property
    def effective_embedding_version(self) -> str:
        return self.embedding_version or self.embedding_model


settings = Settings()
