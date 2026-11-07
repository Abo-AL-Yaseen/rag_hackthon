# Academic context decisions and offline evidence selection

`FacultyRuntime` distinguishes a missing program/plan (`ambiguous`) from absent
evidence in an explicitly selected plan (`missing_evidence`). Shared regulations
remain available without selecting a program. A complete textual program and
plan may be resolved against verified catalog names; contradictory UI/text
context requires clarification. Academic warnings without faculty context and
personal registration-load questions receive targeted clarification. Exam dates
are not in this dataset; the response refers students to the official schedule.

The integrated offline Backend uses `LocalAcademicEvidenceProvider`, which has
no question bank and no academic answer constants. It recognizes bounded intent
families, checks the actual retrieved policy headings or exact course rows, and
selects original excerpts. Missing prerequisite semantics remain guarded before
generation. Citation validation, matching-plan precedence, Qdrant prefiltering,
single-owner lifecycle and RAGResponse v1.0.0 are unchanged.

This selector is **not an LLM**. Because contract v1.0.0 supports only `mock` and
`remote`, local extractive responses use `mode=mock`; the UI explicitly labels
them as local excerpts without an LLM. Backend no longer loads scripted question
fixtures. Historical fixture utilities are not used by the serving path.

It supports only the covered intent families, not arbitrary reasoning. It cannot
translate Arabic policy evidence into verified English claims, calculate a
student's personal eligibility, or access records. Unknown or insufficient
evidence is refused. Passing this evaluation does not establish live LLM accuracy.

To reproduce the offline real-index evaluation, first stop the single owning
Backend process, then run:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_academic_decisions.py --index data\index\engineering_faculty_20261107_v1 --output .local\academic_decision_evaluation
```

The evaluator uses FastAPI's actual application and FacultyRuntime with the
existing index, blocks external connections, and writes actual requests,
responses, evidence, scope isolation and citation checks locally. Restart with
`powershell -ExecutionPolicy Bypass -File scripts\run_final_demo.ps1 -Component backend`.
It does not rebuild the index or call Groq. Both API permission flags stay false.
