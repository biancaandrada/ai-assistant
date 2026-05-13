import os
from typing import List, Tuple
import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

_client = chromadb.PersistentClient(
    path=os.getenv("CHROMA_PATH", "./chroma_db"),
    settings=Settings(anonymized_telemetry=False),
)
_collection = _client.get_or_create_collection(name="documents")
_openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EMBED_MODEL = "text-embedding-3-small"


async def _embed(text: str) -> List[float]:
    resp = await _openai.embeddings.create(model=EMBED_MODEL, input=text)
    return resp.data[0].embedding


async def add_documents(docs: List[str], ids: List[str] | None = None) -> None:
    if ids is None:
        ids = [f"doc-{i}" for i in range(len(docs))]
    embeddings = [await _embed(d) for d in docs]
    _collection.upsert(ids=ids, documents=docs, embeddings=embeddings)


async def retrieve(query: str, top_k: int = 3) -> Tuple[List[str], List[str]]:
    q_emb = await _embed(query)
    result = _collection.query(query_embeddings=[q_emb], n_results=top_k)
    docs = result.get("documents", [[]])[0]
    ids = result.get("ids", [[]])[0]
    return docs, ids


def build_context(docs: List[str]) -> str:
    if not docs:
        return ""
    parts = [f"[{i + 1}] {d}" for i, d in enumerate(docs)]
    return "Context:\n" + "\n\n".join(parts)
