from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, ingest, logs, rag
from app.core.config import settings
from app.core.logger import logger
from app.db import postgres as db


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting LLMOps API (env=%s)", settings.app_env)
    if settings.database_enabled:
        db.ensure_schema()
    yield
    logger.info("Shutting down LLMOps API")


app = FastAPI(
    title="LLMOps API",
    description="LLM + RAG backend skeleton",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(ingest.router, prefix="/api", tags=["ingest"])
app.include_router(logs.router, prefix="/api", tags=["logs"])
app.include_router(rag.router, prefix="/api", tags=["rag"])


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "env": settings.app_env,
        "database": settings.database_enabled,
        "allow_online_api": settings.allow_online_api,
    }
