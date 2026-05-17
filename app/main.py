"""FastAPI application factory.

Wires settings → logging → clients → repos → services → controllers → routes.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.v1.router import api_router
from .clients import ChromaClient, OpenAIClient
from .controllers import AgentController, AskController, IndexController
from .core.config import Settings, get_settings
from .core.logging import configure_logging, get_logger
from .core.middleware import RequestContextMiddleware, register_exception_handlers
from .repositories.vector_repository import VectorRepository
from .services.agent_service import AgentService
from .services.llm_service import LLMService
from .services.rag_service import RAGService
from .tools import CalcTool, SearchTool, ToolRegistry
from .websocket import router as ws_router

logger = get_logger(__name__)


def _build_container(settings: Settings) -> dict:
    """Wire all singletons. Returns the DI container."""
    # Clients (SDK wrappers)
    openai_client = OpenAIClient(settings)
    chroma_client = ChromaClient(settings)

    # Repositories (data access)
    vectors = VectorRepository(chroma_client)

    # Services (business logic)
    llm = LLMService(openai_client)
    rag = RAGService(settings, llm, vectors)

    # Tools
    tools = ToolRegistry()
    tools.register(SearchTool(rag, top_k=settings.rag_default_top_k))
    tools.register(CalcTool())

    agent = AgentService(settings, llm, tools)

    return {
        "settings": settings,
        "openai_client": openai_client,
        "chroma_client": chroma_client,
        "vectors": vectors,
        "llm": llm,
        "rag": rag,
        "tools": tools,
        "agent": agent,
        "ask_controller": AskController(rag),
        "agent_controller": AgentController(agent),
        "index_controller": IndexController(rag),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings)
    logger.info(f"starting {settings.app_name} v{settings.app_version} ({settings.environment})")

    for k, v in _build_container(settings).items():
        setattr(app.state, k, v)

    yield
    logger.info("shutting down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)
    app.include_router(ws_router, prefix=settings.api_prefix)

    return app


app = create_app()
