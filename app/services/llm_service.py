"""Domain operations on top of the OpenAI client.

Currently a thin pass-through, but this is where higher-level logic lives:
provider fallbacks, model routing, caching, prompt templating, etc.
"""
from typing import AsyncIterator

from ..clients.openai_client import OpenAIClient


class LLMService:
    def __init__(self, openai: OpenAIClient) -> None:
        self._openai = openai

    async def embed(self, text: str) -> list[float]:
        return await self._openai.embed(text)

    async def chat(self, messages: list[dict], *, json_mode: bool = False) -> str:
        return await self._openai.chat(messages, json_mode=json_mode)

    async def chat_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        async for tok in self._openai.chat_stream(messages):
            yield tok
