from typing import Optional

from app.core.llm_gateway import TaskType, completion

from pathlib import Path

def _load_system_prompt() -> str:
    prompt_path = Path(__file__).parent.parent / "prompts" / "chat_v1.txt"
    return prompt_path.read_text(encoding="utf-8").strip()



async def chat(
    message: str,
    *,
    user_id: Optional[str] = None,
    use_rag: bool = True,
    task_type: TaskType = TaskType.SIMPLE,
) -> dict:

    # 跳过 RAG 的逻辑
    # if use_rag:
    # context = retrieve_context(message)

    system_prompt = _load_system_prompt()

    result = completion(
        message,
        system_prompt=system_prompt,
        task_type=task_type,
    )

    return {
        "reply": result["content"],
        "model": result["model"],
        "tokens": result["tokens"],
        "latency_ms": result["latency_ms"],
        "used_rag": False,
    }
    
