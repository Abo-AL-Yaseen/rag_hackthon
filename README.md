# IEEE RAG Hackathon - RAG Engine

CPU-friendly Arabic/English document retrieval and conservative, source-cited answers. Backend and Frontend are owned by teammates. The unknown hackathon challenge has not been implemented.

**Readiness:** 178 offline regression tests passed in preparation; the final staged-snapshot result is recorded in [publication checks](docs/evidence/publication_checks.json). New synthetic Arabic/English PDFs passed extraction, chunking, CPU embeddings, independent Qdrant Local indexing, retrieval and filename/physical-page citations. Synthetic mock results demonstrate integration, not real LLM quality or challenge performance.

**License: GNU AGPL-3.0-only.** The owner confirmed credential rotation and authorized this open-source license. Publication is currently paused for the specific `regex`/CNRI dependency-license concern documented in [third-party notices](THIRD_PARTY_NOTICES.md). No commit or push has been made during preparation.

## Project license and source obligations

Except for separately licensed third-party materials, this project is licensed under GNU Affero General Public License version 3 only. The complete, unmodified [LICENSE](LICENSE) was obtained from the [official GNU text](https://www.gnu.org/licenses/agpl-3.0.txt). The program is provided without warranty as described there.

When distributing covered copies, preserve copyright/license notices, identify modifications and provide Corresponding Source as required by the license. If you modify the program and users interact with it remotely over a computer network, section 13 requires a prominent opportunity to obtain that version's Corresponding Source at no charge. A future hosted Backend must implement the appropriate source offer; publishing this repository is not a substitute for maintaining the offer for the deployed version. The engine does not deploy an HTTP server or add a source-offer UI by itself.

Dependency and font licenses remain their own licenses; the project license does not relicense upstream material. PyMuPDF/MuPDF are used through their open-source licensing route, not a purchased commercial license. Preserve upstream notices and PDF producer information. See [third-party notices and compatibility findings](THIRD_PARTY_NOTICES.md). No paid service is authorized.

## Environment and installation

Tested: Windows x64, Python **3.11.9**, PyTorch **2.8.0+cpu**, cached `intfloat/multilingual-e5-small` (384 dimensions). Use Windows Git Bash from the repository root. The existing workspace is `/d/rag_hackathon`; use your own checkout directory elsewhere.

Keep an existing `.venv`. If absent, create it with an installed Python 3.11.9 interpreter:

```bash
if [ ! -f .venv/Scripts/python.exe ]; then py -3.11 -m venv .venv; fi
PY="./.venv/Scripts/python.exe"
"$PY" -c 'import sys; assert sys.version_info[:3] == (3, 11, 9), "Python 3.11.9 required"'
export PYTHONPATH="$(cygpath -w "$PWD/src")"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
export ALLOW_PAID_API_CALLS=false ALLOW_FREE_API_CALLS=false

# Restore the exact locked environment from the separately prepared local wheel cache.
"$PY" -m pip --isolated install --no-index --find-links .cache/wheels --require-hashes -r requirements-phase1.lock.txt
"$PY" -m pip check
if [ ! -f .env ]; then cp .env.example .env; fi
"$PY" -m pytest -q
```

**A Git clone does not include the model, wheel cache or virtual environment.** Restore approved caches separately before running these commands. The exact Windows wheel names/hashes are in [the wheel manifest](docs/evidence/wheel_manifest.json); model files/revision/hashes are in [the model manifest](docs/evidence/model_manifest.json). Missing files are a blocker, not permission to download. The cache-only install and cached model path are verified; no clean internet installation is claimed.

For a separately approved new-machine download, `scripts/setup_phase1.py install` and `scripts/setup_phase1.py model` are the existing metered bootstrap tools. They require `.venv` Python 3.11.9 and a decimal 2 GB payload cap with reserve. They were **not executed** during publication preparation. The installer resolves `requirements-phase1.in`; it is not a replacement for verifying/restoring the hash-locked environment above. Do not run an unmetered pip command, relax hashes, fetch CUDA, or obtain another model implicitly. No paid API call is authorized.

## Offline execution

The one-command rehearsal creates a fresh sample index, extracts/retrieves documents, invokes the scripted offline engine and runs tests:

```bash
bash scripts/readiness_demo.sh
```

Individual steps after the environment block:

```bash
RUN_ID="$(date +%Y%m%d-%H%M%S)"
INDEX="data/index/sample-$RUN_ID"
OUT=".local/sample-$RUN_ID"
mkdir -p "$OUT"
"$PY" scripts/local_documents.py extract --input data/sample/readiness/inputs --output "$OUT/extracted.json"
"$PY" scripts/local_documents.py ingest --input data/sample/readiness/inputs --index "$INDEX" --output "$OUT/ingest.json"
"$PY" scripts/local_documents.py retrieve --index "$INDEX" --question "How long is an observatory telescope reservation?" --output "$OUT/hits.json"
"$PY" examples/invoke_local_engine.py --index "$INDEX" --request data/sample/readiness/request_ar1.json --mock-rules data/sample/readiness/mock_rules.json --output "$OUT/answer-ar.json"
"$PY" examples/invoke_local_engine.py --index "$INDEX" --request data/sample/readiness/request_en1.json --mock-rules data/sample/readiness/mock_rules.json --output "$OUT/answer-en.json"
```

These entry points forbid outbound connections and do not load `.env`. Answers are marked `mode=mock`; rules are explicitly synthetic/scripted. Unknown mock questions refuse. Open saved UTF-8 JSON in your editor to inspect Arabic.

## Actual documents and Backend integration

After the challenge is announced, save only authorized organizer PDFs under a private input directory, review extraction against every required physical page, and ingest into a **new** `data/index/<dataset-id>` path. Never use the synthetic factory or append actual documents to sample stores. Directory input defaults to PDF; explicit page-structured JSON is supported. Existing index paths, duplicate document IDs and incompatible snapshots fail closed.

[Final Backend handoff](docs/final_backend_handoff.md) includes exact imports and an executable direct call. [The existing contract](docs/integration_contract.md) and [JSON schema](docs/rag_response.schema.json) remain v1.0.0. Use `RAGService(retriever, provider)` and call `engine(question, language="ar" or "en")` for a dictionary or `engine.ask(...)` for a typed response. The synchronous engine is a Python library; no standalone HTTP service is deployed. Backend owns its transport, upload validation, authorization, lifecycle and secure document serving. One process owns each Qdrant Local directory; offload blocking calls in an async Backend.

Current factory selections are `mock`, `groq`, `openrouter`, `together`, `compatible`. Default is mock. `provider_from_env()` reads process settings; private loading requires explicit `env_file=Path(".env")`, with process overrides. Groq uses `GROQ_*`, JSON-object configuration and free-only approval gates. Keep `ALLOW_PAID_API_CALLS=false`. Earlier live allowances are exhausted; no retries, paid/model fallbacks or new live calls are authorized. The older contract's provider paragraph predates named Groq support; the final handoff explains the implemented settings.

## Architecture, evaluation and limits

[Architecture/evaluation](docs/architecture_and_evaluation.md) | [Readiness/troubleshooting](docs/hackathon_readiness.md) | [Faithfulness procedure](docs/faithfulness_evaluation.md)

PDF/page-JSON ingestion -> token chunks with source/page metadata -> CPU E5/Qdrant retrieval -> bounded evidence -> provider -> server-owned excerpt/citation validation -> v1.0.0 response. BM25 is available separately; the local index helper does not automatically enable hybrid retrieval.

Status is `answered`, `insufficient_evidence` or `error`. The current mode returns verified source excerpts, not unrestricted paraphrased synthesis or translation. Matching citation IDs/exact text does not prove semantic relevance. OCR, robust structured tables, general semantic contradiction detection, native multi-turn/history, tenant RBAC and Frontend are not implemented. Evaluate at least ten real-corpus references plus negatives after announcement; synthetic results are not challenge scores. No LLM training is claimed mandatory.

## Security, attribution and publication scope

`.env.example` has blank credentials; `.env`, authorization markers, private documents, indexes, models/caches and logs are excluded. Historical machine-specific reports and organizer material remain local. Only curated synthetic evidence is published. Source excerpts can still contain sensitive data on a real corpus: keep debug content private and assess hosted-data consent before any authorized remote call.

OpenAI Codex assisted with guide analysis, setup/tools, engine code, synthetic fixtures, prompts, tests, integration examples, diagnostics, evaluation, documentation and publication preparation. Independent team review remains required. [AI attribution](docs/ai_attribution.md) and [third-party notices](THIRD_PARTY_NOTICES.md) distinguish assistance from third-party licenses. The official judging guide is excluded pending redistribution permission; obtain an authorized copy from organizers. The owner explicitly selected the GNU AGPL-3.0-only project license.
