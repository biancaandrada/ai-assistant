"""Upload a file → extract text → ingest into RAG."""
from ..core.errors import ValidationError
from ..core.logging import get_logger
from ..schemas.upload import UploadResponse
from ..services.rag_service import RAGService
from ..utils.pdf import extract_text

logger = get_logger(__name__)

MAX_BYTES = 20 * 1024 * 1024  # 20 MB


class UploadController:
    def __init__(self, rag: RAGService) -> None:
        self._rag = rag

    async def handle_pdf(self, filename: str, data: bytes) -> UploadResponse:
        if len(data) > MAX_BYTES:
            raise ValidationError(f"file too large (max {MAX_BYTES // 1024 // 1024} MB)")
        if not filename.lower().endswith(".pdf"):
            raise ValidationError("only .pdf is supported")

        text = extract_text(data)
        chunks_indexed = await self._rag.index_documents(
            [(filename, text, {"filename": filename, "source": "upload"})]
        )
        logger.info(f"uploaded {filename}: {len(text)} chars → {chunks_indexed} chunks")
        return UploadResponse(
            filename=filename,
            chars_extracted=len(text),
            chunks_indexed=chunks_indexed,
        )
