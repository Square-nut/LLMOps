import time
from enum import Enum
from typing import Any, Dict, Optional

from openai import OpenAI

from app.core.config import settings
from app.core.logger import logger

_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.geekai_api_key:
            raise ValueError("GEEKAI_API_KEY is not configured")
        _client = OpenAI(
            api_key=settings.geekai_api_key,
            base_url=settings.geekai_base_url,
        )
    return _client


class TaskType(str, Enum):
    """任务类型，用于选模型（Phase 4 实现 select_model）。"""

    SIMPLE = "simple"
    REASONING = "reasoning"
    LONG_CONTEXT = "long_context"


def select_model(task_type: TaskType = TaskType.SIMPLE, context_length: int = 0) -> str:
    """根据任务类型选择模型。TODO: Phase 4 实现。"""
    raise NotImplementedError("Phase 4: 在 llm_gateway.select_model 中实现模型路由")


def _build_messages(
    user_message: str,
    system_prompt: Optional[str] = None,
    context: Optional[str] = None,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    if context:
        messages.append({
            "role": "system",
            "content": f"Use the following context to answer the user question.\n\n{context}",
        })

    messages.append({"role": "user", "content": user_message})
    return messages


def completion(
    user_message: str,
    *,
    system_prompt: Optional[str] = None,
    context: Optional[str] = None,
    task_type: TaskType = TaskType.SIMPLE,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    selected_model = model or settings.default_model
    messages = _build_messages(user_message, system_prompt, context)

    start = time.perf_counter()
    try:
        response = get_client().chat.completions.create(
            model=selected_model,
            messages=messages,
            stream=False,
        )
    except Exception as exc:
        logger.error("LLM completion failed model=%s: %s", selected_model, exc)
        raise

    latency_ms = int((time.perf_counter() - start) * 1000)
    content = response.choices[0].message.content or ""
    usage = response.usage

    return {
        "content": content,
        "model": selected_model,
        "tokens": {
            "prompt": getattr(usage, "prompt_tokens", 0) or 0,
            "completion": getattr(usage, "completion_tokens", 0) or 0,
            "total": getattr(usage, "total_tokens", 0) or 0,
        },
        "latency_ms": latency_ms,
    }
