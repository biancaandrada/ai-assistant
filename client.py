"""Standalone client to test the running server. Run with: python client.py"""
import asyncio
import json
import sys

import websockets


async def ask(question: str) -> str:
    async with websockets.connect("ws://localhost:8000/api/v1/ws/ask") as ws:
        await ws.send(json.dumps({"question": question, "use_rag": True, "top_k": 3}))
        full = ""
        async for msg in ws:
            evt = json.loads(msg)
            if evt["type"] == "start":
                print("[generating...]")
            elif evt["type"] == "token":
                print(evt["data"], end="", flush=True)
                full += evt["data"]
            elif evt["type"] == "end":
                print()
                return full
        return full


async def run_agent(task: str) -> None:
    async with websockets.connect("ws://localhost:8000/api/v1/ws/agent") as ws:
        await ws.send(json.dumps({"task": task, "max_steps": 5}))
        async for msg in ws:
            evt = json.loads(msg)
            if evt["type"] == "step":
                s = evt["data"]
                print(f"THOUGHT: {s['thought']}")
                print(f"ACTION:  {s['action']}")
                print(f"OBS:     {s['observation']}\n")
            elif evt["type"] == "final":
                print(f"ANSWER: {evt['data']}")
                return


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "ask"
    text = " ".join(sys.argv[2:]) or "When is check-in?"
    if mode == "agent":
        asyncio.run(run_agent(text))
    else:
        asyncio.run(ask(text))
