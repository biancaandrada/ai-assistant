"""Controller for the ReAct agent."""
from fastapi import HTTPException

from ..models import AgentRequest, AgentResponse
from ..agent import run_agent


class AgentController:
    """Orchestrates the /agent flow."""

    @staticmethod
    def _validate(req: AgentRequest) -> None:
        if not req.task.strip():
            raise HTTPException(status_code=400, detail="task is empty")
        if req.max_steps < 1 or req.max_steps > 20:
            raise HTTPException(status_code=400, detail="max_steps must be between 1 and 20")

    @classmethod
    async def handle(cls, req: AgentRequest) -> AgentResponse:
        cls._validate(req)
        return await run_agent(req.task, max_steps=req.max_steps)
