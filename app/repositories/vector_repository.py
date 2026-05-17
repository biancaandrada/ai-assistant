"""Data-access layer for the vector store. Uses ChromaClient under the hood."""
from dataclasses import dataclass
from typing import Sequence

from ..clients.chroma_client import ChromaClient
from ..core.errors import ExternalServiceError
from ..core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RetrievedChunk:
    id: str
    text: str
    score: float
    metadata: dict


class VectorRepository:
    """Domain-level operations over the Chroma collection."""

    def __init__(self, chroma: ChromaClient) -> None:
        self._collection = chroma.collection

    async def upsert(
        self,
        ids: Sequence[str],
        documents: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        metadatas: Sequence[dict] | None = None,
    ) -> None:
        try:
            self._collection.upsert(
                ids=list(ids),
                documents=list(documents),
                embeddings=list(embeddings),
                metadatas=list(metadatas) if metadatas else None,
            )
        except Exception as e:
            raise ExternalServiceError(f"vector store upsert failed: {e}") from e

    async def query(self, embedding: Sequence[float], top_k: int) -> list[RetrievedChunk]:
        try:
            res = self._collection.query(query_embeddings=[list(embedding)], n_results=top_k)
        except Exception as e:
            raise ExternalServiceError(f"vector store query failed: {e}") from e

        ids = res.get("ids", [[]])[0]
        docs = res.get("documents", [[]])[0]
        dists = res.get("distances", [[]])[0]
        metas = res.get("metadatas", [[]])[0] or [{}] * len(ids)
        return [
            RetrievedChunk(id=i, text=d, score=float(dist), metadata=m or {})
            for i, d, dist, m in zip(ids, docs, dists, metas)
        ]

    async def count(self) -> int:
        return self._collection.count()
