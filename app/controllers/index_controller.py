from ..schemas.index import IndexRequest, IndexResponse
from ..services.rag_service import RAGService


class IndexController:
    def __init__(self, rag: RAGService) -> None:
        self._rag = rag

    async def handle(self, req: IndexRequest) -> IndexResponse:
        docs = [(d.id, d.text, d.metadata) for d in req.documents]
        count = await self._rag.index_documents(docs)
        return IndexResponse(indexed=count)
