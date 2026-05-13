from fastapi import FastAPI

from .models import AskRequest, AskResponse, AgentRequest, AgentResponse
from .controllers import AskController, AgentController, IndexController
from .websocket import router as ws_router

app = FastAPI(title="AI Assistant", version="0.2.0")
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    return await AskController.handle(req)


@app.post("/agent", response_model=AgentResponse)
async def agent_endpoint(req: AgentRequest) -> AgentResponse:
    return await AgentController.handle(req)


@app.post("/index")
async def index_docs(docs: list[str]):
    return await IndexController.handle(docs)
