from typing import Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.llm_gateway import TaskType
from app.services import chat_service

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    user_id: Optional[str] = None
    use_rag: bool = True
    task_type: TaskType = TaskType.SIMPLE


class ChatResponse(BaseModel):
    reply: str
    model: str
    tokens: Dict[str, int]
    latency_ms: int
    used_rag: bool


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(body: ChatRequest) -> ChatResponse:
    try:
        result = await chat_service.chat(
            body.message,
            user_id=body.user_id,
            use_rag=body.use_rag,
            task_type=body.task_type,
        )
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    return ChatResponse(**result)
