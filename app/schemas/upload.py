from pydantic import BaseModel


class UploadResponse(BaseModel):
    filename: str
    chars_extracted: int
    chunks_indexed: int
    status: str = "ok"
