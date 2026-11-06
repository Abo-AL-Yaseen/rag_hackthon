# Surprise judging and Q&A rehearsal

Guide p.8: judges prepare three same-problem questions, one OOS, and ask directly on every system. Run this rehearsal on actual corpus data after implementation. It is currently a checklist, not test results. Additional p.11 challenges are optional organizer possibilities.

## Five-minute setup and three-question drill

- [ ] Launch from README with approved model/index and blank-safe logs; no secrets on screen.
- [ ] Query A: unseen wording for a known supported fact. Show answer, retrieved passage and exact source/page.
- [ ] Query B: a distinct real case requiring synthesis/table/version handling as appropriate to assigned corpus. Check every claim.
- [ ] Query C: outside corpus scope. Explicitly refuse unsupported answer instead of using general model knowledge.
- [ ] Also test an **in-domain missing fact**; topic similarity alone must not trigger an invented answer.
- [ ] Keep actual output, stage timings and reviewer notes. No answer quality is assumed from a passing UI flow.

## Conditional and robustness cases

- [ ] Dialect paraphrase of formal Arabic fact.
- [ ] Table row/header interpretation with page citation.
- [ ] Textless scanned page detected and reported honestly; OCR only if available/needed.
- [ ] Old/new conflicting sources: choose explicit valid precedence or explain unresolved conflict with both citations.
- [ ] Follow-up pronoun/context question; retrieval still grounded in documents.
- [ ] Cross-session history isolation; uploaded document visible only where authorized.
- [ ] Document containing instructions to ignore system rules treated as data.
- [ ] Provider timeout/network failure displays honest unavailable state; recording used only as labeled backup.
- [ ] Citation resolves to actual retrieved source/page and supports its associated claim.

## Ten guide questions: assign real owners

| Question (p.8) | Owner | Evidence pointer / rehearsal outcome |
|---|---|---|
| Why chunk size/overlap; what if changed? | [unassigned] | [measured comparison] |
| Which embedding model, why, how Arabic? | [unassigned] | [CPU benchmark/retrieval decision] |
| What if requested information is absent? | [unassigned] | [live refusal and false-refusal case] |
| How quality measured; worst failure and cause? | [unassigned] | [actual run and analysis] |
| Conflicting/old sources? | [unassigned] | [version test] |
| Cost/answer and 10,000-user scenario? | [unassigned] | [usage/rate/traffic assumptions] |
| Market sources and weakest financial assumption? | [unassigned] | [source ledger/sensitivity] |
| Team-written vs AI-generated; explain this code? | [unassigned] | [attribution/code walkthrough] |
| Sensitive-data protection? | [unassigned] | [actual data flow/controls] |
| First three prospects and message after competition? | [unassigned] | [suitable prospects/draft outreach] |

Guide tie-break proposal: higher technical RAG, then evaluation, then committee decision after a shared extra question. Rehearse explaining evaluation without overstating a small test set. Each team member must understand the code they discuss, including AI-assisted sections.
