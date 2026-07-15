from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2 import OperationalError
from psycopg2.extras import Json, RealDictCursor, execute_values

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
        "create extension if not exists pgcrypto",
        "alter table llm_logs add column if not exists prompt_tokens integer default 0",
        "alter table llm_logs add column if not exists completion_tokens integer default 0",
        """
        create table if not exists model_configs (
            id uuid primary key default gen_random_uuid(),
            model_key text not null unique,
            display_name text not null,
            model_type text not null check (model_type in ('chat', 'embedding', 'vision')),
            provider text not null,
            model_name text not null,
            endpoint text,
            dimension integer check (dimension is null or dimension > 0),
            enabled boolean not null default true,
            is_active boolean not null default false,
            notes text not null default '',
            runtime_config jsonb not null default '{}'::jsonb,
            created_at timestamptz not null default now(),
            updated_at timestamptz not null default now()
        )
        """,
        "create index if not exists idx_model_configs_type on model_configs(model_type)",
        "alter table model_configs add column if not exists is_active boolean not null default false",
        "alter table model_configs add column if not exists runtime_config jsonb not null default '{}'::jsonb",
        """
        create unique index if not exists idx_model_configs_one_active_per_type
        on model_configs(model_type) where is_active
        """,
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


def list_all_documents() -> List[Dict[str, Any]]:
    conn = _get_connection()
    if conn is None:
        return []

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, content, source, created_at
                FROM documents
                ORDER BY created_at ASC
                """
            )
            rows = cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def delete_chunks_for_document(*, document_id: str) -> None:
    conn = _get_connection()
    if conn is None:
        return

    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chunks WHERE document_id = %s", (document_id,))
        conn.commit()
    finally:
        conn.close()


def get_chunk_version_stats() -> Dict[str, Any]:
    conn = _get_connection()
    if conn is None:
        return {"total": 0, "versions": {}}

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*)::int AS total FROM chunks")
            total_row = cur.fetchone() or {"total": 0}

            cur.execute(
                """
                SELECT embedding_version, COUNT(*)::int AS count
                FROM chunks
                GROUP BY embedding_version
                ORDER BY count DESC
                """
            )
            version_rows = cur.fetchall()

        versions = {row["embedding_version"]: row["count"] for row in version_rows}
        return {"total": total_row["total"], "versions": versions}
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


def list_model_configs() -> List[Dict[str, Any]]:
    conn = _get_connection()
    if conn is None:
        raise RuntimeError("Database unavailable")

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, model_key, display_name, model_type, provider, model_name,
                       endpoint, dimension, enabled, is_active, notes, runtime_config, created_at, updated_at
                FROM model_configs
                ORDER BY model_type, display_name
                """
            )
            rows = cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def create_model_config(**values: Any) -> Dict[str, Any]:
    conn = _get_connection()
    if conn is None:
        raise RuntimeError("Database unavailable")

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO model_configs
                    (model_key, display_name, model_type, provider, model_name,
                     endpoint, dimension, enabled, notes, runtime_config)
                VALUES
                     (%(model_key)s, %(display_name)s, %(model_type)s, %(provider)s,
                     %(model_name)s, %(endpoint)s, %(dimension)s, %(enabled)s, %(notes)s, %(runtime_config)s)
                RETURNING id, model_key, display_name, model_type, provider, model_name,
                          endpoint, dimension, enabled, is_active, notes, runtime_config, created_at, updated_at
                """,
                {**values, "runtime_config": Json(values.get("runtime_config") or {})},
            )
            row = cur.fetchone()
        conn.commit()
        return dict(row)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def update_model_config(*, model_id: str, **values: Any) -> Optional[Dict[str, Any]]:
    conn = _get_connection()
    if conn is None:
        raise RuntimeError("Database unavailable")

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT is_active FROM model_configs WHERE id = %s FOR UPDATE",
                (model_id,),
            )
            existing = cur.fetchone()
            if existing and existing["is_active"] and not values["enabled"]:
                raise ValueError("Active model cannot be disabled")
            cur.execute(
                """
                UPDATE model_configs
                SET model_key = %(model_key)s,
                    display_name = %(display_name)s,
                    model_type = %(model_type)s,
                    provider = %(provider)s,
                    model_name = %(model_name)s,
                    endpoint = %(endpoint)s,
                    dimension = %(dimension)s,
                    enabled = %(enabled)s,
                    notes = %(notes)s,
                    runtime_config = %(runtime_config)s,
                    updated_at = now()
                WHERE id = %(model_id)s
                RETURNING id, model_key, display_name, model_type, provider, model_name,
                          endpoint, dimension, enabled, is_active, notes, runtime_config, created_at, updated_at
                """,
                {**values, "runtime_config": Json(values.get("runtime_config") or {}), "model_id": model_id},
            )
            row = cur.fetchone()
        conn.commit()
        return dict(row) if row else None
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_model_config(*, model_id: str) -> bool:
    conn = _get_connection()
    if conn is None:
        raise RuntimeError("Database unavailable")

    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM model_configs WHERE id = %s AND is_active = false",
                (model_id,),
            )
            deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_active_model_config(model_type: str) -> Optional[Dict[str, Any]]:
    conn = _get_connection()
    if conn is None:
        return None

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, model_key, display_name, model_type, provider, model_name,
                       endpoint, dimension, enabled, is_active, notes, runtime_config, created_at, updated_at
                FROM model_configs
                WHERE model_type = %s AND is_active = true
                """,
                (model_type,),
            )
            row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_model_config(model_id: str) -> Optional[Dict[str, Any]]:
    conn = _get_connection()
    if conn is None:
        raise RuntimeError("Database unavailable")

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, model_key, display_name, model_type, provider, model_name,
                       endpoint, dimension, enabled, is_active, notes, runtime_config, created_at, updated_at
                FROM model_configs
                WHERE id = %s
                """,
                (model_id,),
            )
            row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def activate_model_config(*, model_id: str) -> Optional[Dict[str, Any]]:
    conn = _get_connection()
    if conn is None:
        raise RuntimeError("Database unavailable")

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, model_type, enabled
                FROM model_configs
                WHERE id = %s
                FOR UPDATE
                """,
                (model_id,),
            )
            candidate = cur.fetchone()
            if candidate is None:
                conn.rollback()
                return None
            if not candidate["enabled"]:
                raise ValueError("Disabled model cannot be activated")

            cur.execute(
                "UPDATE model_configs SET is_active = false WHERE model_type = %s",
                (candidate["model_type"],),
            )
            cur.execute(
                """
                UPDATE model_configs
                SET is_active = true, updated_at = now()
                WHERE id = %s
                RETURNING id, model_key, display_name, model_type, provider, model_name,
                          endpoint, dimension, enabled, is_active, notes, runtime_config, created_at, updated_at
                """,
                (model_id,),
            )
            row = cur.fetchone()
        conn.commit()
        return dict(row) if row else None
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
