"""Application configuration via environment variables / .env file."""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed app settings. Read once at startup, then injected via deps."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "AI Assistant"
    app_version: str = "1.0.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_json: bool = False  # set True in prod for structured logs

    # API
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # OpenAI
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_timeout_s: float = 30.0
    openai_max_retries: int = 2

    # Vector store
    chroma_path: str = "./chroma_db"
    chroma_collection: str = "documents"

    # Chunking — smaller chunks = more precise retrieval.
    # ~400 chars ≈ 80-100 tokens, big enough for context, small enough to discriminate.
    chunk_size: int = 400
    chunk_overlap: int = 60

    # Agent
    agent_max_steps: int = 5
    agent_max_steps_hard_cap: int = 20

    # Ask
    rag_default_top_k: int = 8
    rag_max_top_k: int = 20


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor. Import this everywhere — single source of truth."""
    return Settings()  # type: ignore[call-arg]
