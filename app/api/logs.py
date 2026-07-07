from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.config import settings
from app.db import postgres as db

router = APIRouter()


class ChatLogItem(BaseModel):
    id: UUID
    user_id: Optional[str] = None
    input: str
    output: str
    model: str
    tokens: int
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency: int
    created_at: datetime


class IngestLogItem(BaseModel):
    id: UUID
    source: str
    content_length: int
    chunk_count: int
    embedding_version: Optional[str] = None
    created_at: datetime


class UsageSummary(BaseModel):
    chat_count: int
    total_tokens: int
    total_prompt_tokens: int
    total_completion_tokens: int
    document_count: int
    chunk_count: int


class LogsResponse(BaseModel):
    summary: UsageSummary
    chat_logs: List[ChatLogItem]
    ingest_logs: List[IngestLogItem]


@router.get("/logs", response_model=LogsResponse)
async def get_logs(limit: int = Query(default=50, ge=1, le=200)):
    if not settings.database_enabled:
        raise HTTPException(status_code=503, detail="Database not configured")

    summary = db.get_usage_summary()
    chat_logs = db.list_chat_logs(limit=limit)
    ingest_logs = db.list_ingest_logs(limit=limit)

    return LogsResponse(
        summary=UsageSummary(**summary),
        chat_logs=[ChatLogItem(**row) for row in chat_logs],
        ingest_logs=[IngestLogItem(**row) for row in ingest_logs],
    )
