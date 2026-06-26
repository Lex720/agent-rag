# agent-rag

RAG agent that answers questions about API integrations from an OpenAPI specification.
Built as a portfolio project to demonstrate RAG pipeline design, LLM API integration, and GCP deployment.

## Architecture

```
Client
  │
  ▼
POST /v1/query  ──┐
POST /v2/query  ──┤  FastAPI (Cloud Run)
                  │
                  ▼
            Guardrails (input)
                  │
                  ▼
            Retriever
            (embed query → pgvector similarity search → top-5 chunks)
                  │
                  ▼
            Prompt builder
            (system prompt + context chunks + history + query)
                  │
                  ▼
            Claude API (claude-haiku-4-5)
                  │
                  ▼
            Guardrails (output)
                  │
                  ▼
            { answer, history, sources }


Ingestion (offline script, run once):

                         ┌─ v1 ─ embedder.py (Voyage AI SDK) ─ loader.py (SQLAlchemy) ─┐
openapi.json → parser.py ┤                                                               ├─ PostgreSQL
                         └─ v2 ─ loader_llama.py (LlamaIndex embeds + loads) ───────────┘
```

## Stack

| Component | Technology | Why |
|---|---|---|
| LLM | Claude API (`claude-haiku-4-5`) | Cost-efficient, sufficient quality for Q&A over structured docs |
| Embeddings | Voyage AI `voyage-4-lite` (1024 dims) | Recommended by Anthropic for Claude stacks; 200M token free tier covers this use case |
| Vector store | Supabase — Postgres + pgvector | Managed Postgres with native vector search; free tier; no extra infra |
| API | FastAPI + Python 3.13 | Fast iteration, auto OpenAPI docs |
| Migrations | Alembic | Version-controlled schema; `alembic upgrade head` replaces any manual SQL step |
| Secrets | GCP Secret Manager | API keys injected as env vars by Cloud Run at runtime; never in code |
| Deploy | GCP Cloud Run | Serverless, pay-per-use, `max-instances=1` for demo cost control |

## Project structure

```
agent-rag/
├── src/
│   ├── domain/query/          # Entities, repository interfaces, QueryAsk ABC
│   ├── application/query/     # usecase_manual.py (v1), usecase_llama.py (v2), service.py
│   ├── infrastructure/        # Adapters: voyage, postgres, claude, guardrails, config
│   └── presentation/api/      # FastAPI app, routers (v1, v2), DTOs
├── ingest/                    # Offline ingestion scripts
│   ├── parser.py              # Shared: OpenAPI → chunks (one per operation)
│   ├── run.py                 # Orchestrator: --pipeline v1|v2|both
│   ├── v1/                    # Manual pipeline: Voyage AI SDK + SQLAlchemy
│   └── v2/                    # LlamaIndex pipeline: embeds + loads internally
├── alembic/                   # Database migrations
│   └── versions/
│       └── 65ade98eb90d_initial_schema.py
├── data/                      # Place openapi.json here
├── tests/unit/                # Unit tests (no external dependencies)
├── Dockerfile                 # Multi-stage Alpine build
├── alembic.ini
└── pyproject.toml
```

## Chunking strategy

**Operation-level semantic chunking** (schema-aware).

Each chunk represents one OpenAPI operation (path + method), serialized as plain text:

```
POST /users/login
Summary: Authenticate user
Description: Validates credentials and returns a JWT token.
Parameters: username (body, required, string) | password (body, required, string)
Responses: 200 - JWT token | 401 - Invalid credentials | 422 - Validation error
```

**Overlap: zero.** Each operation is semantically self-contained. Overlap exists to recover
context cut at arbitrary chunk boundaries — unnecessary here because boundaries are semantic
(one operation = one chunk), not positional.

## Two implementations: v1 vs v2

Both endpoints share the same domain layer, DTOs, guardrails, and Supabase database.
They differ only in how the retrieval and generation pipeline is assembled.

| | v1 — manual (`/v1/query`) | v2 — LlamaIndex (`/v2/query`) |
|---|---|---|
| Ingestion | Voyage AI SDK + SQLAlchemy direct insert | LlamaIndex `VectorStoreIndex.from_documents()` |
| Vector store | SQLAlchemy + raw `<=>` cosine query | `PGVectorStore` + LlamaIndex retriever |
| Prompt / context | `_build_messages()` — explicit injection | `ContextChatEngine` — managed internally |
| LLM | `anthropic` SDK direct | LlamaIndex `Anthropic` wrapper |
| Guardrails | applied at route level | applied at route level (same component) |
| Pipeline visibility | every step explicit and debuggable | abstracted by the framework |

**v1** is the right choice when you want full control: the retrieval query, prompt structure,
and token usage are all visible. Easier to debug, profile, and optimize.

**v2** shows how LlamaIndex reduces boilerplate at the cost of abstraction. Useful as a
starting point when you want to layer in rerankers, hybrid search, or query transformations.

## Guardrails

`src/infrastructure/guardrails/guardrails.py` — a standalone component applied at the route
level, before the query reaches the pipeline and before the response reaches the client.

**Input validation (`validate_input`):**
1. Length ≤ 500 characters.
2. Prompt injection detection: regex patterns for known jailbreak phrases
   (`ignore previous instructions`, `you are now`, `new instructions:`, etc.).
3. Domain check: at least one API/integration keyword must be present in the query.
   Off-domain requests (general knowledge, unrelated topics) are rejected with a 400.

**Output sanitization (`validate_output`):**
1. System prompt leak detection: 4-gram matching against the system prompt. If any
   4-consecutive-word sequence from the system prompt appears verbatim in the response, the
   request is rejected.
2. Secret redaction: regexes for known API key formats (Anthropic `sk-ant-*`, OpenAI `sk-*`,
   Google `AIza*`) are replaced with `[REDACTED]`.

The component has no external dependencies and is fully unit-testable in isolation.
See `tests/unit/infrastructure/test_guardrails.py`.

## Stateless conversation

The server stores no session state. The client sends `history` with each request and receives
an updated `history` in the response — mirroring how the Claude API `messages[]` array works
natively. This approach survives Cloud Run cold starts with no shared state issues.

```json
// Request 1
{ "query": "How does the auth endpoint work?", "history": [] }

// Response 1
{
  "answer": "The POST /auth/login endpoint...",
  "history": [
    { "role": "user", "content": "How does the auth endpoint work?" },
    { "role": "assistant", "content": "The POST /auth/login endpoint..." }
  ],
  "sources": ["POST /auth/login"]
}

// Request 2 — pass history from response 1
{
  "query": "What headers does it require?",
  "history": [
    { "role": "user", "content": "How does the auth endpoint work?" },
    { "role": "assistant", "content": "The POST /auth/login endpoint..." }
  ]
}
```

History is capped at 20 messages (10 turns) to bound token usage per request.

## Local setup

### Option A — Docker (recommended)

The Docker setup includes a local Postgres container with pgvector pre-installed
(`pgvector/pgvector:pg16`). The `api` and `migrate` services always connect to this local
container — `DB_URL` is hardcoded in `docker-compose.yaml` and never reads from
`.env`, so you cannot hit Supabase by accident during local development.

Only `VOYAGE_API_KEY` and `ANTHROPIC_API_KEY` are required in `.env` for Docker.

```bash
# 1. Configure environment (only API keys needed — DB is local)
cp .env.example .env
# Fill in: VOYAGE_API_KEY, ANTHROPIC_API_KEY

# 2. Build images
docker compose build

# 3. Start postgres and run migrations
docker compose up -d postgres
docker compose run --rm migrate

# 4. Place your OpenAPI spec and run ingestion
#    The ingest scripts run locally and connect to postgres via localhost:5432
cp your-openapi.json data/openapi.json
DB_URL=postgresql://postgres:postgres@localhost:5432/agent_rag \
  python -m ingest.run --input data/openapi.json --pipeline both

# 5. Start the API
docker compose up api

# 6. Smoke test
curl -X POST http://localhost:8080/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How does the authentication endpoint work?", "history": []}'
```

### Option B — Local Python

```bash
# 1. Install dependencies
poetry install --with test,lint

# 2. Configure environment
cp .env.example .env
# Fill in: VOYAGE_API_KEY, ANTHROPIC_API_KEY, DB_URL

# 3. Run database migrations
#    Creates the chunks table, ivfflat index, and enables pgvector.
#    Requires the postgres user (default on Supabase) for CREATE EXTENSION.
alembic upgrade head

# 4. Place your OpenAPI spec and run ingestion
cp your-openapi.json data/openapi.json
python -m ingest.run --input data/openapi.json --pipeline both
# --pipeline v1   runs only the manual pipeline (chunks table)
# --pipeline v2   runs only the LlamaIndex pipeline (chunks_llama table)
# --pipeline both runs both (default)

# 5. Start the API
uvicorn src.presentation.api.main:api --reload

# 6. Smoke test
curl -X POST http://localhost:8000/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How does the authentication endpoint work?", "history": []}'
```

## Tests

```bash
# Docker
docker compose run --rm unit-tests

# Local
pytest tests/unit -v
```

No e2e tests: external dependencies (LLM, vector DB) are non-deterministic and require live
credentials. Integration is validated manually with the smoke test above.

## Voyage AI free tier and rate limiting

The `voyage-4-lite` free tier has two simultaneous limits:

| Limit | Value |
|---|---|
| Requests per minute (RPM) | 3 |
| Tokens per minute (TPM) | 10,000 |

Both pipelines handle this explicitly.

**v1 — `ingest/v1/embedder.py`:** chunks are sent in batches of 30 (~3,600 tokens each, safely under 10K TPM). A `time.sleep(21)` is inserted between batches to stay under 3 RPM. With 84 chunks this adds ~42 seconds of pause during ingestion.

**v2 — `src/infrastructure/llamaindex/rag_client.py`:** LlamaIndex's `VoyageEmbedding` has an internal sub-batch loop that feeds the Voyage SDK, which has its own default batch size of 128 — large enough to send all 84 chunks in a single HTTP request regardless of LlamaIndex's `embed_batch_size`. To fix this, `_RateLimitedVoyageEmbedding` subclasses `VoyageEmbedding`, sets `embed_batch_size=20`, and overrides `_get_text_embeddings()` to sleep 21 seconds before each call after the first. `PrivateAttr` is required to track call count because `VoyageEmbedding` is a Pydantic model.

```python
class _RateLimitedVoyageEmbedding(VoyageEmbedding):
    _batch_call_count: int = PrivateAttr(default=0)

    def _get_text_embeddings(self, texts):
        if self._batch_call_count > 0:
            time.sleep(21)  # 3 RPM free tier
        self._batch_call_count += 1
        return super()._get_text_embeddings(texts)
```

These sleeps exist only because of the free tier. Adding a payment method in the Voyage dashboard raises limits to 2,000 RPM / 6M TPM, at which point both `_BATCH_SLEEP_SECONDS` and the sleep in `_get_text_embeddings` can be removed.

## Configuration

All optional — defaults are production-ready for a demo workload.

| Variable | Default | Description |
|---|---|---|
| `LLM_MODEL` | `claude-haiku-4-5-20251001` | Claude model ID |
| `LLM_MAX_TOKENS` | `1024` | Hard cap on response tokens; bounds cost and latency |
| `EMBED_MODEL` | `voyage-4-lite` | Voyage AI embedding model; must match between ingestion and query |
| `EMBED_DIM` | `1024` | Embedding dimensions; must match the model and the pgvector index |

> **Note on service availability:** The service is not left running permanently to avoid unnecessary token costs. If you want to try it live, reach out and I will spin it up on demand. The code, README, and documented architecture are the primary deliverable of this portfolio.
