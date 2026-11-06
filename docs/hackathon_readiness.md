# Hackathon readiness and troubleshooting

**READY for the tested extractable Arabic/English text-PDF engine workflow.** Unknown-corpus suitability and integrated-product readiness remain unverified. No challenge has been implemented. The owner confirmed credential rotation and selected GNU AGPL-3.0-only. Publication is separately paused for the `regex`/CNRI dependency-compatibility concern in [third-party notices](../THIRD_PARTY_NOTICES.md).

## Verified preparation

Two new, visibly synthetic PDFs (two physical pages each) were extracted and visually reviewed. Four pages became four chunks, embedded with cached 384-dimensional multilingual-e5-small on CPU, indexed in a fresh Qdrant Local store, reopened and queried. Four of four fixture questions retrieved the correct first-ranked page; four of four scripted responses cited the correct filename, physical page and exact excerpt. This tiny preparation test is not a real-corpus benchmark or a real LLM score.

A reproduced RTL extraction issue was corrected by sorting PDF blocks while preserving logical order inside each block. No citation/grounding rule was relaxed. Bad presentation-form/replacement-character extraction is rejected for manual review. All original 173 tests were preserved; five readiness tests brought the suite to 178. Latest staged-snapshot checks are in [publication_checks.json](evidence/publication_checks.json).

[Full workflow measurements](evidence/phase4_workflow.json) and [actual offline contract examples](evidence/phase4_contract_examples.json) are included. Small-corpus audit: model hash/load 10.329 s; extraction 22.960 ms; embedding/index stage 335.544 ms; four warm scripted service calls 22.609?28.474 ms; sampled process peak RSS 0.739 GiB, sampling every 50 ms. Initialization is excluded from per-question timings. These are single-run observations, not latency/quality guarantees.

A separate English-only store contained only its two supplied chunks; historical sample stores were preserved. The same internal collection name in different local directories does not share vectors. Existing paths are rejected, never reset or appended to. Snapshot/model/corpus compatibility is validated when opening.

## Start and ingest

Use the exact [README Git Bash installation/configuration commands](../README.md), preserving an existing `.venv` and restoring the separately approved model/wheel caches. Run `bash scripts/readiness_demo.sh` for the complete offline sample path. Use a fresh timestamp each time.

After announcement only: copy authorized organizer PDFs into `data/raw/hackathon/`; extract with `scripts/local_documents.py extract --input data/raw/hackathon --output .local/hackathon-extraction.json`; review every required page; ingest with `scripts/local_documents.py ingest --input data/raw/hackathon --index data/index/<NEW_DATASET_ID>`. Replace the angle-bracket placeholder with a new safe directory name. Never combine organizer data with `data/sample/`.

Use `open_index()` and `RAGService` through the [final Backend handoff](final_backend_handoff.md). Its scripted example proves integration. Actual generation needs an independently authorized provider; none is approved by publishing this code. Keep both paid/free call switches disabled for offline work. No automatic retries or paid/model fallback are implemented.

## Troubleshooting

| Symptom | Action |
|---|---|
| Wrong Python/import failure | Use `.venv/Scripts/python.exe`, Python 3.11.9 and Git Bash `PYTHONPATH` via `cygpath`. Do not alter global Python. |
| Missing wheel or model/hash mismatch | Restore the approved cache. Stop if unavailable; no automatic downloads, hash relaxation or model substitution. |
| Empty/scanned or scrambled Arabic page | Compare extraction with visible physical pages; obtain a clean export or reviewed page-structured input. OCR is not implemented. Do not reverse strings heuristically. |
| Tables or columns lose meaning | Inspect relevant rows/cells and design corpus-specific extraction before claiming support. |
| Fresh index required / incompatible snapshot | Choose a new directory after fixing input/configuration. Keep existing datasets/evidence intact. |
| Duplicate document ID | Rename colliding source files before ingestion; retain the original-name mapping. |
| Qdrant locked | Close the other owner of the same directory; do not share a local store across competing processes. |
| Mock refuses a new question | Expected for unregistered questions. Inspect retrieved evidence; fixture rules are not a real generator for new documents. |
| Arabic looks wrong only in console | Open the saved UTF-8 JSON in an editor. |
| Provider error in a later approved run | Stop; preserve sanitized diagnostics. No automatic retry or fallback. Never display credentials/raw provider bodies. |

## Tomorrow's gates

Read the actual statement and organizer updates first. Inspect extraction, build a fresh dataset, label at least ten real reference questions plus negatives, measure retrieval, manually review claim/source support and record failures. Rehearse grounded answer/refusal demonstrations and team explanations. Business/marketing figures, presentation and any integrated-product bonus need actual work/evidence, not synthetic preparation claims. Organizer requirements govern; no training or proposed challenge is assumed mandatory.

Conditional blockers: scanned PDFs/OCR, broken font mappings, complex reading order, robust structured tables, native multi-turn/history or access-control requirements. These capabilities are not implemented. Backend/Frontend acceptance and deployment belong to teammates. No new live call, paid service or unannounced challenge implementation is authorized.
