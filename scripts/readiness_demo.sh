#!/usr/bin/env bash
# Offline-only proof that these commands work in Windows Git Bash.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
PY="./.venv/Scripts/python.exe"
test -x "$PY"
export PYTHONPATH="$(cygpath -w "$PWD/src")"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
export ALLOW_PAID_API_CALLS=false ALLOW_FREE_API_CALLS=false
RUN_ID="${READINESS_RUN_ID:-$(date +%Y%m%d-%H%M%S)}"
INDEX="data/index/readiness-gitbash-$RUN_ID"
OUT=".local/readiness-$RUN_ID"
mkdir -p "$OUT"
"$PY" --version
"$PY" -m pip check
"$PY" scripts/local_documents.py extract --input data/sample/readiness/inputs --output "$OUT/extracted.json"
"$PY" scripts/local_documents.py ingest --input data/sample/readiness/inputs --index "$INDEX" --output "$OUT/ingest.json"
"$PY" scripts/local_documents.py retrieve --index "$INDEX" --question "How long is an observatory telescope reservation?" --output "$OUT/retrieval.json"
"$PY" examples/invoke_local_engine.py --index "$INDEX" --request data/sample/readiness/request_ar1.json --mock-rules data/sample/readiness/mock_rules.json --output "$OUT/answer_ar.json"
"$PY" examples/invoke_local_engine.py --index "$INDEX" --request data/sample/readiness/request_en1.json --mock-rules data/sample/readiness/mock_rules.json --output "$OUT/answer_en.json"
"$PY" -m pytest -q --junitxml="$OUT/tests.xml"
printf 'Offline Git Bash workflow complete. Index: %s; private outputs: %s\n' "$INDEX" "$OUT"
