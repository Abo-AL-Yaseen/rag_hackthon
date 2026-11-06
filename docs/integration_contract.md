# RAG engine integration contract v1.0.0

This is the engine owner's concrete contract for Backend/Frontend review. No teammate acceptance or external communication is claimed. The callable and response schema are implemented and tested. No existing Backend/Frontend file is modified; `examples/backend_integration.py` is an optional adapter example only.

## Callable boundary

```python
from rag_hackathon.service import RAGService, RAGPolicy
from rag_hackathon.generation.providers import provider_from_env

# Use the team's initialized/authorized retriever, not the synthetic preparation factory.
provider = provider_from_env()  # defaults to conservative offline mock
engine = RAGService(retriever, provider, policy=RAGPolicy(top_k=3))

response_model = engine.ask("Question text", language="en")  # Pydantic RAGResponse
payload = engine("نص السؤال", language="ar")                # JSON-serializable dict
```

The engine takes a retriever with `search(question, k) -> list[Hit]` and a provider with `generate(GenerationRequest) -> ProviderResult`. A Hit uses the existing Phase 1 immutable Chunk, including source filename, 1-based page, ID, text and version. No challenge-specific routing is built into the engine. The explicitly synthetic `build_preparation_service()` factory is for offline demonstration/evaluation only.

Backend owns lifecycle and authorization: initialize a single model/retriever/engine at startup, prefilter allowed documents, close the Qdrant client at shutdown, and handle auth, CORS, request limits, deployment and logging. This service serializes calls to its CPU/Qdrant owner. Run the blocking callable in a worker thread; the example uses `run_in_threadpool`. Do not open the same Qdrant Local directory from multiple processes. Multiple workers require separate stores/appropriate server architecture. This engine does not implement per-user RBAC or history.

Imports assume the repository's `src` is on the application's Python path. From this checkout in PowerShell: `$env:PYTHONPATH = (Resolve-Path ./src).Path`. CLI scripts/tests configure their own path. No additional package install is required in the existing `.venv`.

## Request JSON

```json
{"question":"How do I recover my account?","language":"en"}
```

`question` must be nonempty and at most 2,000 characters by default; language is `ar` or `en` (default `en`). The example rejects extra fields; credentials, provider selection, approval flags, source-version priorities and system prompts must never be accepted from an end-user request. Whitespace-only input is an engine `invalid_request`. The example transport returns HTTP 422 for request-schema failures; Backend may adopt a different documented transport mapping.

## Response JSON

Normative machine-readable schema: [rag_response.schema.json](rag_response.schema.json). Actual generated offline examples are in [phase2_contract_examples.json](evidence/phase2_contract_examples.json).

```json
{
  "contract_version":"1.0.0",
  "answer":"Loans last twelve days. [S1]",
  "sources":[{
    "source_id":"S1",
    "chunk_id":"<retrieved chunk ID>",
    "document_id":"library",
    "document_name":"synthetic_library.json",
    "page_number":1,
    "supporting_excerpt":"Loans last twelve days.",
    "version":"fixture"
  }],
  "claims":[{"text":"Loans last twelve days.","source_ids":["S1"]}],
  "status":"answered",
  "reason":"supported",
  "language":"en",
  "mode":"mock",
  "latency":{"retrieval_ms":0.0,"generation_ms":0.0,"validation_ms":0.0,"total_ms":0.0},
  "validation":{
    "citation_references":"verified",
    "support_check":"exact_quote",
    "semantic_faithfulness":"not_evaluated"
  }
}
```

This shape example uses illustrative placeholders and zero timing values, not measured output. Use the linked actual examples for real fixture IDs/excerpts/timings.

| Field | Meaning/invariant |
|---|---|
| `answer` | Plain text with server-constructed `[S1]` markers; never HTML. In the initial answer mode, factual text is copied verbatim from evidence. |
| `sources` | Only cited excerpts from the exact evidence supplied to the provider. Names/pages/versions come from trusted retrieved metadata, not provider assertions. |
| `document_name`, `page_number`, `supporting_excerpt` | Nested under each source, not duplicated as ambiguous top-level values. Pages are physical for PDF ingestion; synthetic JSON page records are explicitly assigned fixture numbers. |
| `claims` | Each claim references source IDs; all linked excerpts equal its text in this strict mode. |
| `status` | `answered`, `insufficient_evidence`, or `error`. Never infer status from answer wording or similarity. |
| `reason` | Stable machine code, safe for routing; no raw provider error body. See codes below. |
| `mode` | `mock` for scripted/HTTP-mocked providers, `remote` for the real adapter. Always display mock mode clearly in demos. |
| `latency` | Milliseconds from `perf_counter`; retrieval/generation/validation plus total. Total includes queue wait and engine overhead; stage values need not sum exactly to total. Network timeout is per HTTP operation, not a guaranteed end-to-end SLA. |
| `validation` | Structural references and exact copying only. `semantic_faithfulness` is always `not_evaluated` here. |

All unsuccessful responses have empty `sources` and `claims`; only server-owned localized refusal/error text is shown. Failed/partially validated claims are discarded atomically. Backend must preserve this behavior rather than showing the raw provider draft.

Refusal reason codes: `missing_evidence`, `out_of_scope`, `false_assumption`, `ambiguous`, `conflicting_sources`, `outdated_sources`, `unsupported_claim`. Error reason codes: `invalid_request`, `retrieval_error`, `invalid_citation`, `malformed_response`, `provider_timeout`, `provider_error`, `provider_authentication`, `provider_rate_limited`, `remote_calls_disabled`, `provider_configuration`. `supported` is used for answered output.

## UI guidance and service limits

- Render `answer`, filenames and excerpts as escaped plain text. Do not execute document/provider markup or turn arbitrary filenames into filesystem links.
- Link `[S1]` to the matching source card; show filename, page and excerpt. Backend should map authorized document IDs to allowed download URLs. The engine does not serve raw files.
- For insufficient evidence, show the localized message and optional clarification input. For errors, show a generic retry state and safe reason code; no keys or raw HTTP exceptions.
- A citation match does not guarantee relevance, completeness or freedom from misleading extraction. The prompt asks the provider to assess these, but independent human evaluation is still required. An irrelevant verbatim quote can pass the mechanical checks; an explicit adversarial test/ablation records this limitation.
- Current mode deliberately rejects paraphrases, translations and synthesis that cannot be verified by exact identity. If evidence lacks the requested language, provider should refuse. No general language detector, semantic entailment model or ambiguity detector is claimed.
- Trusted `RAGPolicy.current_versions` filters stale versions before generation. With no authoritative priority, a document group containing multiple versions is excluded; if no clean evidence remains, the service refuses. Unrelated conflicting groups do not suppress independent clean evidence. Cross-document/same-version contradictions and false premises rely on provider assessment; metadata alone cannot discover them. Historical questions need a separately designed historical-version policy.
- Context and question limits are bounded. Chunks not sent due to the context budget cannot be cited. Version filtering runs after top-k retrieval, so a valid lower-ranked version may require a filtered retriever or larger candidate set later.

## Provider configuration and approval

`provider_from_env()` reads process environment, not `.env` files automatically. Backend may explicitly load a private `.env` with python-dotenv; never commit it. Supported selections are `mock`, `openrouter`, `together` and `compatible`. Remote choices require the appropriate API key, base URL and `LLM_MODEL`. See `.env.example`.

No paid call is approved now. Real adapter use requires **both** `ALLOW_PAID_API_CALLS=true` and an operator-created `RemoteCallApproval` scoped to exact base URL/model and a maximum number of attempts. Attempt/token limits are not a dollar-cost guarantee; inspect current rates and obtain a named spend approval first. Never build this approval object from HTTP request data. No automatic retries, redirects, provider fallback or model substitution are implemented.

Keys use SecretStr, are absent from response contracts, and raw provider messages/errors are not logged. HTTPS is required; credentials/query tokens in configured endpoint URLs are rejected. The response body is bounded, requests have configured timeouts, and ambient proxy settings are disabled. Backend should also disable debug request/body logging and assess hosted-data privacy before sending real documents.

The adapter implements Chat Completions with prompt-specified JSON, not provider-specific schema guarantees. Verify the chosen model supports the request options before approved live testing. Authoritative protocol references: [OpenRouter API reference](https://openrouter.ai/docs/api_reference/overview), [Together compatibility](https://docs.together.ai/docs/inference/openai-compatibility), [HTTPX mocked transports](https://www.python-httpx.org/advanced/transports/).

## Phase 3 additive implementation notes

The normative v1.0.0 schema and callable are unchanged. [direct_rag.py](../examples/direct_rag.py) is a minimal tested example: `make_engine(retriever, environment=private_settings, approval=operator_approval)` initializes the engine, and `answer_json(engine, question, language="ar")` returns the existing JSON shape. No HTTP server is needed. It defaults to the offline mock; a real-provider approval is server-owned and must follow explicit spend authorization. This example does not load `.env` or import synthetic answer rules.

New optional environment settings configure temperature, top-p, JSON-object response format and input bytes; OpenRouter-only options configure reasoning and routing price ceilings. See [.env.example](../.env.example) and the [live protocol](phase3_live_protocol.md). Together/custom providers reject unsupported OpenRouter-specific settings. The proposed exact model strings differ: OpenRouter `qwen/qwen3.5-9b`, Together `Qwen/Qwen3.5-9B`; no default model is silently selected.

Token usage, returned model identity and cost estimates are retained in the operator evaluation sidecar, **not** added to the public response. Missing usage remains unknown. Backend should not read mutable adapter `last_usage` fields concurrently to attribute billing; the serialized audited runner owns per-attempt receipts. Public `mode=remote` is never silently replaced with a mock result. Responses remain exact excerpts; semantic correctness and faithfulness require independent review. Stateless follow-ups/history are not supported by this contract.
