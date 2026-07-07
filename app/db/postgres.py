from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2 import OperationalError
from psycopg2.extras import RealDictCursor, execute_values

from app.core.config import settings
from app.core.logger import logger


def _get_connection():
    if not settings.database_enabled:
        return None
    try:
        return psycopg2.connect(settings.database_url, cursor_factory=RealDictCursor)
    except OperationalError as exc:
        logger.warning("Database unavailable, skipping DB write: %s", exc)
        return None


def ensure_schema() -> None:
    """Apply incremental schema changes for existing databases."""
    conn = _get_connection()
    if conn is None:
        return

    migrations = [
        "alter table llm_logs add column if not exists prompt_tokens integer default 0",
        "alter table llm_logs add column if not exists completion_tokens integer default 0",
    ]

    try:
        with conn.cursor() as cur:
            for sql in migrations:
                cur.execute(sql)
        conn.commit()
        logger.info("Database schema up to date")
    except Exception as exc:
        conn.rollback()
        logger.error("Failed to apply schema migrations: %s", exc)
        raise
    finally:
        conn.close()


def log_chat(
    *,
    user_id: Optional[str],
    input_text: str,
    output_text: str,
    model: str,
    tokens: Dict[str, int],
    latency_ms: int,
) -> Optional[Dict[str, Any]]:
    conn = _get_connection()
    if conn is None:
        logger.debug("Database disabled, skipping chat log")
        return None

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO llm_logs (user_id, input, output, model, tokens, prompt_tokens, completion_tokens, latency)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    user_id,
                    input_text,
                    output_text,
                    model,
                    tokens.get("total", 0),
                    tokens.get("prompt", 0),
                    tokens.get("completion", 0),
                    latency_ms,
                ),
            )
            row = cur.fetchone()
        conn.commit()
        return dict(row) if row else None
    except Exception as exc:
        conn.rollback()
        logger.error("Failed to log chat: %s", exc)
        raise
    finally:
        conn.close()


def save_document(*, content: str, source: str) -> Optional[Dict[str, Any]]:
    conn = _get_connection()
    if conn is None:
        logger.debug("Database disabled, skipping document save")
        return None

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents (content, source)
                VALUES (%s, %s)
                RETURNING *
                """,
                (content, source),
            )
            row = cur.fetchone()
        conn.commit()
        return dict(row) if row else None
    except Exception as exc:
        conn.rollback()
        logger.error("Failed to save document: %s", exc)
        raise
    finally:
        conn.close()


def save_chunks(
    *,
    document_id: str,
    chunks: List[str],
    embedding_version: str,
) -> Optional[List[Dict[str, Any]]]:
    if not chunks:
        return []

    conn = _get_connection()
    if conn is None:
        logger.debug("Database disabled, skipping chunk save")
        return None

    rows = [(document_id, chunk, embedding_version) for chunk in chunks]

    try:
        with conn.cursor() as cur:
            result = execute_values(
                cur,
                """
                INSERT INTO chunks (document_id, chunk_text, embedding_version)
                VALUES %s
                RETURNING *
                """,
                rows,
                fetch=True,
            )
        conn.commit()
        return [dict(row) for row in result] if result else []
    except Exception as exc:
        conn.rollback()
        logger.error("Failed to save chunks: %s", exc)
        raise
    finally:
        conn.close()


def list_chat_logs(*, limit: int = 50) -> List[Dict[str, Any]]:
    conn = _get_connection()
    if conn is None:
        return []

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, input, output, model, tokens,
                       prompt_tokens, completion_tokens, latency, created_at
                FROM llm_logs
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def list_ingest_logs(*, limit: int = 50) -> List[Dict[str, Any]]:
    conn = _get_connection()
    if conn is None:
        return []

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT d.id, d.source, d.created_at,
                       length(d.content) AS content_length,
                       COUNT(c.id) AS chunk_count,
                       MAX(c.embedding_version) AS embedding_version
                FROM documents d
                LEFT JOIN chunks c ON c.document_id = d.id
                GROUP BY d.id, d.source, d.created_at, d.content
                ORDER BY d.created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_usage_summary() -> Dict[str, Any]:
    conn = _get_connection()
    if conn is None:
        return {
            "chat_count": 0,
            "total_tokens": 0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "document_count": 0,
            "chunk_count": 0,
        }

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*)::int AS chat_count,
                    COALESCE(SUM(tokens), 0)::int AS total_tokens,
                    COALESCE(SUM(prompt_tokens), 0)::int AS total_prompt_tokens,
                    COALESCE(SUM(completion_tokens), 0)::int AS total_completion_tokens
                FROM llm_logs
                """
            )
            chat_stats = dict(cur.fetchone() or {})

            cur.execute("SELECT COUNT(*)::int AS document_count FROM documents")
            doc_stats = dict(cur.fetchone() or {})

            cur.execute("SELECT COUNT(*)::int AS chunk_count FROM chunks")
            chunk_stats = dict(cur.fetchone() or {})

        return {**chat_stats, **doc_stats, **chunk_stats}
    finally:
        conn.close()
