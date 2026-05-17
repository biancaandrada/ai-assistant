# AI Assistant

Production-style FastAPI service combining **Retrieval-Augmented Generation** (OpenAI + ChromaDB) with a small **ReAct agent**. HTTP for request/response, WebSockets for token streaming.

## Features

- `POST /api/v1/ask` — RAG-grounded Q&A with citations
- `POST /api/v1/agent` — ReAct agent with pluggable tools (`search`, `calc`)
- `POST /api/v1/index` — index documents at runtime
- `WS /api/v1/ws/ask` — token-by-token streaming
- `WS /api/v1/ws/agent` — per-step streaming of agent reasoning
- `GET /api/v1/health`, `GET /api/v1/ready` — probes
- Structured logging, request IDs, global error envelope, CORS
- Docker + Compose, Makefile, pytest with fakes (no network in tests)

## Architecture

```
api/v1/routes ──► controllers ──► services ──► clients (OpenAI, Chroma)
                                     │
                                     └────────► repositories (vector store)

websocket/      same pipeline, streaming transport
tools/          pluggable agent actions (search, calc)
core/           config, logging, errors, middleware (cross-cutting)
schemas/        Pydantic DTOs (request/response contracts)
utils/          chunking and helpers
```

Each layer only depends on the layer below it.

## Quick start

```bash
cp .env.example .env             # then add your OPENAI_API_KEY

make dev                         # install runtime + dev deps
make run                         # uvicorn on :8000

# in another terminal
curl http://localhost:8000/api/v1/health
```

Swagger UI: http://localhost:8000/docs

## Loading documents

**Option A — drop files in `data/` and run the ingestion script:**
```bash
cp my_notes.txt data/
python -m scripts.ingest
```

**Option B — POST via the API:**
```bash
curl -X POST http://localhost:8000/api/v1/index \
  -H "Content-Type: application/json" \
  -d '{"documents":[{"text":"Check-in is at 3 PM."}]}'
```

**Reset the vector store:**
```bash
python -m scripts.reset_chroma --yes
```

## Asking questions

```bash
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"When is check-in?", "use_rag": true, "top_k": 3}'
```

Streaming via WebSocket:
```bash
python client.py ask "When is check-in?"
python client.py agent "What is 12 * (3 + 4)?"
```

## Docker

```bash
make docker-build
make docker-up
make docker-logs
make docker-down
```

The Compose stack persists ChromaDB in a named volume (`chroma_data`).

## Testing

```bash
make test                        # pytest, no real network calls
make lint                        # ruff
make type                        # mypy
```

Tests live in `tests/unit/` (fast, no I/O) and `tests/integration/` (real services, run sparingly).

## Configuration

Every knob is in `.env` and surfaced as a typed `Settings` field in [`app/core/config.py`](app/core/config.py). The most important ones:

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | — | Required |
| `OPENAI_CHAT_MODEL` | `gpt-4o-mini` | Chat model |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `CHROMA_PATH` | `./chroma_db` | Vector store path |
| `CHUNK_SIZE` | `1000` | Chars per chunk on ingest |
| `CHUNK_OVERLAP` | `150` | Overlap between chunks |
| `LOG_JSON` | `false` | Set `true` in prod for structured logs |
| `CORS_ORIGINS` | `["*"]` | Allowed origins |

## Project layout

```
ai-assistant/
├── app/
│   ├── main.py                  # app factory + DI wiring
│   ├── api/v1/                  # versioned HTTP routes
│   │   ├── router.py
│   │   ├── routes/{ask,agent,index,health}.py
│   │   └── deps.py
│   ├── controllers/             # thin orchestration
│   ├── core/                    # config, logging, errors, middleware
│   ├── schemas/                 # Pydantic DTOs
│   ├── services/                # business logic
│   ├── repositories/            # data-access (vector store)
│   ├── clients/                 # SDK wrappers (OpenAI, Chroma)
│   ├── tools/                   # agent tool registry
│   ├── websocket/               # streaming transport
│   └── utils/                   # chunking, etc.
├── tests/{unit,integration}/
├── scripts/{ingest,reset_chroma}.py
├── data/                        # source documents for ingestion
├── Dockerfile / docker-compose.yml
├── Makefile
├── pyproject.toml
├── requirements.txt / requirements-dev.txt
└── .env.example
```

## Extending

**Add an agent tool:**
1. Subclass `Tool` in `app/tools/your_tool.py`.
2. Register it in `_build_container` inside `app/main.py`.

**Swap the vector store:**
Replace `app/clients/chroma_client.py` and adapt `VectorRepository` — no other file touches Chroma.

**Swap the LLM provider:**
Replace `app/clients/openai_client.py` with another implementation exposing the same interface (`embed`, `chat`, `chat_stream`).

## License

MIT
