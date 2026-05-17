"""Test fixtures. Stubs the OpenAI client and vector store — no network."""
import os
from typing import AsyncIterator

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("CHROMA_PATH", "./.test_chroma")

from app.clients.openai_client import OpenAIClient  # noqa: E402
from app.main import create_app  # noqa: E402
from app.repositories.vector_repository import RetrievedChunk, VectorRepository  # noqa: E402


class FakeOpenAIClient(OpenAIClient):
    def __init__(self) -> None:  # skip parent __init__
        self.embed_calls: list[str] = []
        self.chat_calls: list[list[dict]] = []

    async def embed(self, text: str) -> list[float]:
        self.embed_calls.append(text)
        return [0.1, 0.2, 0.3]

    async def chat(self, messages: list[dict], *, json_mode: bool = False) -> str:
        self.chat_calls.append(messages)
        if json_mode:
            return '{"thought":"done","action":"final","action_input":"42"}'
        return "stub answer"

    async def chat_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        self.chat_calls.append(messages)
        for tok in ["stub ", "answer"]:
            yield tok


class FakeVectorRepo(VectorRepository):
    def __init__(self) -> None:  # skip parent __init__
        self._store: dict[str, str] = {}

    async def upsert(self, ids, documents, embeddings, metadatas=None) -> None:
        for i, d in zip(ids, documents):
            self._store[i] = d

    async def query(self, embedding, top_k):
        return [
            RetrievedChunk(id=k, text=v, score=0.0, metadata={})
            for k, v in list(self._store.items())[:top_k]
        ]

    async def count(self) -> int:
        return len(self._store)


@pytest.fixture
def app():
    """Provide a fresh app with all clients swapped for fakes."""
    app = create_app()

    with TestClient(app) as client:
        fake_openai = FakeOpenAIClient()
        fake_vec = FakeVectorRepo()
        app.state.openai_client = fake_openai
        app.state.vectors = fake_vec

        from app.controllers import AgentController, AskController, IndexController
        from app.services.agent_service import AgentService
        from app.services.llm_service import LLMService
        from app.services.rag_service import RAGService
        from app.tools import CalcTool, SearchTool, ToolRegistry

        llm = LLMService(fake_openai)
        rag = RAGService(app.state.settings, llm, fake_vec)
        tools = ToolRegistry()
        tools.register(SearchTool(rag))
        tools.register(CalcTool())
        agent = AgentService(app.state.settings, llm, tools)

        app.state.llm = llm
        app.state.rag = rag
        app.state.agent = agent
        app.state.ask_controller = AskController(rag)
        app.state.agent_controller = AgentController(agent)
        app.state.index_controller = IndexController(rag)

        yield app, client
