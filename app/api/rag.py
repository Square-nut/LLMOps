from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.online_api import OnlineApiDisabledError, require_online_api
from app.services import rag_service

router = APIRouter()


class EmbeddingStatus(BaseModel):
    provider: str
    model: str
    version: str
    dim: int
    device: str
    ready: bool


class IndexStatus(BaseModel):
    exists: bool
    path: str
    vector_count: int
    stored_embedding_model: Optional[str] = None
    stored_embedding_provider: Optional[str] = None
    stored_embedding_version: Optional[str] = None
    stored_dim: Optional[int] = None
    updated_at: Optional[str] = None


class DatabaseRagStatus(BaseModel):
    enabled: bool
    document_count: int
    chunk_count: int
    chunk_versions: Dict[str, int]


class RagStatusResponse(BaseModel):
    status: str
    warnings: List[str]
    chat_model: str
    embedding: EmbeddingStatus
    index: IndexStatus
    database: DatabaseRagStatus


class ReindexResponse(BaseModel):
    documents_processed: int
    chunks_indexed: int
    vector_count: int
    embedding_version: str


@router.get("/rag/status", response_model=RagStatusResponse)
async def get_rag_status():
    return RagStatusResponse(**rag_service.get_rag_status())


@router.post("/rag/reindex", response_model=ReindexResponse)
async def reindex_rag():
    try:
        result = rag_service.reindex_all()
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OnlineApiDisabledError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return ReindexResponse(**result)
