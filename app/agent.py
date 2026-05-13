import os
import json
from typing import AsyncIterator
from openai import AsyncOpenAI
from dotenv import load_dotenv

from .models import AgentResponse, AgentStep
from .rag import retrieve, build_context

load_dotenv()

_openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


async def _tool_search(query: str, top_k: int = 3) -> str:
    docs, _ = await retrieve(query, top_k=top_k)
    return build_context(docs) or "No results."


async def _tool_calc(expression: str) -> str:
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"calc error: {e}"


TOOLS = {"search": _tool_search, "calc": _tool_calc}

SYSTEM = """You are a mini ReAct agent. At each step output JSON:
{"thought": "...", "action": "search|calc|final", "action_input": "..."}
- search: query the knowledge base
- calc: evaluate a math expression
- final: provide the final answer in action_input
Only output the JSON, nothing else."""


async def run_agent(task: str, max_steps: int = 5) -> AgentResponse:
    history = [{"role": "system", "content": SYSTEM},
               {"role": "user", "content": task}]
    steps: list[AgentStep] = []

    for _ in range(max_steps):
        resp = await _openai.chat.completions.create(
            model=MODEL, messages=history, response_format={"type": "json_object"}
        )
        raw = resp.choices[0].message.content or "{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return AgentResponse(final_answer=raw, steps=steps)

        action = data.get("action", "final")
        action_input = data.get("action_input", "")
        thought = data.get("thought", "")

        if action == "final":
            steps.append(AgentStep(thought=thought, action="final", observation=action_input))
            return AgentResponse(final_answer=action_input, steps=steps)

        tool = TOOLS.get(action)
        observation = await tool(action_input) if tool else f"unknown tool: {action}"
        steps.append(AgentStep(thought=thought, action=f"{action}({action_input})", observation=observation))
        history.append({"role": "assistant", "content": raw})
        history.append({"role": "user", "content": f"Observation: {observation}"})

    return AgentResponse(final_answer="Step limit reached.", steps=steps)


async def stream_answer(question: str, use_rag: bool = True, top_k: int = 3) -> AsyncIterator[str]:
    messages = [{"role": "system", "content": "You are a helpful assistant. Cite sources as [1], [2] when context is given."}]
    if use_rag:
        docs, _ = await retrieve(question, top_k=top_k)
        ctx = build_context(docs)
        if ctx:
            messages.append({"role": "system", "content": ctx})
    messages.append({"role": "user", "content": question})

    stream = await _openai.chat.completions.create(model=MODEL, messages=messages, stream=True)
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
