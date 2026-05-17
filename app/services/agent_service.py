"""ReAct-style mini agent. Decides which tool to call until it produces a final answer."""
import json
from typing import AsyncIterator

from ..core.config import Settings
from ..core.errors import AgentError
from ..core.logging import get_logger
from ..schemas.agent import AgentResponse, AgentStep
from ..tools.base import ToolRegistry
from .llm_service import LLMService

logger = get_logger(__name__)


def _build_system_prompt(registry: ToolRegistry) -> str:
    return (
        "You are a ReAct agent. Choose one action per step and respond with strict JSON:\n"
        '{"thought": "...", "action": "<name>|final", "action_input": "..."}\n\n'
        f"Available actions:\n{registry.describe()}\n"
        '- final: provide the user-facing answer in action_input.\n'
        "Only output the JSON, no prose."
    )


class AgentService:
    def __init__(self, settings: Settings, llm: LLMService, tools: ToolRegistry) -> None:
        self._settings = settings
        self._llm = llm
        self._tools = tools

    async def run(self, task: str, max_steps: int) -> AgentResponse:
        max_steps = min(max_steps, self._settings.agent_max_steps_hard_cap)
        history: list[dict] = [
            {"role": "system", "content": _build_system_prompt(self._tools)},
            {"role": "user", "content": task},
        ]
        steps: list[AgentStep] = []

        for step_idx in range(max_steps):
            raw = await self._llm.chat(history, json_mode=True)
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                raise AgentError(f"agent returned non-JSON at step {step_idx}: {e}") from e

            thought = data.get("thought", "")
            action = data.get("action", "final")
            action_input = data.get("action_input", "")

            if action == "final":
                steps.append(AgentStep(thought=thought, action="final", observation=action_input))
                return AgentResponse(final_answer=action_input, steps=steps)

            tool = self._tools.get(action)
            observation = await tool.run(action_input) if tool else f"unknown tool: {action}"
            steps.append(AgentStep(
                thought=thought,
                action=f"{action}({action_input})",
                observation=observation,
            ))
            history.append({"role": "assistant", "content": raw})
            history.append({"role": "user", "content": f"Observation: {observation}"})

        return AgentResponse(final_answer="Step limit reached.", steps=steps)

    async def stream_steps(self, task: str, max_steps: int) -> AsyncIterator[dict]:
        """Same as run() but yields each step as a dict (for WebSocket streaming)."""
        result = await self.run(task, max_steps)
        for step in result.steps:
            yield {"type": "step", "data": step.model_dump()}
        yield {"type": "final", "data": result.final_answer}
