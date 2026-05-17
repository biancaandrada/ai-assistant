from ..services.rag_service import RAGService
from .base import Tool


class SearchTool(Tool):
    name = "search"
    description = "Search the document knowledge base. Input: a natural-language query."

    def __init__(self, rag: RAGService, top_k: int = 3) -> None:
        self._rag = rag
        self._top_k = top_k

    async def run(self, action_input: str) -> str:
        chunks = await self._rag.retrieve(action_input, top_k=self._top_k)
        if not chunks:
            return "No results."
        return "\n\n".join(f"[{i + 1}] {c.text}" for i, c in enumerate(chunks))
