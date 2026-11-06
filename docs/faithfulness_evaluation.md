# Correctness, citations and faithfulness review procedure

The judging guide p.3 asks for 10+ reference questions, evaluation and error-driven improvement. Phase 2 supplies 20 **synthetic** questions and an offline scripted mock. This proves integration, not semantic reasoning, live model capability or hackathon performance.

## Separate measurements

1. **Retrieval**: Phase 1 P@K/R@K evidence remains unchanged. Phase 2 has additional version fixtures, so its retrieval runs are not a controlled before/after comparison against the original corpus.
2. **Reference answer diagnostics**: normalize Unicode/case/Arabic diacritics, then compute exact match and multiset token F1 against reference answers. These are lexical agreement measures, not semantic correctness. A longer faithful quote can receive low F1; a wrong negation or number can share many tokens. Negative cases have N/A lexical answer scores.
3. **Citation correctness**: verify cited ID belongs to retrieved evidence, document/page/version match, and excerpt is an exact nonempty substring. Also check claim/source link integrity. This is structural correctness, not proof that the excerpt answers the question.
4. **Refusal behavior**: report expected-status matches, false refusals on positives, refusals/unsafe answers on negatives, errors and denominators. The mock's answerability is scripted from known fixtures; label it accordingly. A failed provider is an `error`, not a successful refusal.
5. **Semantic correctness and faithfulness**: pending independent human review. JSON values remain null until actual reviewed judgments exist; never fill them with mock status accuracy, token F1, similarity or quote-copy counts.

## Human review workflow

Use `docs/evidence/phase2_review_queue.json`. Freeze corpus/model/prompt/policy/run IDs before review. The queue includes the question, reference answer, actual response, claim/source links and retrieved text. The AI-authored fixture labels themselves require team verification.

- For each question, verify the reference against original document/page; identify missing or erroneous labels before judging the answer. Keep revisions/version history separate from the evaluated run.
- Score answer correctness **0 = incorrect/unresponsive, 1 = partially correct or materially incomplete, 2 = correct and complete**. Check numbers, exceptions, language, assumptions, temporal validity and whether it answers the specific question. Reference wording alone is not authority.
- Break answered output into atomic factual claims. For each claim, inspect the cited excerpt **and surrounding source context**. Record `supported`, `contradicted`, or `unverifiable`, with reviewer and explanation. A source containing the same words can still be misleading, obsolete, irrelevant, or quoted out of context.
- Faithfulness = supported factual claims / all factual claims. Contradicted and unverifiable claims count as unsupported. Refusals with no factual claims are N/A, not perfect faithfulness. Report per-case values, aggregate numerator/denominator and sample size.
- Separately record whether each source supports the associated claim and the question, whether all needed citations are present, and whether cross-source conflicts were disclosed.
- For negatives, check whether refusal/clarification is appropriate. A false premise can sometimes be corrected with evidence; this preparation policy conservatively refuses it. Do not count generic failure messages as correct abstention.
- Prefer a second reviewer for disagreements and high-impact cases; record adjudication. If only one reviewer is available, disclose that limitation. No paid LLM judge is configured or authorized.

## Required negative categories and retained weaknesses

The preparation cases include outside-scope, in-domain absent facts, false assumptions, ambiguity, conflicting versions, obsolete evidence and instruction attacks. Unit tests additionally cover no evidence, invalid references, mismatched excerpts, unsupported paraphrases, timeouts, provider errors and malformed output.

Trusted version metadata can reject outdated/mixed versions; it cannot infer the latest effective law/policy from a filename. Source priority must come from the actual challenge/owner. Same-version contradictions and ambiguous questions require provider or human judgment; no general automated semantic detector exists here.

The paired ablation deliberately includes an **irrelevant but verbatim quote**. It passes exact-copy validation, demonstrating why semantic relevance and faithfulness need separate review. Do not hide this case or present mechanical validation as solving hallucination generally.

## Before/after reporting

Phase 1 had no generation layer, so no historical generation-quality percentage can be compared. The Phase 2 evaluator records a separate artificial ablation: the same valid/invalid draft fixtures before mechanical validation versus after strict validation. Label it a validation-control experiment, not a live LLM improvement. Preserve all misses, false refusals, provider errors and known accepted-but-irrelevant cases.

After the challenge is announced, build at least 10 real corpus-grounded questions, keep tuning and held-out cases distinct where practical, run the **approved actual provider**, then apply this review. Synthetic and real reports must remain separate. Paid calls require approval before that run.
