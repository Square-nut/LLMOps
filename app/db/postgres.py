from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values

from app.core.config import settings
from app.core.logger import logger


def _get_connection():
    if not settings.database_enabled:
        return None
    return psycopg2.connect(settings.database_url, cursor_factory=RealDictCursor)


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
                INSERT INTO llm_logs (user_id, input, output, model, tokens, latency)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (user_id, input_text, output_text, model, tokens.get("total", 0), latency_ms),
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
