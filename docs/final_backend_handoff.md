# Ready-to-send teammate message

Copy the message below. It describes the implemented engine, not an agreement already accepted by teammates. Existing contract/schema files are unchanged.

---

Hi team,

The RAG Engine is ready for integration. The tested Arabic/English text-PDF workflow passes 178 automated tests. Backend and Frontend remain your components; the RAG Engine is a Python library with a synchronous callable, not a separately deployed server. The existing response contract is **v1.0.0**.

## 1. Imports and exact callable boundary

Use Python 3.11.9 and the existing `.venv`, with this repository's `src` on `PYTHONPATH`.

Imports:

```text
from rag_hackathon.workspace import cached_encoder, ingest, open_index
from rag_hackathon.service import RAGService, RAGPolicy
from rag_hackathon.generation.contracts import RAGResponse
from rag_hackathon.generation.providers import DeterministicMockProvider, provider_from_env
```

Implemented signatures:

```text
cached_encoder()
ingest(input_path, index_path, *, encoder=None, include_json=False, max_tokens=240, overlap=32)
open_index(index_path, *, encoder=None)
RAGService(retriever, provider, *, policy=None, diagnostics=None)
engine.ask(question: str, *, language="en") -> RAGResponse
engine(question, *, language="en") -> JSON-serializable dict
```

`ingest()` returns a dataset manifest after closing the newly built index. `open_index()` returns a `DenseRetriever`; call `retriever.close()` at shutdown. `cached_encoder()` verifies local model hashes and loads multilingual-e5-small on CPU. Reuse an encoder when building/opening stores rather than loading it per request.

Default `RAGPolicy` settings: `top_k=3`, `max_question_chars=2000`, `max_context_chars=12000`, `reject_mixed_versions=True`, `current_versions={}`, `refusal_messages={}`. These are server-owned settings, not end-user request fields. The persisted-index helper uses dense retrieval. BM25 exists separately; it is not automatically combined with dense search by `open_index()`.

The service accepts a retriever with `search(question, k) -> list[Hit]` and a provider with `generate(GenerationRequest) -> ProviderResult`. No dataset-specific routing is assumed.

## 2. Request and language handling

Request JSON for your transport:

```json
{"question":"How long is an observatory telescope reservation?","language":"en"}
```

Call `engine(request["question"], language=request.get("language", "en"))`. Use `language="ar"` for Arabic, for example `كم تستمر ورشة الروبوتات؟`; use `"en"` for English. Language is explicit, not automatically detected. Reject extra request fields in Backend. Do not accept credentials, provider/model selection, policy, source-version priorities, prompts or live-call approvals from the user.

Questions must be strings, nonblank and within the configured character limit. Invalid input produces `status="error"`, `reason="invalid_request"`; invalid language produces the safe English error response. The engine does not accept conversation/session history. Follow-up questions must be self-contained. Exact excerpts are returned in their source language; automatic translation and unrestricted paraphrased synthesis are not implemented.

## 3. Ingest documents and keep datasets separate

Backend must authorize uploads, check file size/type and actual contents, assign safe server-controlled storage paths, preserve a mapping to the supplied filename, and manage ingestion-job status. Do not use an uploaded filename as a trusted path. The engine has no upload endpoint, upload size limit, tenant registry, antivirus scanner or access-control system.

Save reviewed PDFs in an isolated input directory, then call `ingest(input_directory, fresh_index_directory, encoder=encoder)`. Directory input defaults to PDF only. Page-structured JSON is also supported explicitly; directory JSON inclusion needs `include_json=True`. OCR and robust structured-table extraction are not implemented. Inspect extracted Arabic order, numbers, tables and required physical pages before declaring ingestion successful.

Every dataset build needs a **new index directory**. Existing directories are rejected, never appended to or overwritten. The internal Qdrant collection name is `preparation`; independent local storage directories contain independent collections and share no vectors. Do not use the synthetic preparation factory or sample directory for the real organizer dataset. Duplicate document IDs/basenames are rejected. Source filenames and 1-based physical PDF page numbers are preserved.

The store contains source/configuration manifests and a checksummed chunk snapshot. Opening a changed/incompatible store fails. Preserve these files together and privately. For changed documents, build a fresh store, close/switch the owning engine deliberately, and keep the old dataset separate. Separate storage is not a substitute for Backend authorization: map each allowed dataset to its own authorized engine; do not expose arbitrary local paths to clients.

Windows Git Bash, offline sample rehearsal:

```bash
cd /d/rag_hackathon
PY="./.venv/Scripts/python.exe"
export PYTHONPATH="$(cygpath -w "$PWD/src")"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
export ALLOW_PAID_API_CALLS=false ALLOW_FREE_API_CALLS=false
export RAG_INDEX_PATH="data/index/teammate-demo-$(date +%Y%m%d-%H%M%S)"
mkdir -p .local

"$PY" scripts/local_documents.py extract --input data/sample/readiness/inputs --output .local/teammate-extraction.json
# Review extracted text before indexing a real corpus.
"$PY" scripts/local_documents.py ingest --input data/sample/readiness/inputs --index "$RAG_INDEX_PATH" --output .local/teammate-ingest.json
"$PY" scripts/local_documents.py retrieve --index "$RAG_INDEX_PATH" --question "How long is an observatory telescope reservation?" --output .local/teammate-retrieval.json
"$PY" examples/invoke_local_engine.py --index "$RAG_INDEX_PATH" --request data/sample/readiness/request_en1.json --mock-rules data/sample/readiness/mock_rules.json --output .local/teammate-answer.json
```

These scripts block outbound connections and never load `.env`. For the actual dataset after announcement, replace both input and index paths, use only organizer documents, and review extraction first. The sample mock rules are not a generator for new documents; unregistered mock questions refuse.

## 4. Minimal executable direct Python example

Run from the repository root after setting `PYTHONPATH` and `RAG_INDEX_PATH` above. Save this as a local script or run it in your integration environment. It uses the real CPU/Qdrant pipeline and explicitly scripted synthetic generation; it makes no LLM request.

Run this check as a standalone script. Its global socket patch is test-only and must not be installed in a running Backend server.

<!-- executable-example:start -->
```python
import json
import os
from pathlib import Path
from unittest.mock import patch

from rag_hackathon.workspace import open_index
from rag_hackathon.service import RAGService, RAGPolicy
from rag_hackathon.generation.providers import DeterministicMockProvider
from rag_hackathon.generation.contracts import RAGResponse

fixture = json.loads(Path("data/sample/readiness/mock_rules.json").read_text(encoding="utf-8"))
assert fixture["synthetic"] is True and fixture["scripted"] is True

with patch("socket.socket.connect", side_effect=RuntimeError("Offline example forbids network")):
    retriever = open_index(Path(os.environ["RAG_INDEX_PATH"]))
    try:
        provider = DeterministicMockProvider(fixture["rules"])
        engine = RAGService(retriever, provider, policy=RAGPolicy(top_k=3))
        payload = engine("How long is an observatory telescope reservation?", language="en")
        RAGResponse.model_validate(payload)
        assert payload["status"] == "answered" and payload["mode"] == "mock"
        print(json.dumps(payload, ensure_ascii=True, indent=2))
        # Alternative: typed = engine.ask(question, language="ar")
    finally:
        retriever.close()
```
<!-- executable-example:end -->

For real generation, inject an independently authorized provider into the same constructor. The current named factory supports `mock`, `groq`, `openrouter`, `together` and `compatible`. A credential alone does not enable calls. Groq uses `LLM_PROVIDER=groq`, `GROQ_MODEL=openai/gpt-oss-120b`, `GROQ_BASE_URL=https://api.groq.com/openai/v1`, and the private `GROQ_API_KEY`. **Keep `ALLOW_PAID_API_CALLS=false`.** Groq rejects paid-call enablement; free inference additionally requires both free-plan flags and a fresh operator-owned endpoint/model/attempt approval. None is authorized now, and previous call allowances are exhausted. No retries, model changes or paid fallbacks are automatic.

`provider_from_env()` reads process settings by default. Explicit private-file loading is `provider_from_env(env_file=Path("D:/rag_hackathon/.env"), approval=operator_approval)`; do not pass both `env` and `env_file`. Process values override the file. Do not print the environment/configuration or expose it in request fields. **The older provider paragraph in `integration_contract.md` predates Groq and its free-only gates; use the implementation and Groq review for that configuration.** The public response schema remains unchanged.

## 5. Response JSON and citations

This is a recorded, actual offline readiness fixture response (rounded measured timings), not a live LLM result:

```json
{
  "contract_version": "1.0.0",
  "answer": "The observatory telescope reservation lasts forty minutes. [S1]",
  "sources": [{
    "source_id": "S1",
    "chunk_id": "d0728cb9-b641-5ad2-914e-718a09aef33c",
    "document_id": "readiness_english",
    "document_name": "readiness_english.pdf",
    "page_number": 1,
    "supporting_excerpt": "The observatory telescope reservation lasts forty minutes.",
    "version": "unspecified"
  }],
  "claims": [{
    "text": "The observatory telescope reservation lasts forty minutes.",
    "source_ids": ["S1"]
  }],
  "status": "answered",
  "reason": "supported",
  "language": "en",
  "mode": "mock",
  "latency": {
    "retrieval_ms": 28.3233,
    "generation_ms": 0.0324,
    "validation_ms": 0.0755,
    "total_ms": 28.4741
  },
  "validation": {
    "citation_references": "verified",
    "support_check": "exact_quote",
    "semantic_faithfulness": "not_evaluated"
  }
}
```

`S1` is a response-local reference; `chunk_id` identifies the retrieved chunk. Do not cache an `S1` mapping across answers. Names, pages and excerpts come from server-owned retrieved metadata, not model-authored references. The current generator selects server-owned excerpt IDs; the engine resolves the original text and constructs citations. The strict legacy format remains accepted. Arbitrary paraphrases, translations and unsupported claims are rejected. Valid references/exact copying do not prove semantic relevance or completeness.

The normative schema is `docs/rag_response.schema.json`. Full measured examples are in `docs/evidence/phase4_contract_examples.json`. Latencies are milliseconds; total includes queue/engine overhead, so stage values need not sum exactly. API tokens/cost are not fields in this public response.

## 6. Status and error handling

| `status` | Backend / Frontend behavior |
|---|---|
| `answered` | Show the escaped answer and source cards. `reason=supported`. |
| `insufficient_evidence` | Show the localized refusal or clarification message. `sources=[]`, `claims=[]`; never show a raw draft. |
| `error` | Show the generic safe error text and use the reason code for routing/telemetry. `sources=[]`, `claims=[]`. No automatic provider retry/fallback. |

Refusal reasons: `missing_evidence`, `out_of_scope`, `false_assumption`, `ambiguous`, `conflicting_sources`, `outdated_sources`, `unsupported_claim`.

Error reasons currently used: `invalid_request`, `retrieval_error`, `invalid_citation`, `malformed_response`, `provider_timeout`, `provider_error`, `provider_authentication`, `provider_rate_limited`, `remote_calls_disabled`, `provider_configuration`. Consume `reason` as a string with a safe unknown-code fallback; the schema does not enumerate it.

Setup, provider construction, ingestion and index opening can raise exceptions before any RAG response exists. Handle them at application startup/job boundaries and return your own sanitized transport/job error; do not log raw file content, configuration, credentials or provider bodies. HTTP status mapping belongs to Backend. The optional `examples/backend_integration.py` demonstrates a FastAPI wrapper, but it is not a deployed endpoint or mandatory server. Its request-schema failures use HTTP 422. Choose and document your actual routes; no other endpoint is supplied by the engine.

## 7. Ownership and deployment

| Owner | Responsibilities |
|---|---|
| RAG Engine | PDF/page-JSON extraction, token chunking, CPU embeddings, retrieval modules, evidence prompt, provider adapters, citation/claim validation, refusal policy, response contract and evaluation tools. |
| Backend | Upload validation/storage, users/authorization, dataset-to-engine mapping, startup/shutdown, bounded job/request concurrency, HTTP transport, CORS, rate limits, secure source-file access, provider approvals, logging and deployment. |
| Frontend | Arabic RTL/English rendering, question/upload forms, loading/error/refusal states, source cards and page navigation through Backend-authorized file URLs. History UI does not create engine multi-turn support. |

Direct imports execute the engine in the **calling Python process**. Calls are synchronous and internally serialized per `RAGService`; run them in a worker thread if your Backend is async. Share one owning engine/client per Qdrant Local directory, and do not reopen that store in competing processes or multiple web workers. Directly accessing the retriever outside that owner needs your own synchronization. Cross-user RBAC and history are not implemented by the engine.

A separate engine service is possible only through a Backend-owned wrapper and transport design; there is no running standalone service to connect to. A non-Python Backend would need that wrapper. Multiple workers/stores, queueing or a vector server require a deliberate architecture choice; do not assume shared Qdrant Local supports them.

Please integrate against the existing callable/schema and use the offline fixture first. Actual-corpus evaluation, scan/table handling if required, and any new live Free-plan call need their own review. No paid service is authorized.

Thanks.
