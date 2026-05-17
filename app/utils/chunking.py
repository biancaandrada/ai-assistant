"""Text chunking for RAG ingestion.

Embeddings work best on focused chunks (~200-500 tokens). Long documents need
to be split before being indexed — otherwise retrieval returns noisy mega-blobs
and the LLM gets distracted.

The chunker is paragraph-aware: it splits on blank lines first, then packs
paragraphs into chunks up to `chunk_size` chars with optional `overlap`
between consecutive chunks to preserve context across boundaries.
"""
from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    index: int
    source: str | None = None


def chunk_text(
    text: str,
    *,
    chunk_size: int = 1000,
    overlap: int = 150,
    source: str | None = None,
) -> list[Chunk]:
    """Split text into overlapping chunks.

    Args:
        text: raw text to chunk.
        chunk_size: target characters per chunk (default ~250 tokens).
        overlap: characters carried from end of previous chunk into next.
        source: optional source identifier (filename, URL) for traceability.

    Returns:
        Non-empty Chunks ordered by position.
    """
    if not text.strip():
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be in [0, chunk_size)")

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buf = ""

    def _hard_split(s: str) -> list[str]:
        step = chunk_size - overlap
        return [s[i : i + chunk_size] for i in range(0, len(s), step) if s[i : i + chunk_size]]

    for para in paragraphs:
        if len(buf) + len(para) + 2 <= chunk_size:
            buf = f"{buf}\n\n{para}".strip() if buf else para
            continue

        if buf:
            chunks.append(buf)
            buf = ""
        if len(para) > chunk_size:
            chunks.extend(_hard_split(para))
        else:
            buf = para

    if buf:
        chunks.append(buf)

    return [Chunk(text=c, index=i, source=source) for i, c in enumerate(chunks)]
