from fastapi import FastAPI, HTTPException

from .models import AskRequest, AskResponse, AgentRequest, AgentResponse
from .rag import retrieve, build_context, add_documents
from .agent import run_agent, stream_answer
from .websocket import router as ws_router

app = FastAPI(title="AI Assistant", version="0.1.0")
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question is empty")

    sources: list[str] = []
    if req.use_rag:
        docs, ids = await retrieve(req.question, top_k=req.top_k)
        sources = ids
        _ = build_context(docs)

    chunks: list[str] = []
    async for tok in stream_answer(req.question, use_rag=req.use_rag, top_k=req.top_k):
        chunks.append(tok)

    return AskResponse(
        answer="".join(chunks),
        sources=sources,
        session_id=req.session_id,
    )


@app.post("/agent", response_model=AgentResponse)
async def agent_endpoint(req: AgentRequest) -> AgentResponse:
    return await run_agent(req.task, max_steps=req.max_steps)


@app.post("/index")
async def index_docs(docs: list[str]):
    await add_documents(docs)
    return {"indexed": len(docs)}
