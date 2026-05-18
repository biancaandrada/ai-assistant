from pydantic import BaseModel


class DocumentSummary(BaseModel):
    source: str
    chunks: int
    chars: int


class DocumentList(BaseModel):
    documents: list[DocumentSummary]
    total: int


class DeleteResponse(BaseModel):
    source: str
    deleted_chunks: int
    status: str = "ok"
    remaining_documents: list[DocumentSummary] = []
