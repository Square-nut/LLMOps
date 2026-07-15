from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field
from psycopg2 import IntegrityError

from app.core.config import settings
from app.db import postgres as db

router = APIRouter()


class ModelConfigInput(BaseModel):
    model_key: str = Field(..., min_length=1, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    display_name: str = Field(..., min_length=1, max_length=120)
    model_type: str = Field(..., pattern=r"^(chat|embedding|vision)$")
    provider: str = Field(..., min_length=1, max_length=80)
    model_name: str = Field(..., min_length=1, max_length=200)
    endpoint: Optional[str] = Field(default=None, max_length=500)
    dimension: Optional[int] = Field(default=None, gt=0)
    enabled: bool = True
    notes: str = Field(default="", max_length=2000)

    def db_values(self) -> dict:
        return {
            **self.model_dump(),
            "endpoint": self.endpoint.strip() if self.endpoint and self.endpoint.strip() else None,
            "notes": self.notes.strip(),
        }


class ModelConfigResponse(ModelConfigInput):
    id: UUID
    created_at: datetime
    updated_at: datetime


def _require_database() -> None:
    if not settings.database_enabled:
        raise HTTPException(status_code=503, detail="Database not configured")


def _database_error(exc: Exception) -> HTTPException:
    if isinstance(exc, IntegrityError):
        return HTTPException(status_code=409, detail="模型标识已存在，请使用其他标识")
    return HTTPException(status_code=503, detail="Database unavailable")


@router.get("/models", response_model=List[ModelConfigResponse])
async def list_models():
    _require_database()
    try:
        rows = db.list_model_configs()
    except Exception as exc:
        raise _database_error(exc) from exc
    return [ModelConfigResponse(**row) for row in rows]


@router.post("/models", response_model=ModelConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_model(body: ModelConfigInput):
    _require_database()
    try:
        return ModelConfigResponse(**db.create_model_config(**body.db_values()))
    except Exception as exc:
        raise _database_error(exc) from exc


@router.put("/models/{model_id}", response_model=ModelConfigResponse)
async def update_model(model_id: UUID, body: ModelConfigInput):
    _require_database()
    try:
        row = db.update_model_config(model_id=str(model_id), **body.db_values())
    except Exception as exc:
        raise _database_error(exc) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="模型不存在")
    return ModelConfigResponse(**row)


@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(model_id: UUID) -> Response:
    _require_database()
    try:
        deleted = db.delete_model_config(model_id=str(model_id))
    except Exception as exc:
        raise _database_error(exc) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="模型不存在")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
