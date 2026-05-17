"""Agent tool abstraction. Add new tools by subclassing Tool and registering."""
from abc import ABC, abstractmethod


class Tool(ABC):
    name: str
    description: str

    @abstractmethod
    async def run(self, action_input: str) -> str:
        """Execute the tool. Return a string observation for the agent."""


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def describe(self) -> str:
        """Used inside the agent system prompt."""
        return "\n".join(f"- {t.name}: {t.description}" for t in self._tools.values())

    @property
    def names(self) -> list[str]:
        return list(self._tools.keys())
