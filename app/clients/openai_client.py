"""Thin SDK wrapper around OpenAI. The only place that imports `openai`.

Maps SDK errors to app exceptions, owns connection/timeout/retry config.
Services consume this — they don't touch the SDK directly.
"""
from typing import AsyncIterator

from openai import AsyncOpenAI, APIError, APITimeoutError
from openai import RateLimitError as OpenAIRateLimit

from ..core.config import Settings
from ..core.errors import ExternalServiceError, RateLimitError
from ..core.logging import get_logger

logger = get_logger(__name__)


class OpenAIClient:
    def __init__(self, settings: Settings) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout_s,
            max_retries=settings.openai_max_retries,
        )
        self._chat_model = settings.openai_chat_model
        self._embed_model = settings.openai_embedding_model

    async def embed(self, text: str) -> list[float]:
        try:
            resp = await self._client.embeddings.create(model=self._embed_model, input=text)
            return resp.data[0].embedding
        except OpenAIRateLimit as e:
            raise RateLimitError("OpenAI rate limit") from e
        except (APIError, APITimeoutError) as e:
            raise ExternalServiceError(f"OpenAI embed failed: {e}") from e

    async def chat(self, messages: list[dict], *, json_mode: bool = False) -> str:
        kwargs: dict = {"model": self._chat_model, "messages": messages}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            resp = await self._client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content or ""
        except OpenAIRateLimit as e:
            raise RateLimitError("OpenAI rate limit") from e
        except (APIError, APITimeoutError) as e:
            raise ExternalServiceError(f"OpenAI chat failed: {e}") from e

    async def chat_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        try:
            stream = await self._client.chat.completions.create(
                model=self._chat_model, messages=messages, stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except OpenAIRateLimit as e:
            raise RateLimitError("OpenAI rate limit") from e
        except (APIError, APITimeoutError) as e:
            raise ExternalServiceError(f"OpenAI stream failed: {e}") from e
