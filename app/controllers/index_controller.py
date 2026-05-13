"""Controller for document indexing."""
from fastapi import HTTPException

from ..rag import add_documents


class IndexController:
    """Orchestrates uploads into the vector store."""

    @staticmethod
    def _validate(docs: list[str]) -> None:
        if not docs:
            raise HTTPException(status_code=400, detail="docs list is empty")
        if any(not d.strip() for d in docs):
            raise HTTPException(status_code=400, detail="docs cannot contain empty strings")

    @classmethod
    async def handle(cls, docs: list[str]) -> dict:
        cls._validate(docs)
        await add_documents(docs)
        return {"indexed": len(docs), "status": "ok"}
