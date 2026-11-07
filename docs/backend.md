# Backend integration notes

Canonical runbook: [backend/README.md](../backend/README.md).

This document is the Frontend/RAG teammate-facing contract summary for the FastAPI transport added under `backend/`.

## Endpoints

| Method | Path | Success body |
|---|---|---|
| `GET` | `/health` | readiness JSON (not RAGResponse) |
| `GET` | `/api/programs` | `ProgramSummary[]` from verified catalog only |
| `POST` | `/api/chat` | **RAGResponse v1.0.0** |

## Chat request / response

Request:

```json
{
  "question": "string (1..2000)",
  "language": "ar|en",
  "program_id": "string|null",
  "plan_version": "string|null"
}
```

Rules:

- `extra=forbid` — no client secrets, model, index, or approval fields
- `program_id` and `plan_version` must both be omitted/null or both nonempty and catalog-known
- HTTP **422** for request-schema / unknown program failures
- HTTP **503** `{"detail":"rag_not_ready"}` when index/engine not opened
- HTTP **200** + RAGResponse for engine `answered` / `insufficient_evidence` / `error`

Response: normative schema `docs/rag_response.schema.json` (`contract_version: "1.0.0"`).

## Filtering behavior

`RAGService.ask(question, language=...)` does not take program/plan arguments. Backend applies a request-scoped document-id allowlist wrapper around the shared dense retriever (oversample → filter hits). Filtering changes retrieval evidence, not only the prompt. Concurrent requests do not share a mutable allowlist.

Catalog file: `backend/catalog/programs.json` (currently empty, `verified: true`). Do not invent programs or course mappings.

## Frontend contract gap (do not rewrite Frontend here)

Observed Frontend state:

| File | Behavior |
|---|---|
| `frontend/src/types/rag.ts` | Already mirrors RAGResponse v1.0.0 + `RAGRequest {question, language}` |
| `frontend/src/api/mockClient.ts` | Offline fixtures; comment mentions `/rag/answer` |
| `frontend/src/api/chatApi.ts` | Stub `askAdvisor` returning `status: "not_connected"` with a **different** shape (`citations`, no contract_version) |
| `frontend/src/lib/chatStore.ts` | Local demo replies; **no HTTP call** to Backend |

Suggested Frontend changes (for Frontend owner):

1. Call `POST http://127.0.0.1:8000/api/chat` (configurable base URL via Vite env).
2. Prefer `RAGResponse` from `types/rag.ts` / `mockClient` over `chatApi.ts` stub types.
3. Optionally send `program_id` + `plan_version` once a program picker exists and catalog is populated.
4. Map UI:
   - `status=answered` → show answer + source cards (`document_name`, `page_number`, `supporting_excerpt`)
   - `insufficient_evidence` → refusal text
   - `error` → generic retry; show safe `reason` only
   - HTTP 503 → “advisor offline / index not ready”
5. Keep rendering plain escaped text; do not treat filenames as filesystem links.
6. Display `mode=mock` clearly during demos.

Engine contract example path in docs remains `/rag/answer` (`examples/backend_integration.py`). This Backend deliberately exposes `/api/chat` for the product API; Frontend should target `/api/chat`.

## Supabase

Optional. `smart-student-advisor` had **no tables** at audit time. Chat MVP does not need Supabase. No migrations without approval. No service keys in Frontend.

## Blockers for READY

- Python 3.11.x + restored `.venv` / wheel cache / model cache
- Existing complete `RAG_INDEX_PATH` (never rebuild on API startup)
- Optional: verified catalog entries + Frontend wiring + authorized free-tier Groq only if explicitly approved
