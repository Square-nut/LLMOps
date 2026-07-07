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
    """根据任务类型与上下文长度选择模型。"""
    if task_type == TaskType.REASONING:
        return settings.reasoning_model
    if task_type == TaskType.LONG_CONTEXT or context_length > 8000:
        return settings.long_context_model
    return settings.default_model


def _estimate_context_length(
    user_message: str,
    system_prompt: Optional[str] = None,
    context: Optional[str] = None,
) -> int:
    total = len(user_message)
    if system_prompt:
        total += len(system_prompt)
    if context:
        total += len(context)
    return total


def _create_completion(model: str, messages: list[dict[str, str]]):
    return get_client().chat.completions.create(
        model=model,
        messages=messages,
        stream=False,
    )


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
    context_length = _estimate_context_length(user_message, system_prompt, context)
    selected_model = model or select_model(task_type, context_length=context_length)
    messages = _build_messages(user_message, system_prompt, context)

    start = time.perf_counter()
    try:
        response = _create_completion(selected_model, messages)
    except Exception as exc:
        fallback = settings.fallback_model
        if selected_model == fallback:
            logger.error("LLM completion failed model=%s: %s", selected_model, exc)
            raise
        logger.warning(
            "LLM completion failed model=%s, retrying fallback=%s: %s",
            selected_model,
            fallback,
            exc,
        )
        selected_model = fallback
        response = _create_completion(selected_model, messages)

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
