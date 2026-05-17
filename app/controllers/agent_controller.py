from typing import AsyncIterator

from ..schemas.agent import AgentRequest, AgentResponse
from ..services.agent_service import AgentService


class AgentController:
    def __init__(self, agent: AgentService) -> None:
        self._agent = agent

    async def handle(self, req: AgentRequest) -> AgentResponse:
        return await self._agent.run(req.task, max_steps=req.max_steps)

    async def stream(self, req: AgentRequest) -> AsyncIterator[dict]:
        async for event in self._agent.stream_steps(req.task, max_steps=req.max_steps):
            yield event
