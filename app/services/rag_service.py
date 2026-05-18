"""Retrieval-Augmented Generation orchestration."""
import re
import uuid
from typing import AsyncIterator

from ..core.config import Settings
from ..core.logging import get_logger
from ..repositories.vector_repository import VectorRepository, RetrievedChunk
from ..schemas.ask import Source
from ..utils.chunking import chunk_text
from .llm_service import LLMService

logger = get_logger(__name__)


def _humanize_filename(name: str) -> str:
    """'09_TOA_Client_Testimonials.pdf' → 'TOA Client Testimonials'."""
    base = re.sub(r"\.(pdf|txt|md|docx?)$", "", name, flags=re.IGNORECASE)
    # Strip leading numeric prefixes like '09_' or '01-'
    base = re.sub(r"^\d+[_\-\.\s]+", "", base)
    return base.replace("_", " ").replace("-", " ").strip()

SYSTEM_PROMPT = (
    "You are an assistant answering questions strictly from the user's uploaded "
    "documents. Relevant excerpts are provided below in a 'Context' section.\n\n"
    "CORE RULES:\n"
    "1. ONLY use information that is EXPLICITLY stated in the Context. Do not infer, "
    "   speculate, generalize, or extrapolate.\n"
    "2. If the Context directly answers the question: answer naturally and concisely, "
    "   quoting or paraphrasing the relevant text.\n"
    "3. If the Context only partially answers it: give the part you can support, then "
    "   say what's missing in one short sentence.\n"
    "4. If the Context does NOT contain information that answers the question: reply "
    "   with exactly: 'I don't have that information in the uploaded documents.' "
    "   Do NOT try to be helpful by guessing or filling in plausible-sounding details. "
    "   Do NOT add 'However, it can be inferred...' or similar phrasing.\n\n"
    "FORMATTING:\n"
    "- Write naturally, no bracketed citation markers like [1], [2].\n"
    "- No disclaimers, no 'based on the context provided' padding.\n"
    "- Just the answer."
)

QUERY_EXPANSION_PROMPT = (
    "Rewrite the user's question as a richer search query for a document retrieval "
    "system. Include the original question plus 4-8 related terms and synonyms that "
    "are likely to appear in relevant documents. Output ONLY the expanded query as "
    "one line of text, no quotes, no preamble, no formatting.\n\n"
    "Example:\n"
    "Input: What do participants say about TOA?\n"
    "Output: What do participants say about TOA? client testimonials feedback reviews "
    "opinions experiences quotes participant comments\n\n"
    "Input: How long is the sailing retreat?\n"
    "Output: How long is the sailing retreat? duration days length schedule itinerary "
    "trip timeline sailing program"
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

        Each chunk is embedded with its filename prefixed as a header — this
        makes the source identifier searchable, so queries like "client
        testimonials" match the file '09_TOA_Client_Testimonials.pdf' even
        when its contents are just names and quotes.
        """
        ids: list[str] = []
        stored_texts: list[str] = []
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
            # Humanize the filename for better embedding match
            # "09_TOA_Client_Testimonials.pdf" → "TOA Client Testimonials"
            readable = _humanize_filename(parent_id)

            for c in pieces:
                chunk_id = f"{parent_id}#{c.index}" if chunk and len(pieces) > 1 else parent_id
                embed_text = f"[Document: {readable}]\n\n{c.text}"
                ids.append(chunk_id)
                # Store the original text for display, but embed the prefixed version
                stored_texts.append(c.text)
                metas.append({
                    **meta, "source": parent_id, "chunk_index": c.index,
                    "title": readable,
                })
                embeddings.append(await self._llm.embed(embed_text))

        await self._vectors.upsert(
            ids=ids, documents=stored_texts, embeddings=embeddings, metadatas=metas,
        )
        logger.info(f"indexed {len(ids)} chunks from {len(docs)} documents")
        return len(ids)

    async def _expand_query(self, query: str) -> str:
        """Use the LLM to add synonyms and related terms so retrieval has more
        signal to match against, especially at low top-K."""
        try:
            expanded = await self._llm.chat([
                {"role": "system", "content": QUERY_EXPANSION_PROMPT},
                {"role": "user", "content": query},
            ])
            expanded = (expanded or "").strip().splitlines()[0] if expanded else query
            return expanded or query
        except Exception as e:
            # Expansion is a quality boost, not critical — fall back silently
            logger.warning(f"query expansion failed, using original: {e}")
            return query

    async def retrieve(self, query: str, top_k: int) -> list[RetrievedChunk]:
        expanded = await self._expand_query(query)
        if expanded != query:
            logger.info(f"query expansion: '{query}' → '{expanded}'")
        emb = await self._llm.embed(expanded)
        return await self._vectors.query(embedding=emb, top_k=top_k)

    @staticmethod
    def _build_context(chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return ""
        parts: list[str] = []
        for i, c in enumerate(chunks):
            title = (c.metadata or {}).get("title") or (c.metadata or {}).get("source") or "doc"
            parts.append(f"[{i + 1}] (from {title})\n{c.text}")
        return "Context:\n" + "\n\n".join(parts)

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
        """Token-only stream (legacy)."""
        messages, _ = await self._build_messages(question, use_rag, top_k)
        async for tok in self._llm.chat_stream(messages):
            yield tok

    async def stream_answer_with_sources(
        self, question: str, use_rag: bool, top_k: int
    ) -> AsyncIterator[dict]:
        """Event-based stream: emits a sources event first, then token events.

        Events:
            {"type": "sources", "data": [Source, ...]}
            {"type": "token",   "data": "..."}
        """
        messages, sources = await self._build_messages(question, use_rag, top_k)
        yield {"type": "sources", "data": [s.model_dump() for s in sources]}
        async for tok in self._llm.chat_stream(messages):
            yield {"type": "token", "data": tok}
