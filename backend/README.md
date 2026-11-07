# Integrated Engineering faculty Backend

FastAPI transport around the existing `FacultyRuntime`; RAGResponse **v1.0.0** is unchanged. This integration deliberately accepts **mock generation only**, with both remote API switches false. No private `.env`, key or consumed approval is loaded.

## Run

Python3.11.9 with the existing phase1 environment, cached model and existing faculty index are required. Only Uvicorn0.38.0 and Click8.3.0 were added for serving (`requirements-serving.txt`); no model stack upgrade or embedding rebuild.

From `D:\rag_hackathon`, in PowerShell:

```powershell
.\scripts\run_final_demo.ps1 -Component backend
```

Equivalent process environment and command:

```powershell
$env:PYTHONPATH='D:\rag_hackathon\src;D:\rag_hackathon'
$env:RAG_INDEX_PATH='D:\rag_hackathon\data\index\engineering_faculty_20261107_v1'
$env:MOCK_RULES_PATH='D:\rag_hackathon\.local\integration_execution_20261107\mock_cases.json'
$env:LLM_PROVIDER='mock'
$env:ALLOW_FREE_API_CALLS='false'
$env:ALLOW_PAID_API_CALLS='false'
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
.\.venv\Scripts\python.exe -m backend
```

Use one worker and no reload. Do not start a second process against the same Qdrant Local directory. `scripts/run_final_demo.ps1` sets all offline gates and ignores absent private fixture files, producing honest insufficient-evidence responses if no fixtures are available. In this workspace, private mock fixtures contain verified example questions; they are not general LLM generation and must remain local.

## Ownership and routes

Lifespan opens one FacultyRuntime in a worker thread and closes it once. Each `/api/chat` executes `runtime.ask(question, language, program_id, plan_version)` in the threadpool. The original RAGService callable remains question/language only. FacultyRuntime owns exact program/plan Qdrant prefilters, shared policies, missing-scope restrictions, uncertain prerequisite refusals and matching-plan graduation precedence. The legacy post-filter adapter is retained only for isolated teammate fixture tests and is not imported by production startup/routes.

- `GET /health`: actual readiness, mock mode, verified program count and local index status.
- `GET /api/programs`:15 verified Engineering choices derived from runtime metadata; no manually maintained catalog file is required. Preserves name/plan_versions and adds optional bilingual names.
- `POST /api/chat`: strict question1..2000, language ar/en, optional program_id/plan_version together; no secrets/provider/model/document-ID input. Unknown/partial scope422; unavailable runtime503; engine results200 with v1.0.0 answered/refusal/error body.
- `GET /api/sources/{document_id}`: trusted official HTTPS najah.edu URL/title and physical PDF page/article or HTML table/row. No arbitrary URL input or local file serving. This sidecar does not change RAGResponse.

Unselected scope retrieves shared regulations only. Explicit program selection retains those rules and excludes all foreign programs/versions. Plan IDs are not automatically assigned from admission dates. The empty historical backend/catalog/programs.json is no longer a production data source.

CORS permits localhost5173 and127.0.0.1:5173, without credentials. Vite can use the same-origin proxy or VITE_API_BASE_URL. Keys must never enter VITE_*.

## Tests / live limit

`python -m pytest -q` discovers RAG and Backend tests. The local execution report records real-index HTTP startup/scope/source/concurrency tests separately. Mock responses are visibly labelled in UI and public mode field. Arbitrary questions may refuse rather than invent answers.

Live browser Groq requires a NEW explicit authorization and a separately reviewed server-owned bounded provider integration. Current lifespan refuses remote/free-enabled/paid-enabled settings before opening the index. The consumed five-case grant must never be replayed. No setting alone enables live calls in this integration.
