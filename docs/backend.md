# Integrated Backend/Frontend boundary

The approved integration branch connects the team's FastAPI transport to Mahmoud's existing FacultyRuntime. See backend/README.md and scripts/run_final_demo.ps1 for exact startup. No main/source branch is pushed or modified.

Product API remains GET /health, GET /api/programs, POST /api/chat. A trusted GET /api/sources/{document_id} sidecar supplies official source locators outside the frozen RAGResponse1.0.0 schema. HTTP422 covers invalid/unknown scope;503 covers unavailable runtime. Engine answered/insufficient_evidence/error responses use200 and must be interpreted from the body.

Program/plan choices come from runtime.programs(), not backend/catalog/programs.json. Chat sends question/language/program_id/plan_version; the runtime routes exact scope while the inner RAGService retains its original callable. Scoped retrieval happens before ranking and keeps shared regulations. No program means shared regulations only. No global top40 filtering is used by the running application.

The Arabic UI now makes asynchronous HTTP requests, preserves full response/source/status/mode metadata, binds replies to originating conversation IDs, and freezes scope per request. Context changes preserve the old conversation and begin another. Citation markers link source cards; official URLs are resolved by the Backend whitelist. HTML table references are not displayed as physical PDF pages.

This branch is OFFLINE/mock only. Both API flags remain false; no private .env or live grant is loaded. Supported fixture replies are clearly marked as simulation; other questions may refuse. No historical approval is reusable. Current code must be separately adapted/reviewed under a fresh authorization before live-browser generation.
