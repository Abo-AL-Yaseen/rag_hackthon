# AI assistance and source attribution record

Guide pp.2,7-8 permits and encourages AI use in writing/development with a short README disclosure naming tools and their work. Judges test actual team understanding. Unattributed copied code/project has a proposed penalty on p.6. AI disclosure and third-party code attribution are distinct obligations.

## Current factual record

| Tool | Work performed | Human review status |
|---|---|---|
| OpenAI Codex | Read/extract and visually inspect supplied guide; inspect local environment; draft checklist, readiness/implementation documents and templates; create PDF audit script and preparation config files. | Team review pending. |
| PyMuPDF 1.26.6 | Local text extraction and PNG rendering for all 12 source pages. | All 12 page images visually inspected during preparation. |
| OpenAI Codex, approved Phase 1 | CPU-only dependency setup, metered cached downloads, synthetic source pages/reference questions, retrieval and citation modules, evaluation/benchmark runner, automated tests and measured evidence report. | Automated test and measurement evidence in `docs/evidence/`; team review of AI-authored code and labels still pending. |
| OpenAI Codex, approved Phase 2 | Provider interface/adapters, conservative RAG service, version/refusal policy, citation validation, scripted mock rules, synthetic negative cases, evaluation/review tools, Backend contract/example, regression tests and report. | Offline tests/evidence available. Mock lookup is scripted; semantic correctness and faithfulness are not independently reviewed. No real provider calls made. |
| OpenAI Codex, Phase 3 preparation | Current provider documentation/catalog validation, configurable generation/routing parameters, numeric token/cost accounting, plan-bound live approval/audit tools, dialect/paraphrase fixtures, offline tests/evaluation, direct-call example and report. | 101 offline tests pass, including the original 78. Human review pending; no real inference, semantic score or live approval claimed. |
| OpenAI Codex, Groq configuration review | Named Groq factory mapping, explicit private-file loading, free-only local guards, provider-specific request settings, credential-template cleanup, offline tests and configuration report. | Automated evidence available; replacement credential, account Free status and live authentication remain unverified. No live Groq request made. |
| OpenAI Codex, user-authorized Groq Free smoke | Read-only credential/model preflight, exactly two real synthetic-corpus inference attempts, safe numeric telemetry, direct evidence review, post-run regression and failure report. | English source-supported answer; Arabic false refusal. 141 tests pass; independent team review pending. Two-call authorization exhausted. |
| OpenAI Codex, Phase 3.1 offline investigation | Failure-path isolation, server-owned excerpt selection prompt/protocol, strict backward-compatible validation, local redacted diagnostics, synthetic control experiments and regression report. | 171 tests pass. Historical Arabic cause remains unconfirmed; no new live inference, model download or semantic-quality claim. Team review and separately authorized real verification remain pending. |
| OpenAI Codex, user-authorized Phase 3.2 | Exactly one real Groq Free Arabic verification, single-use request guard, original-source comparison, sanitized diagnostics, regression checks and report. | PASS for this synthetic fixture; 173 tests pass. Existing tests/contract preserved. No further live allowance remains; independent team review and broader evaluation are still pending. |
| OpenAI Codex, Phase 4 readiness | New synthetic two-language PDF fixtures and visual checks, reproduced/fixed RTL PDF extraction ordering, fresh-index lifecycle/CLI, executable offline callable example, five regression tests, Git Bash rehearsal, readiness documentation and proposed handoff/security checklist. | 178 tests pass, including the original 173 unchanged. Four tiny PDF cases verify retrieval and citation mechanics with scripted generation. No new live inference, downloads or installed packages; independent team and actual-corpus review remain pending. |
| OpenAI Codex, publication preparation | Selective candidate review/staging, credential-pattern/privacy checks, public README/readiness cleanup, font-license notices, Git ignore/line-ending rules and regression from the staged export. | 178 tests pass from the staged export using existing caches. Engine/test code and Backend contract preserved. No commit, push or live inference. Owner credential-rotation and project-license decisions remain publication blockers. |
| OpenAI Codex, owner-approved AGPL licensing review | Official full AGPL text, source-obligation documentation, dependency-license metadata/notices review, staged security checks and repository-local public noreply identity. | Owner confirmed key rotation and selected AGPL-3.0-only. The pinned regex/CNRI compatibility concern remains unresolved; no commit or push was made. Executable code/dependencies unchanged; prior 178-test result retained. |

No independent team review, model training, business validation, production readiness or real challenge quality is claimed. Phase 1 benchmark/retrieval figures describe synthetic preparation only; consult the dated report for actual measurements and limitations.

## README disclosure template for submission

> We used [tool names] for [actual activities/files]. Team members reviewed and tested [specific work] and are responsible for the final system. [Human-authored work and key technical decisions]. Evaluation uses [actual dataset and review method]; [any AI judge and its limitations]. Third-party code, models and datasets are credited in [ledger path].

Replace every placeholder and remove untrue clauses. The current README already includes a factual preparation-stage disclosure.

## Third-party source/model/data ledger

| Component/material | Origin URL or supplied source | Version/commit | License/rights checked | Reused or modified scope | Attribution location |
|---|---|---|---|---|---|
| Judging guide | Team-supplied local PDF | v1.0, hash in checklist | Do not assume redistribution rights | Read for preparation, unchanged | README/checklist |
| PyMuPDF | https://pymupdf.readthedocs.io/ | 1.26.6 | Review terms before distributing dependencies/product | Inspection dependency | Requirements/this record |
| Embedding model, cached Python distributions and embedded PDF fonts | Upstream sources and exact local manifests | See notices/manifests | Publication/license choice still requires owner approval | Dependencies and synthetic fixtures; no model weights/wheels published | [Third-party notices](../THIRD_PARTY_NOTICES.md) |

Keep generated/reference/synthetic data labeled. Record model revisions and training provenance only from authoritative documentation; using pretrained weights is not training by this team. Every member should explain prompts, chunking, retrieval, metrics, failure handling and any code they present.
