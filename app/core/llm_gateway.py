import time
from enum import Enum
from typing import Any, Dict, Optional

from openai import OpenAI

from app.core.config import settings
from app.core.online_api import require_online_api
from app.core.logger import logger
from app.services.model_runtime import active_chat_completion_options, active_chat_is_online, active_chat_uses_catalog

_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.geekai_api_key:
            raise ValueError("Active chat provider API key is not configured")
        _client = OpenAI(
            api_key=settings.geekai_api_key,
            base_url=settings.geekai_base_url,
        )
    return _client


def reset_client() -> None:
    global _client
    _client = None


class TaskType(str, Enum):
    """任务类型，用于选模型（Phase 4 实现 select_model）。"""

    SIMPLE = "simple"
    REASONING = "reasoning"
    LONG_CONTEXT = "long_context"


def select_model(task_type: TaskType = TaskType.SIMPLE, context_length: int = 0) -> str:
    """根据任务类型与上下文长度选择模型。"""
    # A catalogue selection is deliberately singular: all Chat requests use
    # the active record instead of hidden task-specific .env routes.
    if active_chat_uses_catalog():
        return settings.default_model
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
        **active_chat_completion_options(),
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
    use_mock: bool = True,
) -> Dict[str, Any]:
    if (
        use_mock
        and settings.embedding_provider == "mock"
        and settings.mock_chat_enabled
        and user_message.strip() == settings.mock_rag_query.strip()
    ):
        return {
            "content": settings.mock_chat_reply,
            "model": "mock-chat",
            "tokens": {"prompt": 0, "completion": 0, "total": 0},
            "latency_ms": 0,
        }

    if active_chat_is_online():
        require_online_api("chat completion")
    context_length = _estimate_context_length(user_message, system_prompt, context)
    selected_model = model or select_model(task_type, context_length=context_length)
    messages = _build_messages(user_message, system_prompt, context)

    start = time.perf_counter()
    try:
        response = _create_completion(selected_model, messages)
    except Exception as exc:
        # Once a catalogue model is active, do not silently fall back to an
        # independent .env model. The selected catalogue record is the single
        # source of truth for Chat routing.
        if active_chat_uses_catalog():
            logger.error("Active catalogue chat model failed model=%s: %s", selected_model, exc)
            raise
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
