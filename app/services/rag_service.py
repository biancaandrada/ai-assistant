"""Retrieval-Augmented Generation orchestration."""
import uuid
from typing import AsyncIterator

from ..core.config import Settings
from ..core.logging import get_logger
from ..repositories.vector_repository import VectorRepository, RetrievedChunk
from ..schemas.ask import Source
from ..utils.chunking import chunk_text
from .llm_service import LLMService

logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are a helpful assistant. When context is provided, ground your answer in it "
    "and cite sources as [1], [2], etc. If the context is insufficient, say so."
)


class RAGService:
    def __init__(
        self,
        settings: Settings,
        llm: LLMService,
        vectors: VectorRepository,
    ) -> None:
        self._settings = settings
        self._llm = llm
        self._vectors = vectors

    async def index_documents(
        self,
        docs: list[tuple[str | None, str, dict]],
        *,
        chunk: bool = True,
    ) -> int:
        """Embed and store documents. `docs` is list of (id?, text, metadata).

        Long documents are split into overlapping chunks before embedding —
        each chunk becomes its own vector store entry, tagged with the parent id.
        """
        ids: list[str] = []
        texts: list[str] = []
        metas: list[dict] = []
        embeddings: list[list[float]] = []

        for parent_id, text, meta in docs:
            parent_id = parent_id or f"doc-{uuid.uuid4().hex[:12]}"
            pieces = (
                chunk_text(text, chunk_size=self._settings.chunk_size,
                           overlap=self._settings.chunk_overlap, source=parent_id)
                if chunk
                else [type("C", (), {"text": text, "index": 0, "source": parent_id})()]
            )
            for c in pieces:
                chunk_id = f"{parent_id}#{c.index}" if chunk and len(pieces) > 1 else parent_id
                ids.append(chunk_id)
                texts.append(c.text)
                metas.append({**meta, "source": parent_id, "chunk_index": c.index})
                embeddings.append(await self._llm.embed(c.text))

        await self._vectors.upsert(ids=ids, documents=texts, embeddings=embeddings, metadatas=metas)
        logger.info(f"indexed {len(ids)} chunks from {len(docs)} documents")
        return len(ids)

    async def retrieve(self, query: str, top_k: int) -> list[RetrievedChunk]:
        emb = await self._llm.embed(query)
        return await self._vectors.query(embedding=emb, top_k=top_k)

    @staticmethod
    def _build_context(chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return ""
        return "Context:\n" + "\n\n".join(f"[{i + 1}] {c.text}" for i, c in enumerate(chunks))

    @staticmethod
    def _to_sources(chunks: list[RetrievedChunk]) -> list[Source]:
        return [Source(id=c.id, snippet=c.text[:200]) for c in chunks]

    async def _build_messages(
        self, question: str, use_rag: bool, top_k: int
    ) -> tuple[list[dict], list[Source]]:
        messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        sources: list[Source] = []

        if use_rag:
            chunks = await self.retrieve(question, top_k=top_k)
            ctx = self._build_context(chunks)
            if ctx:
                messages.append({"role": "system", "content": ctx})
            sources = self._to_sources(chunks)

        messages.append({"role": "user", "content": question})
        return messages, sources

    async def answer(self, question: str, use_rag: bool, top_k: int) -> tuple[str, list[Source]]:
        messages, sources = await self._build_messages(question, use_rag, top_k)
        chunks: list[str] = []
        async for tok in self._llm.chat_stream(messages):
            chunks.append(tok)
        return "".join(chunks), sources

    async def stream_answer(
        self, question: str, use_rag: bool, top_k: int
    ) -> AsyncIterator[str]:
        messages, _ = await self._build_messages(question, use_rag, top_k)
        async for tok in self._llm.chat_stream(messages):
            yield tok
