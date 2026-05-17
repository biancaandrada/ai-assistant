from pydantic import BaseModel, Field
from typing import Optional


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = None
    use_rag: bool = True
    top_k: int = Field(3, ge=1, le=20)


class Source(BaseModel):
    id: str
    snippet: str


class AskResponse(BaseModel):
    answer: str
    sources: list[Source] = []
    session_id: Optional[str] = None
