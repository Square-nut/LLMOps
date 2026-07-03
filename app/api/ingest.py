from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.services import ingest_service

router = APIRouter()


class IngestTextRequest(BaseModel):
    content: str = Field(..., min_length=1)
    source: str = "upload"


class IngestResponse(BaseModel):
    document_id: Optional[str]
    source: str
    chunks_indexed: int
    embedding_version: str


@router.post("/ingest/text", response_model=IngestResponse)
async def ingest_text(body: IngestTextRequest) -> IngestResponse:
    try:
        result = await ingest_service.ingest_text(body.content, source=body.source)
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    return IngestResponse(**result)


@router.post("/ingest/file", response_model=IngestResponse)
async def ingest_file(
    file: UploadFile = File(...),
    source: str = Form(default="upload"),
) -> IngestResponse:
    raw = await file.read()
    content = raw.decode("utf-8")
    file_source = source or file.filename or "upload"
    try:
        result = await ingest_service.ingest_text(content, source=file_source)
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    return IngestResponse(**result)
