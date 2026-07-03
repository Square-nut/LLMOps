from typing import Optional

from app.core.llm_gateway import TaskType


async def chat(
    message: str,
    *,
    user_id: Optional[str] = None,
    use_rag: bool = True,
    task_type: TaskType = TaskType.SIMPLE,
) -> dict:
    """
    Chat 业务编排（ARCHITECTURE.md §6）。

    建议实现顺序：
    1. 若 use_rag → retrieve_context(message)
    2. 读 prompts/chat_v1.txt 作为 system_prompt
    3. llm_gateway.completion(...)
    4. supabase.log_chat(...)
    5. 组装返回 dict
    """
    raise NotImplementedError("Phase 1+: 在 services/chat_service.py 中实现 chat 编排")
