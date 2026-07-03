from typing import Any, Dict, List, Optional

from app.core.config import settings

_client = None


def get_supabase_client():
    """懒加载 Supabase 客户端。未配置 SUPABASE_URL/KEY 时返回 None。"""
    global _client
    if not settings.supabase_enabled:
        return None
    if _client is None:
        from supabase import create_client

        _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client


def log_chat(
    *,
    user_id: Optional[str],
    input_text: str,
    output_text: str,
    model: str,
    tokens: Dict[str, int],
    latency_ms: int,
) -> Optional[Dict[str, Any]]:
    """写入 llm_logs 表。TODO: Phase 3 实现。"""
    raise NotImplementedError("Phase 3: 在 supabase.log_chat 中 insert llm_logs")


def save_document(*, content: str, source: str) -> Optional[Dict[str, Any]]:
    """写入 documents 表。TODO: Phase 2/3 实现。"""
    raise NotImplementedError("Phase 3: 在 supabase.save_document 中 insert documents")


def save_chunks(
    *,
    document_id: str,
    chunks: List[str],
    embedding_version: str,
) -> Optional[List[Dict[str, Any]]]:
    """写入 chunks 表。TODO: Phase 2/3 实现。"""
    raise NotImplementedError("Phase 3: 在 supabase.save_chunks 中 insert chunks")
