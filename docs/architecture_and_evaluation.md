# Engine architecture and evaluation evidence

The engine is a synchronous Python library, separate from teammates' Backend/Frontend. Its public callable and v1.0.0 response are specified in the unchanged [contract](integration_contract.md) and [schema](rag_response.schema.json). The [final handoff](final_backend_handoff.md) contains a tested offline example.

| Module | Implemented responsibility |
|---|---|
| `ingestion.py` | PDF/page-JSON extraction, logical Arabic order, physical-page provenance, token-bounded stable chunks. |
| `workspace.py` | Verified cached CPU encoder, fresh local-dataset ingestion, manifests and checksummed reopening. |
| `retrieval/dense.py`, `retrieval/bm25.py` | E5 query/passage prefixes, normalized 384-dimensional vectors/Qdrant Local; separate lexical baseline. |
| `generation/` | Provider protocol, explicit offline mock, configurable compatible adapters and gated remote calls. |
| `service.py` | Bounded evidence, version policy, synchronous serialized calls, refusal/error handling and source-excerpt validation. |
| `diagnostics.py` | Optional private, redacted structural diagnostics; no arbitrary draft/document prose logging. |
| Evaluation modules/scripts | Retrieval Precision@K/Recall@K, reference lexical diagnostics, citation/refusal checks, latency and review queues. |

## Included measured evidence

- [Phase 1 retrieval/CPU preparation](evidence/phase1_evaluation.json): dense and BM25 measured separately on synthetic references. Preserve its recorded configuration, denominators and resource limits.
- [Phase 2 scripted evaluation](evidence/phase2_evaluation.json) and [review queue](evidence/phase2_review_queue.json): integration/reference diagnostics, including negative cases; not real LLM semantics.
- [Phase 3 offline evaluation](evidence/phase3_offline_evaluation.json): synthetic Arabic/English, paraphrase/dialect and negative preparation cases. Historical paid-provider configuration is not an authorization or current price quote.
- [Original two real Free-plan attempts](evidence/groq_live_smoke_results.json): English passed, Arabic falsely refused. This file is also a regression fixture; the original failure is retained.
- [Separately authorized Arabic verification](evidence/phase32_live_arabic_result.json) and [source review](evidence/phase32_semantic_review.json): the updated server-owned excerpt-ID path passed the twelve-day fixture. This does not retrospectively establish the missing original draft's root cause or general Arabic quality.
- [New bilingual PDF workflow](evidence/phase4_workflow.json): four tiny fixture queries and exact citations, scripted generation, no live inference.
- [Publication verification](evidence/publication_checks.json): sanitized test/security/preservation checks without machine identifiers or credentials.

All source texts in these artifacts are invented, explicitly synthetic preparation documents. They are not actual university policies, organizer data, real user research or business results. All three previous live allowances are exhausted. Account Free status relied on user confirmation; missing monetary receipts remain unknown, never invented.

## Evaluation limits

Citation IDs and exact source copying establish mechanical integrity, not answer relevance or completeness. An irrelevant verbatim quote can pass these checks. Independent human faithfulness/correctness review remains required; the public response deliberately reports `semantic_faithfulness=not_evaluated`. See the [review procedure](faithfulness_evaluation.md).

After announcement, freeze the actual corpus/chunking/configuration; label at least ten real reference questions plus negative cases; review relevant spans; measure retrieval Precision@K/Recall@K, false refusals/errors and latency; inspect every factual claim against its cited page/context. Retain failures and explicit before/after changes. Do not promote synthetic/mock status accuracy, lexical overlap or similarity into semantic-faithfulness scores.

The official judging guide and machine-specific historical logs remain private. Obtain authorized organizer instructions and confirm submission rules before claiming rubric completion or points. No challenge, market figures, scores or mandatory training requirement have been invented.
