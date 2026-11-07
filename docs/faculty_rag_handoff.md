# An-Najah Engineering faculty RAG handoff

This is Mahmoud's RAG-only work. It does not merge or replace the team's Backend or Frontend. The original `RAGService.ask(question, language=...)` and `RAGResponse` contract **v1.0.0** remain unchanged.

## Validated state

- 15 official-directory Engineering program plans; 3,832 local indexed chunks.
- 1,890 program/course records, 892 distinct course codes and 22 shared regulation clauses. Arabic/English records are separately indexed.
- Latest full local regression: **226 passing tests**. Required evidence available at top-5 for **45/45** frozen answerable questions; this is a curated retrieval result, not whole-corpus answer accuracy.
- The authorized five-case live batch made **four** Groq Free inference attempts: Civil plan2021-1 course10871112=3 credits; Geomatics plan2025-1 same code=2; Computer plan2021-1 graduation=162; the verified withdrawal regulation. All four answers passed source/relevance review. The uncertain Computer prerequisite case refused locally without an API call.
- That authorization is consumed. Publishing code grants **no new live calls**. Private approvals, model usage records, source excerpts and actual call reports are not published here.
- No embeddings or index rebuild is needed for integration. Nine handbook/plan graduation discrepancies and 300 flagged course records remain documented locally; unsupported relationships must remain uncertain. A blank prerequisite cell does not mean no prerequisite.

## Runtime and ownership

```python
from rag_hackathon.faculty_runtime import FacultyRuntime

# At process startup, once. Provider defaults to an empty offline mock.
runtime = FacultyRuntime.open(index_path, provider=authorized_or_offline_provider)
try:
    answer = runtime.ask(
        "ما عدد الساعات المعتمدة للمساق 10871112؟",
        language="ar", program_id="civil-engineering", plan_version="2021-1",
    )
    payload = answer.model_dump(mode="json")  # RAGResponse v1.0.0
finally:
    runtime.close()  # At process shutdown, not after every HTTP request.
```

Use one model/index/RAGService owner per process. Backend should initialize/close it once through lifespan and run blocking calls in its worker threadpool. Do not open one Qdrant Local directory in multiple workers/processes. Request-local ContextVars carry immutable scope selection; do not mutate a shared retriever per request.

`ScopedIndex` verifies scope/chunk/manifest bindings and filters the Qdrant query **before ranking**. Exact course identifiers retain their meaning within the selected program/version, including Arabic decimal digits. Selected programs retain shared academic regulations; unselected context retrieves shared regulations only. Unknown/partial/conflicting plan selection refuses. `workspace.open_index()` refuses this mixed faculty dataset unless used through the scoped owner.

Explicit official study plans take precedence for their own course/graduation totals. This does not assign a plan to a student intake. FacultyRuntime refuses ambiguous AND/OR/color/duplicate prerequisite semantics and blank prerequisite cells before generation. `runtime.programs()` exposes validated scope choices; `runtime.source_locator(document_id)` resolves trusted URLs, physical PDF pages, HTML table/row and articles. HTML engine page1 is not a physical PDF page. Keep external source resolution outside the frozen response schema.

## Local-only prerequisites

The Git branch intentionally excludes these runtime assets:

| Material | Existing owner-workspace location |
|---|---|
| Qdrant faculty index and bound manifests | `D:\rag_hackathon\data\index\engineering_faculty_20261107_v1` |
| Processed faculty data and frozen inputs | `D:\rag_hackathon\data\processed\engineering_faculty_20261107` |
| Cached source HTML | `D:\rag_hackathon\data\raw\engineering_faculty_20261107` |
| Reused handbook/source evidence | `data/raw/engineering_mvp_20261107`, `data/processed/engineering_mvp_20261107` |
| CPU multilingual E5 model | `D:\rag_hackathon\models\multilingual-e5-small` |
| Python3.11.9 environment / wheel cache | `.venv`, `.cache` |
| Offline reference packs and earlier evidence | `.local/engineering_faculty_20261107`, `.local/final_qa_20261107`, `.local/final_integration_20261107` |
| Consumed live grant and call records | `.local/groq_faculty_five_20261107` — never reuse or publish |
| Private provider key | Ignored `.env` or private process environment; never echo or copy into Vite |

A fresh clone requires an authorized local restoration of these assets. Do not infer a redistribution license or upload the university sources/dataset just because this authored code is public. The runtime reads scope metadata from the local index; no generated academic dataset is added to this commit.

## Offline validation

From `D:\rag_hackathon` with the existing environment and local assets:

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
$env:ALLOW_FREE_API_CALLS='false'
$env:ALLOW_PAID_API_CALLS='false'
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\check_faculty_integration.py --output .local\NEW_offline_http_check
.\.venv\Scripts\python.exe scripts\faculty\evaluate_faculty.py
```

The HTTP check is an in-process FastAPI **handoff harness**, not the teammate application or a browser deployment. `examples/faculty_backend_handoff.py` refuses live settings and owns exactly one runtime. `config/faculty_offline.env.example` contains non-secret process settings; no `.env` is loaded automatically. Uvicorn is not bundled or installed by this work.

The faculty replay creates a new ignored output directory, uses cached embeddings and scoped retrieval, and exercises citations with an explicitly scripted provider. It does not edit index manifests or establish general LLM accuracy. Historical Q52 expects a conflict under the conservative view; an explicit selected-plan total and unassigned-intake ambiguity are separately tested by the runtime/HTTP checks.

## Preserved authored dataset workflow

`scripts/faculty/` preserves the reviewed collection, DOM/table extraction, index construction and evaluation code. Outputs remain in ignored `data/` and `.local/` directories. No source collection or dataset authoring is needed now:

- `html_tables.py`: authored DOM-order parser; whitespace collapsing, no Arabic reversal.
- `collect_faculty.py`: historical bounded public-source acquisition. Requires explicit `--collect-public`; do not run without new collection authorization.
- `build_faculty.py`: bilingual table extraction, exact codes/credits, source locators and explicit/unknown prerequisite operators. Requires `--rebuild-reviewed-local-dataset`; depends on existing reviewed handbook/policy inputs. Do not rerun over the validated dataset casually. The small numeric handbook cross-check constants are review logic, not a license to redistribute source material.
- `index_faculty.py`: uses the existing engine and cached model; rejects an existing destination. The current default destination already exists and will be refused. Do not run it for integration.
- `evaluate_faculty.py`: read-only index replay against local reviewed data; new private output directory on each invocation.

## Groq safety and later integration

`scripts/evaluate_faculty_live.py` defaults to an offline payload preflight. The explicit five-case mode requires `--max-attempts 5` and the verified L01/L02/L05/L07/L10 scope/reference bindings. Both provider approval consumption and a separate HTTP-send boundary enforce the ceiling. Wrong endpoint/model, a sixth request, errors or consumed state fail closed. No retries, redirects, provider/model fallback or paid enablement. Calls are paced31 seconds apart to respect Free limits; elapsed timings include pacing.

Live operation requires a NEW operator attestation of a non-billable Groq Free path, exact model/endpoint/settings, private key and fresh plan-bound approval. Local flags alone do not verify billing. `ALLOW_PAID_API_CALLS` must remain false. Do not reuse the published synthetic runner's historical authorization or the consumed faculty grant. The prepared private reference/approval files are dependencies, not committed credentials or authorization.

Teammate integration remains a separate approved task: retain their HTTP/UI ownership, connect their lifespan/routes to this runtime, expose a validated catalog, send program/plan metadata, render source cards/statuses, and install only approved serving/build dependencies. The audited teammate implementation currently calls bare open_index, post-filters global candidates, has an empty catalog and a demo-only UI. Do not merge these gaps into the RAG-only publication.
