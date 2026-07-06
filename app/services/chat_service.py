from pathlib import Path
from typing import Optional

from app.core.llm_gateway import TaskType, completion
from app.db import postgres as db
from app.rag.retrieve import retrieve_context


def _load_system_prompt() -> str:
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "chat_v1.txt"
    return prompt_path.read_text(encoding="utf-8").strip()


async def chat(
    message: str,
    *,
    user_id: Optional[str] = None,
    use_rag: bool = True,
    task_type: TaskType = TaskType.SIMPLE,
) -> dict:
    context = retrieve_context(message) if use_rag else None
    system_prompt = _load_system_prompt()

    result = completion(
        message,
        system_prompt=system_prompt,
        context=context or None,
        task_type=task_type,
    )

    db.log_chat(
        user_id=user_id,
        input_text=message,
        output_text=result["content"],
        model=result["model"],
        tokens=result["tokens"],
        latency_ms=result["latency_ms"],
    )

    return {
        "reply": result["content"],
        "model": result["model"],
        "tokens": result["tokens"],
        "latency_ms": result["latency_ms"],
        "used_rag": bool(context),
    }
