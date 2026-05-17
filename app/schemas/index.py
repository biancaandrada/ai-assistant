from pydantic import BaseModel, Field
from typing import Optional


class Document(BaseModel):
    id: Optional[str] = None
    text: str = Field(..., min_length=1)
    metadata: dict = {}


class IndexRequest(BaseModel):
    documents: list[Document] = Field(..., min_length=1)


class IndexResponse(BaseModel):
    indexed: int
    status: str = "ok"
