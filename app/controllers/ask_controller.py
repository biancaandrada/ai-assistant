"""Ask flow orchestration. Thin layer between routes and services."""
from typing import AsyncIterator

from ..schemas.ask import AskRequest, AskResponse
from ..services.rag_service import RAGService


class AskController:
    def __init__(self, rag: RAGService) -> None:
        self._rag = rag

    async def handle(self, req: AskRequest) -> AskResponse:
        answer, sources = await self._rag.answer(
            question=req.question, use_rag=req.use_rag, top_k=req.top_k
        )
        return AskResponse(answer=answer, sources=sources, session_id=req.session_id)

    async def stream(self, req: AskRequest) -> AsyncIterator[str]:
        async for tok in self._rag.stream_answer(
            question=req.question, use_rag=req.use_rag, top_k=req.top_k
        ):
            yield tok
