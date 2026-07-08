import hashlib
from typing import List

from llama_index.core.embeddings import BaseEmbedding


class MockEmbedding(BaseEmbedding):
    """Deterministic local embeddings for dev/testing without cloud API."""

    embed_dim: int = 1536

    def _embed(self, text: str) -> List[float]:
        seed = hashlib.sha256(text.encode("utf-8")).digest()
        vec: List[float] = []
        counter = 0
        while len(vec) < self.embed_dim:
            for byte in seed:
                if len(vec) >= self.embed_dim:
                    break
                vec.append((byte / 127.5) - 1.0)
                counter += 1
            seed = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]

    def _get_query_embedding(self, query: str) -> List[float]:
        return self._embed(query)

    def _get_text_embedding(self, text: str) -> List[float]:
        return self._embed(text)

    async def _aget_query_embedding(self, query: str) -> List[float]:
        return self._get_query_embedding(query)
