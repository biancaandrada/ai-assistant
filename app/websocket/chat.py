"""WebSocket transport for streaming Q&A and agent runs.

Lives outside `api/routes/` because WebSockets aren't HTTP — they have their
own connection lifecycle, framing, and error model. Mounted under the same
versioned prefix in main.py.
"""
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError as PydanticValidationError

from ..core.errors import AppError
from ..core.logging import get_logger
from ..schemas.agent import AgentRequest
from ..schemas.ask import AskRequest

logger = get_logger(__name__)
router = APIRouter()


def _parse(raw: str, model_cls, fallback_field: str):
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        payload = {fallback_field: raw}
    return model_cls(**payload)


@router.websocket("/ws/ask")
async def ws_ask(ws: WebSocket):
    """Token-by-token streaming Q&A.

    Client sends JSON {question, use_rag?, top_k?}.
    Server emits: {type:"start"} → many {type:"token", data} → {type:"end"}.
    Connection stays open for multiple turns.
    """
    await ws.accept()
    ctrl = ws.app.state.ask_controller
    try:
        while True:
            raw = await ws.receive_text()
            try:
                req = _parse(raw, AskRequest, "question")
            except PydanticValidationError as e:
                await ws.send_json({"type": "error", "data": e.errors()})
                continue

            await ws.send_json({"type": "start"})
            try:
                async for event in ctrl.stream_events(req):
                    # Forward sources + tokens as they're produced
                    await ws.send_json(event)
            except AppError as e:
                await ws.send_json({"type": "error", "data": e.to_dict()})
            await ws.send_json({"type": "end"})
    except WebSocketDisconnect:
        return


@router.websocket("/ws/agent")
async def ws_agent(ws: WebSocket):
    """Streams each ReAct step as it completes, then a final answer."""
    await ws.accept()
    ctrl = ws.app.state.agent_controller
    try:
        while True:
            raw = await ws.receive_text()
            try:
                req = _parse(raw, AgentRequest, "task")
            except PydanticValidationError as e:
                await ws.send_json({"type": "error", "data": e.errors()})
                continue

            try:
                async for event in ctrl.stream(req):
                    await ws.send_json(event)
            except AppError as e:
                await ws.send_json({"type": "error", "data": e.to_dict()})
    except WebSocketDisconnect:
        return
