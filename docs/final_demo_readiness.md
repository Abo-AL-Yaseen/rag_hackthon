# Final Engineering advisor readiness — November 7, 2026

The actual application is a React/TypeScript Frontend, FastAPI Backend and one
FacultyRuntime over the existing 3,832-chunk local index. There are 15 distinct
program identities currently available in the system. This count is derived
from runtime metadata, not a hardcoded list or a count of plan versions.

## Measured final checks

| Check | Actual result |
|---|---|
| Python regression, `tests backend/tests` | 278 passed; one existing Starlette deprecation warning |
| Frontend store/unit tests | 10 passed |
| TypeScript and Vite production build | PASS |
| Actual frontend store → Vite HTTP → FastAPI → faculty runtime | 40/40 expected behavior checks passed |
| Scoped course language matrix, Arabic/English input and selected output | 4/4 answered in selected language from bilingual source rows |
| Attendance, Arabic selected, Arabic or English input | Answered from handbook Article 10 conditions |
| Attendance, English selected | Safe English refusal: verified English policy evidence unavailable |
| Catalog list/count, five question forms × two selected languages | 10/10; 15 programs, source metadata citation and official plan links |
| Natural Palestinian attendance, five forms × selected/unselected program | 10/10; Article 10/ب، ج، د supplied together |
| Clarification, missing evidence, out-of-scope, uncertain prerequisites | Correct distinct reasons, selected-language text and no misleading citations |
| Actual HTTP 422 errors via frontend store | Correct Arabic/English error text |
| Manual visual browser smoke | NOT RUN: computer-use inventory exposed no enabled browsers |

The 40 HTTP checks include expected refusals/errors. They are not 40 generated
LLM answers, nor a whole-corpus accuracy metric. Actual questions, requests,
responses, source locators and timings are saved privately under
`.local/final_improvements_20261107/`; the reproducible HTTP runner is
`frontend/tests/finalHttpSmoke.mjs`. No exact-question answer rules were added.

## What changed

- Selected output language is passed through the actual frontend store/API;
  HTTP errors, pending/recovered requests and refusals respect that selection.
- Attendance retrieval prioritizes the existing shared Article 10 limit,
  unexcused-consequence and accepted-excuse clauses within the allowed scope.
  This fixes semantic coverage for dialect and English input without changing
  source facts, building embeddings or widening program/version access.
- The runtime catalog deduplicates program IDs, retains verified bilingual
  names and cites a clearly labeled metadata view. Its page number is an
  internal metadata locator, never presented as a university PDF page. Official
  plan references are exposed separately; no official catalog URL is fabricated.
- The root README describes the actual application, local dependencies,
  startup/settings, limitations, official source links and AI assistance.

## English and live-provider limits

Source quotes remain exact. Bilingual study-plan rows support the four language
combinations. The indexed shared regulations currently have Arabic evidence
only, so local extractive mode cannot give a verified English synthesis. It
returns an English explanation without fabricated translations or citations.

The web Backend remains deliberately offline-only and rejects enabled remote
settings. The existing Groq adapter and dedicated evaluator support model/URL
binding, no retries/fallback, paid-call prohibition and bounded inference
attempts. Previous authorization is consumed; changed code requires fresh
bindings. No new Groq calls were made during these improvements.

Live-browser generation still needs new explicit operator authorization and
Free/non-billable attestation, server-only secrets, a persistent bounded attempt
ledger wired into Backend lifespan, fail-closed tests and an authorized live
evaluation. It is **not active** or certified by these offline checks.

## Submission and reproduction

GitHub is private. No judge identity/access grant was supplied, so judge access
cannot be confirmed from the owner's authenticated session. A source-only ZIP
can be produced from the verified commit for the owner to deliver. No recipient
has been contacted automatically and no repository visibility was changed.

Another machine must restore authorized local index/manifests, cached model and
dependencies. Raw sources/processed data remain local and may need separate
permission to transfer. Neither Git nor the source ZIP is a self-contained
faculty demo bundle. See the root README for exact setup and source links.
