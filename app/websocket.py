import json
from fastapi import WebSocket, WebSocketDisconnect, APIRouter

from .agent import stream_answer, run_agent

router = APIRouter()


@router.websocket("/ws/ask")
async def ws_ask(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            raw = await ws.receive_text()
            try:
                payload = json.loads(raw)
                question = payload.get("question", "")
                use_rag = payload.get("use_rag", True)
                top_k = payload.get("top_k", 3)
            except json.JSONDecodeError:
                question, use_rag, top_k = raw, True, 3

            await ws.send_json({"type": "start"})
            async for token in stream_answer(question, use_rag=use_rag, top_k=top_k):
                await ws.send_json({"type": "token", "data": token})
            await ws.send_json({"type": "end"})
    except WebSocketDisconnect:
        return


@router.websocket("/ws/agent")
async def ws_agent(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            raw = await ws.receive_text()
            try:
                payload = json.loads(raw)
                task = payload.get("task", "")
                max_steps = payload.get("max_steps", 5)
            except json.JSONDecodeError:
                task, max_steps = raw, 5

            result = await run_agent(task, max_steps=max_steps)
            for step in result.steps:
                await ws.send_json({"type": "step", "data": step.model_dump()})
            await ws.send_json({"type": "final", "data": result.final_answer})
    except WebSocketDisconnect:
        return
