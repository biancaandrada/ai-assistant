import json
from fastapi import WebSocket, WebSocketDisconnect, APIRouter, HTTPException

from .models import AskRequest, AgentRequest
from .controllers import AskController, AgentController

router = APIRouter()


def _parse_ask(raw: str) -> AskRequest:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        payload = {"question": raw}
    return AskRequest(**payload)


def _parse_agent(raw: str) -> AgentRequest:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        payload = {"task": raw}
    return AgentRequest(**payload)


@router.websocket("/ws/ask")
async def ws_ask(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            raw = await ws.receive_text()
            try:
                req = _parse_ask(raw)
            except Exception as e:
                await ws.send_json({"type": "error", "data": str(e)})
                continue

            await ws.send_json({"type": "start"})
            try:
                async for token in AskController.stream(req):
                    await ws.send_json({"type": "token", "data": token})
            except HTTPException as e:
                await ws.send_json({"type": "error", "data": e.detail})
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
                req = _parse_agent(raw)
            except Exception as e:
                await ws.send_json({"type": "error", "data": str(e)})
                continue

            try:
                result = await AgentController.handle(req)
            except HTTPException as e:
                await ws.send_json({"type": "error", "data": e.detail})
                continue

            for step in result.steps:
                await ws.send_json({"type": "step", "data": step.model_dump()})
            await ws.send_json({"type": "final", "data": result.final_answer})
    except WebSocketDisconnect:
        return
