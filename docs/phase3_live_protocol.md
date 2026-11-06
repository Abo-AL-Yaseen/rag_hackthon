# Remote-generation approval protocol

This public companion keeps the existing integration-contract link usable. The original dated Phase 3 paid-provider experiment proposal is retained locally; it is not an active authorization or a current provider price quote. The unapproved `config/phase3_live_plan.json` remains a regression fixture only.

## Current boundary

- No live inference or paid service is authorized by this repository or its examples.
- All earlier two-call and one-call Groq allowances are exhausted. Never reset consumed markers to reuse permission.
- Default provider is mock. Private configuration loading is explicit; keep `ALLOW_PAID_API_CALLS=false`.
- Named Groq uses `GROQ_API_KEY`, `GROQ_BASE_URL`, `GROQ_MODEL`, both free-plan guards and an operator-owned endpoint/model/attempt-scoped `RemoteCallApproval`. It rejects paid-call enablement.
- Local flags do not independently verify account billing status. Obtain new explicit approval and confirm the intended Free account before any future call.
- Credentials, approvals and routing are never request fields. No automatic retries, redirects, model substitution or paid fallback are implemented.
- Record safe numeric usage/latency/errors for an approved attempt; missing cost/usage remains unknown. Never display keys, raw provider errors or sensitive evidence.

The [final handoff](final_backend_handoff.md) describes the implemented factory and callable. The [schema](rag_response.schema.json) remains v1.0.0; public responses do not add billing/token fields. Paid adapters exist for modularity and offline transport tests; their presence grants no spending permission.
