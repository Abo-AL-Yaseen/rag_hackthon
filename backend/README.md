# Backend (FastAPI transport)

HTTP adapter around the existing `rag_hackathon` library. Does **not** rebuild RAG, embeddings, or indexes. Preserves **RAGResponse v1.0.0**.

## Status snapshot

| Item | State |
|---|---|
| FastAPI app | Implemented under `backend/` |
| Verified program catalog | Empty (`backend/catalog/programs.json`) — no fabricated programs |
| Local index `data/index/` | Not present in this checkout |
| Python | Requires **3.11.x** (tested target 3.11.9). Machine may only have 3.14 — that is a blocker for running the locked venv |
| Live Groq | Disabled by default (`LLM_PROVIDER=mock`, `ALLOW_PAID_API_CALLS=false`) |
| Supabase | Optional; MVP chat does not use it |

## Architecture

```text
Client → FastAPI (CORS, validation)
       → threadpool → RAGService.ask(question, language=...)
       → ScopedAllowlistRetriever → DenseRetriever / Qdrant Local
       → provider_from_env() (mock by default)
       → RAGResponse v1.0.0 JSON
```

- Lifespan loads encoder + `open_index` **once** when `RAG_INDEX_PATH` points at an existing complete store.
- Lifespan **never** calls `ingest()`.
- Shutdown closes the Qdrant retriever.
- **Single worker only** (`uvicorn --workers 1`). Qdrant Local is not multi-process safe.

### Program / plan filtering (critical)

`RAGService.ask()` does **not** accept `program_id` / `plan_version`. `DenseRetriever.search()` has no metadata filter argument.

Backend filtering:

1. Verified catalog maps `(program_id, plan_version) → frozenset(document_ids)`.
2. Per request, a `contextvars` allowlist is bound **inside** the threadpool worker.
3. `ScopedAllowlistRetriever` oversamples from the shared index, then keeps only allowlisted `chunk.document_id` hits before generation.

This changes **retrieval evidence**, not just the prompt. Allowlists are request-scoped (no shared mutable filter object).

## Endpoints

| Method | Path | Notes |
|---|---|---|
| `GET` | `/health` | Readiness only; no LLM call. Reports index/RAG status honestly |
| `GET` | `/api/programs` | Verified catalog only; may be `[]` |
| `POST` | `/api/chat` | Body below → `RAGResponse` `1.0.0` |

### `POST /api/chat` request

```json
{
  "question": "How long are loans?",
  "language": "en",
  "program_id": null,
  "plan_version": null
}
```

- `question`: 1..2000 chars
- `language`: `ar` \| `en`
- `program_id` + `plan_version`: omit both, or provide both (must match catalog)
- Extra fields (API keys, model, index path, …) → HTTP **422**
- Engine-level answered / insufficient_evidence / error still return HTTP **200** with RAGResponse
- Transport not ready (no index) → HTTP **503** `{"detail":"rag_not_ready"}`

## Environment

See root `.env.example` Backend section. Important:

| Variable | Purpose |
|---|---|
| `RAG_INDEX_PATH` | Existing index directory with `dataset_manifest.json` |
| `PROGRAM_CATALOG_PATH` | Verified programs JSON (`verified: true`) |
| `MOCK_RULES_PATH` | Optional scripted mock rules (`synthetic`+`scripted`) |
| `LLM_PROVIDER` | Default `mock` |
| `ALLOW_PAID_API_CALLS` | Must stay `false` |
| `ALLOW_FREE_API_CALLS` / `GROQ_FREE_PLAN_CONFIRMED` | Required for any future authorized Groq free calls |
| `BACKEND_CORS_ORIGINS` | Default Vite `localhost:5173` |
| `BACKEND_LOAD_DOTENV` | Opt-in private `.env` load |

## Run (verified command shapes)

Requires Python **3.11.9** `.venv` restored from `requirements-phase1.lock.txt` plus `uvicorn` (not in the current lock — install only into the 3.11 venv after hashes are handled by the team). Do **not** install the lock into Python 3.14.

```bash
# From repo root, Git Bash, after .venv exists:
export PYTHONPATH="$(cygpath -w "$PWD/src");$(cygpath -w "$PWD")"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
export ALLOW_PAID_API_CALLS=false ALLOW_FREE_API_CALLS=false
export LLM_PROVIDER=mock
# export RAG_INDEX_PATH="data/index/<existing-dataset>"   # only if index exists
# export MOCK_RULES_PATH="data/sample/readiness/mock_rules.json"

./.venv/Scripts/python.exe -m backend
# equivalent single-worker serve:
./.venv/Scripts/python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --workers 1
```

PowerShell:

```powershell
$env:PYTHONPATH = "$((Resolve-Path .\src).Path);$((Resolve-Path .).Path)"
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:ALLOW_PAID_API_CALLS = "false"
$env:LLM_PROVIDER = "mock"
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --workers 1
```

## Tests

```bash
./.venv/Scripts/python.exe -m pytest backend/tests -q
# Full engine baseline (when 3.11 env + model cache available):
./.venv/Scripts/python.exe -m pytest -q
```

| Class | Status |
|---|---|
| Backend unit / mocked integration | Implemented under `backend/tests` |
| Real-index chat | **Blocked** until a complete local index exists |
| Remote LLM | **Blocked** — no live authorization; keep mock |
| Frontend e2e | **Blocked** — Frontend still demo/not wired to `/api/chat` |

## Groq safeguards

- Default provider is mock.
- `ALLOW_PAID_API_CALLS=false` always for this hackathon.
- Backend does not attach `RemoteCallApproval`; remote mode fails closed until an operator adds an approval object in server code (never from HTTP).
- Do not run live Groq from this transport unless free-tier gates are verified **and** the user authorizes it.

## Supabase

Project `smart-student-advisor` may exist for the team. Tables were empty at Backend audit time. MVP chat does **not** require Supabase. Do not create migrations/tables without approval. Never expose service role keys to the Frontend.

## Catalog authoring (teammates)

Only append organizer-verified entries to `backend/catalog/programs.json`:

```json
{
  "program_id": "…",
  "name": "…",
  "plan_version": "…",
  "document_ids": ["exact-index-document-id"]
}
```

`document_ids` must already exist in the authorized index. Inventing course/plan content is forbidden.

## Demo checklist

1. `/health` → honest `rag_ready` / index detail
2. `/api/programs` → `[]` or verified entries only
3. `POST /api/chat` validation 422 for bad bodies / unknown program
4. Mock chat 200 + `contract_version=1.0.0` when index+mock ready
5. Confirm `mode=mock` in demos
6. Single uvicorn worker
7. No paid API calls
