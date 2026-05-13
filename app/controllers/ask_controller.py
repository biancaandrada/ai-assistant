"""Controller for question-answering with optional RAG."""
from typing import AsyncIterator
from fastapi import HTTPException

from ..models import AskRequest, AskResponse
from ..rag import retrieve
from ..agent import stream_answer


class AskController:
    """Orchestrates the /ask flow: validation, retrieval, generation, response shaping."""

    @staticmethod
    def _validate(req: AskRequest) -> None:
        if not req.question.strip():
            raise HTTPException(status_code=400, detail="question is empty")
        if req.top_k < 1 or req.top_k > 20:
            raise HTTPException(status_code=400, detail="top_k must be between 1 and 20")

    @classmethod
    async def handle(cls, req: AskRequest) -> AskResponse:
        """HTTP path: collect every streamed token into one response."""
        cls._validate(req)

        sources: list[str] = []
        if req.use_rag:
            _, ids = await retrieve(req.question, top_k=req.top_k)
            sources = ids

        chunks: list[str] = []
        async for tok in stream_answer(req.question, use_rag=req.use_rag, top_k=req.top_k):
            chunks.append(tok)

        return AskResponse(
            answer="".join(chunks),
            sources=sources,
            session_id=req.session_id,
        )

    @classmethod
    async def stream(cls, req: AskRequest) -> AsyncIterator[str]:
        """WebSocket path: yield tokens as they arrive."""
        cls._validate(req)
        async for tok in stream_answer(req.question, use_rag=req.use_rag, top_k=req.top_k):
            yield tok
