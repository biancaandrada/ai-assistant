"""Bulk-ingest documents from the data/ folder into the vector store.

Usage:
    python -m scripts.ingest                  # ingests every *.txt in data/
    python -m scripts.ingest path/to/file.txt

Each file is read, chunked, embedded, and upserted under id=<filename>.
"""
import asyncio
import sys
from pathlib import Path

from app.clients import ChromaClient, OpenAIClient
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.repositories.vector_repository import VectorRepository
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService

logger = get_logger(__name__)


async def _ingest_paths(paths: list[Path]) -> None:
    settings = get_settings()
    configure_logging(settings)

    openai = OpenAIClient(settings)
    chroma = ChromaClient(settings)
    vectors = VectorRepository(chroma)
    llm = LLMService(openai)
    rag = RAGService(settings, llm, vectors)

    docs: list[tuple[str | None, str, dict]] = []
    for p in paths:
        if not p.is_file():
            logger.warning(f"skipping {p}: not a file")
            continue
        text = p.read_text(encoding="utf-8")
        docs.append((p.stem, text, {"path": str(p)}))
        logger.info(f"queued {p} ({len(text)} chars)")

    if not docs:
        logger.warning("nothing to ingest")
        return

    count = await rag.index_documents(docs)
    logger.info(f"done — indexed {count} chunks from {len(docs)} files")


def main() -> None:
    if len(sys.argv) > 1:
        paths = [Path(a) for a in sys.argv[1:]]
    else:
        data_dir = Path(__file__).resolve().parents[1] / "data"
        paths = sorted(data_dir.glob("*.txt")) + sorted(data_dir.glob("*.md"))

    if not paths:
        print("No files to ingest. Drop .txt/.md files in data/ or pass paths as args.")
        return

    asyncio.run(_ingest_paths(paths))


if __name__ == "__main__":
    main()
