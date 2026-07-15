import json
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from psycopg2 import IntegrityError

from app.core.config import settings
from app.db import postgres as db
from app.services import model_runtime
from app.services import xinference_runtime

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
    runtime_config: dict = Field(default_factory=dict)

    def db_values(self) -> dict:
        return {
            **self.model_dump(),
            "endpoint": self.endpoint.strip() if self.endpoint and self.endpoint.strip() else None,
            "notes": self.notes.strip(),
            "runtime_config": self.runtime_config,
        }


class ModelConfigResponse(ModelConfigInput):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ModelActivationResponse(BaseModel):
    model: ModelConfigResponse
    requires_reindex: bool
    message: str


class XinferenceLaunchInput(BaseModel):
    endpoint: Optional[str] = None
    model_engine: Optional[str] = None
    model_format: Optional[str] = None
    quantization: Optional[str] = None
    size: Optional[str] = None
    download_hub: Optional[str] = "modelscope"
    gpu_idx: List[int] = Field(default_factory=lambda: [0])
    n_gpu: Optional[str] = "auto"
    enable_virtual_env: bool = False
    model_uid: Optional[str] = None


class XinferenceRuntimeResponse(BaseModel):
    models: List[dict]


class XinferenceCatalogResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    page_size: int


class XinferenceDeployResponse(BaseModel):
    model: ModelConfigResponse
    runtime: dict


def _require_database() -> None:
    if not settings.database_enabled:
        raise HTTPException(status_code=503, detail="Database not configured")


def _database_error(exc: Exception) -> HTTPException:
    if isinstance(exc, IntegrityError):
        return HTTPException(status_code=409, detail="模型标识已存在，请使用其他标识")
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=503, detail="Database unavailable")


def _runtime_error(exc: Exception) -> HTTPException:
    if isinstance(exc, xinference_runtime.XinferenceRuntimeError):
        return HTTPException(status_code=502, detail=str(exc))
    return _database_error(exc)


def _default_runtime_endpoint() -> str:
    return settings.embedding_api_base or "http://127.0.0.1:9997/v1"


@router.get("/models/runtime/catalog", response_model=XinferenceCatalogResponse)
async def query_runtime_catalog(
    model_type: str = Query("embedding", pattern=r"^(LLM|embedding|rerank)$"),
    q: str = Query("", max_length=120),
    param_q: str = Query("", max_length=120),
    downloaded: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    endpoint: Optional[str] = None,
):
    try:
        runtime_endpoint = endpoint or _default_runtime_endpoint()
        registrations = xinference_runtime.list_registrations(runtime_endpoint, model_type)
        cached = xinference_runtime.list_cached(runtime_endpoint)
        running = xinference_runtime.list_running(runtime_endpoint)
        cached_names = {
            str(item.get("model_name") or item.get("model_version") or "")
            for item in cached
        }
        running_names = {
            str(item.get("model_name") or item.get("id") or "")
            for item in running
        }
        needle = q.strip().lower()
        items: List[dict] = []
        for registration in registrations:
            name = str(
                registration.get("model_name")
                or registration.get("model_id")
                or registration.get("name")
                or ""
            )
            serialized = json.dumps(registration, ensure_ascii=False).lower()
            is_downloaded = name in cached_names or any(
                name and name in cached_name for cached_name in cached_names
            )
            if downloaded is not None and is_downloaded != downloaded:
                continue
            if needle and needle not in name.lower():
                continue
            if param_q.strip().lower() and param_q.strip().lower() not in serialized:
                continue
            items.append(
                {
                    "model_name": name,
                    "model_type": model_type,
                    "downloaded": is_downloaded,
                    "running": name in running_names,
                    "parameters": registration,
                }
            )
        total = len(items)
        start = (page - 1) * page_size
        return XinferenceCatalogResponse(
            items=items[start : start + page_size],
            total=total,
            page=page,
            page_size=page_size,
        )
    except Exception as exc:
        raise _runtime_error(exc) from exc


@router.get("/models/runtime/registrations", response_model=XinferenceRuntimeResponse)
async def list_runtime_registrations(
    model_type: str = Query("embedding", pattern=r"^(LLM|embedding|rerank)$"),
    endpoint: Optional[str] = None,
):
    try:
        models = xinference_runtime.list_registrations(endpoint or _default_runtime_endpoint(), model_type)
        return XinferenceRuntimeResponse(models=models)
    except Exception as exc:
        raise _runtime_error(exc) from exc


@router.get("/models/runtime/running", response_model=XinferenceRuntimeResponse)
async def list_runtime_running(endpoint: Optional[str] = None):
    try:
        models = xinference_runtime.list_running(endpoint or _default_runtime_endpoint())
        return XinferenceRuntimeResponse(models=models)
    except Exception as exc:
        raise _runtime_error(exc) from exc


@router.get("/models/runtime/cached", response_model=XinferenceRuntimeResponse)
async def list_runtime_cached(endpoint: Optional[str] = None):
    try:
        models = xinference_runtime.list_cached(endpoint or _default_runtime_endpoint())
        return XinferenceRuntimeResponse(models=models)
    except Exception as exc:
        raise _runtime_error(exc) from exc


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
        model_runtime.validate_catalog_model(body.db_values())
        return ModelConfigResponse(**db.create_model_config(**body.db_values()))
    except Exception as exc:
        raise _database_error(exc) from exc


@router.post("/models/{model_id}/deploy", response_model=XinferenceDeployResponse)
async def deploy_model(model_id: UUID, body: XinferenceLaunchInput):
    _require_database()
    try:
        model = db.get_model_config(str(model_id))
        if model is None:
            raise HTTPException(status_code=404, detail="模型不存在")
        if model["provider"] != "xinference":
            raise HTTPException(status_code=400, detail="只有 Xinference 模型支持自动部署")

        model_type = "LLM" if model["model_type"] == "chat" else model["model_type"]
        payload = {
            "model_name": model["model_name"],
            "model_type": model_type,
            "model_engine": body.model_engine,
            "model_format": body.model_format,
            "quantization": body.quantization,
            "size": body.size,
            "download_hub": body.download_hub,
            "gpu_idx": body.gpu_idx,
            "n_gpu": body.n_gpu,
            "enable_virtual_env": body.enable_virtual_env,
        }
        launch_keys = {
            "model_engine",
            "model_format",
            "quantization",
            "size",
            "download_hub",
            "gpu_idx",
            "n_gpu",
            "enable_virtual_env",
            "model_uid",
            "model_path",
        }
        payload.update(
            {
                key: value
                for key, value in (model.get("runtime_config") or {}).items()
                if key in launch_keys
            }
        )
        if body.model_uid:
            payload["model_uid"] = body.model_uid
        payload = {key: value for key, value in payload.items() if value is not None}
        runtime = xinference_runtime.launch(
            body.endpoint or model.get("endpoint") or _default_runtime_endpoint(),
            payload,
        )
        return XinferenceDeployResponse(model=ModelConfigResponse(**model), runtime=runtime)
    except HTTPException:
        raise
    except Exception as exc:
        raise _runtime_error(exc) from exc


@router.delete("/models/{model_id}/deploy", status_code=status.HTTP_204_NO_CONTENT)
async def terminate_model(model_id: UUID, model_uid: Optional[str] = None):
    _require_database()
    try:
        model = db.get_model_config(str(model_id))
        if model is None:
            raise HTTPException(status_code=404, detail="模型不存在")
        uid = model_uid or model["model_name"]
        xinference_runtime.terminate(
            model.get("endpoint") or _default_runtime_endpoint(), uid
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise _runtime_error(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/models/{model_id}", response_model=ModelConfigResponse)
async def update_model(model_id: UUID, body: ModelConfigInput):
    _require_database()
    try:
        existing = db.get_model_config(str(model_id))
        if existing is None:
            raise HTTPException(status_code=404, detail="模型不存在")
        model_runtime.validate_catalog_model(body.db_values())
        if existing["is_active"]:
            model_runtime.validate_activatable_model({**existing, **body.db_values()})
        row = db.update_model_config(model_id=str(model_id), **body.db_values())
    except HTTPException:
        raise
    except Exception as exc:
        raise _database_error(exc) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="模型不存在")
    if row["is_active"]:
        try:
            model_runtime.apply_model(row)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ModelConfigResponse(**row)


@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(model_id: UUID) -> Response:
    _require_database()
    try:
        existing = db.get_model_config(str(model_id))
        if existing is None:
            raise HTTPException(status_code=404, detail="模型不存在")
        if existing["is_active"]:
            raise HTTPException(status_code=409, detail="当前使用中的模型不能删除，请先切换到其他模型")
        deleted = db.delete_model_config(model_id=str(model_id))
    except HTTPException:
        raise
    except Exception as exc:
        raise _database_error(exc) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="模型不存在")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/models/{model_id}/activate", response_model=ModelActivationResponse)
async def activate_model(model_id: UUID):
    _require_database()
    try:
        candidate = db.get_model_config(str(model_id))
        if candidate is None:
            raise HTTPException(status_code=404, detail="模型不存在")
        model_runtime.validate_activatable_model(candidate)
        row = db.activate_model_config(model_id=str(model_id))
        if row is None:
            raise HTTPException(status_code=404, detail="模型不存在")
        model_runtime.apply_model(row)
    except HTTPException:
        raise
    except Exception as exc:
        raise _database_error(exc) from exc

    requires_reindex = row["model_type"] == "embedding"
    message = (
        "Embedding 已切换。旧 FAISS 索引已停止使用，请立即重建索引。"
        if requires_reindex
        else "对话模型已切换，后续新对话会使用该模型。"
    )
    return ModelActivationResponse(
        model=ModelConfigResponse(**row),
        requires_reindex=requires_reindex,
        message=message,
    )
