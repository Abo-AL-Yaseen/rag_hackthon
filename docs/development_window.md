# November 7 development plan: 10:30-15:00

Date supplied by team; times follow guide pp.2,8 and are planned in **Asia/Jerusalem**. Total working window is 270 minutes. The guide requires delivery before 15:00. Task allocation below is a team proposal, conditional on actual staffing and scaffold eligibility; no agents or teammates have been assigned work automatically.

| Local time | Minutes | Primary outcome / stop condition |
|---|---:|---|
| 10:30-10:45 | 15 | Capture actual assignment, corpus, rules and submission instructions. Confirm prepared-scaffold eligibility. Define user, scope and three demo cases; inspect PDF extraction. |
| 10:45-11:20 | 35 | Ingest assigned documents; audit Arabic/tables/pages; preserve provenance and versions; create initial reference questions. Stop adding sources once core scope is covered. |
| 11:20-12:00 | 40 | Run BM25/dense baseline and useful fusion/filtering; inspect top passages; select measured k/chunk config. Keep a known working fallback. |
| 12:00-12:35 | 35 | Grounded generation, page citations, refusal and provider failure handling. Use only approved paid calls. Verify supported and absent-fact cases. |
| 12:35-13:05 | 30 | Wire Arabic RTL product to real service; expose sources. Add history or upload only if baseline passes. |
| 13:05-13:40 | 35 | Complete 10+ references; run evaluation, human faithfulness review and unseen-style tests; fix largest measured failure; preserve before/after evidence. |
| 13:40-14:10 | 30 | Freeze core features; complete sourced business/marketing calculations and deck with actual results. Avoid introducing untested architecture changes. |
| 14:10-14:30 | 20 | Five-minute rehearsal/Q&A; record optional 2-3-minute demo if feasible; check final deck and source ledger. |
| 14:30-14:45 | 15 | Clean-start/archive check, secrets/attribution review, verify submission links and artifacts. Fix only submission blockers. |
| 14:45-14:50 | 5 | Submit, verify access and retain receipt. |
| 14:50-15:00 | 10 | Contingency before cutoff; keep submitted version stable and product ready. |

With multiple actual teammates, have a business/presentation owner research the **announced** problem and fill sourced commercial inputs while engineering progresses; have an evaluation owner label/review questions while ingestion/retrieval is built. Record real roles. With one person, shorten optional UI/innovation work and keep business work explicit within each checkpoint.

## Decision gates and fallback order

- At 11:20, if Arabic extraction fails, fix provenance/text quality before embedding more content. Report scanned pages; do not silently omit them.
- At 12:00, if dense setup fails, keep measured BM25 baseline operational and explain limitation. Do not claim an embedding comparison that did not run.
- At 12:35, require at least one genuine cited answer and one refusal before optional product features.
- At 13:40, stop E5-base/reranker/voice/login experiments. Prefer demonstrable retrieval, evaluation, commercial evidence and polished presentation.
- If hosted generation fails, show honest error/retrieval evidence and use authentic labeled demo recording; never substitute invented live output.
- Preserve time for sourced business, marketing and presentation (35 base points) and evaluation (tie-break relevance). A visually complete UI without technical score >=15/30 receives no product bonus under the guide's stated gate.

Judging runs 15:00-16:30 per guide; preferred final session ends 16:15. Keep the prepared five-minute talk, four-minute Q&A and one-minute transition ready, with source/evaluation artifacts accessible.
