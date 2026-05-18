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

    async def list_sources(self) -> list[dict]:
        """Distinct uploaded files, with chunk count and total chars.

        Reads metadata.source from all stored chunks and aggregates.
        """
        try:
            res = self._collection.get(include=["metadatas", "documents"])
        except Exception as e:
            raise ExternalServiceError(f"vector store list failed: {e}") from e

        metas = res.get("metadatas") or []
        docs = res.get("documents") or []
        agg: dict[str, dict] = {}
        for meta, doc in zip(metas, docs):
            source = (meta or {}).get("source") or (meta or {}).get("filename") or "unknown"
            entry = agg.setdefault(source, {"source": source, "chunks": 0, "chars": 0})
            entry["chunks"] += 1
            entry["chars"] += len(doc or "")
        return sorted(agg.values(), key=lambda x: x["source"])

    async def delete_by_source(self, source: str) -> int:
        """Delete all chunks belonging to a source.

        Uses the same fallback logic as `list_sources` — a chunk belongs to
        `source` if its metadata.source == source, OR metadata.filename == source,
        OR (source == "unknown" AND both fields are missing). This matters for
        legacy chunks indexed before the `source` field was added.
        """
        try:
            res = self._collection.get(include=["metadatas"])
            all_ids = res.get("ids") or []
            metas = res.get("metadatas") or []

            ids_to_delete: list[str] = []
            for chunk_id, meta in zip(all_ids, metas):
                meta = meta or {}
                actual = meta.get("source") or meta.get("filename") or "unknown"
                if actual == source:
                    ids_to_delete.append(chunk_id)

            if ids_to_delete:
                self._collection.delete(ids=ids_to_delete)
                logger.info(f"deleted {len(ids_to_delete)} chunks for source: {source}")
            else:
                logger.warning(f"no chunks found for source: {source}")
            return len(ids_to_delete)
        except Exception as e:
            logger.error(f"failed to delete chunks for source {source}: {e}")
            raise ExternalServiceError(f"vector store delete failed: {e}") from e
