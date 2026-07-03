from typing import Any


def add_documents(documents: list[Any]) -> int:
    """
    生成 embedding 并写入 FAISS。

    TODO Phase 2: LlamaIndex + FaissVectorStore，持久化到 settings.faiss_index_path。
    """
    raise NotImplementedError("Phase 2: 在 rag/index.py 中实现向量入库")


def get_index() -> Any:
    """加载或创建 FAISS 索引。TODO Phase 2。"""
    raise NotImplementedError("Phase 2: 在 rag/index.py 中实现 get_index")
