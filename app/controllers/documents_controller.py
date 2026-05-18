from ..repositories.vector_repository import VectorRepository
from ..schemas.documents import DeleteResponse, DocumentList, DocumentSummary


class DocumentsController:
    def __init__(self, vectors: VectorRepository) -> None:
        self._vectors = vectors

    async def list(self) -> DocumentList:
        rows = await self._vectors.list_sources()
        docs = [DocumentSummary(**r) for r in rows]
        return DocumentList(documents=docs, total=len(docs))

    async def delete(self, source: str) -> DeleteResponse:
        n = await self._vectors.delete_by_source(source)
        # Get the new list of documents after deletion
        rows = await self._vectors.list_sources()
        remaining_docs = [DocumentSummary(**r) for r in rows]
        return DeleteResponse(source=source, deleted_chunks=n, remaining_documents=remaining_docs)
