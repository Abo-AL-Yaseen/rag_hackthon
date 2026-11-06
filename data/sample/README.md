# Synthetic preparation corpus

These six JSON documents and their 12 numbered page records are invented test fixtures. They are not university policies, the hackathon challenge, user research or factual business evidence. `synthetic_pages.json` is their combined ingestion fixture; `synthetic_questions.json` contains 12 answerable references plus two unanswerable probes.

Named citation sources resolve to actual files under `documents/`. A JSON page number is explicitly assigned fixture metadata; PDF ingestion separately uses physical 1-based PDF pages. Source text is retained unchanged in each retrieved chunk. Regenerate the document files offline with:

```powershell
./.venv/Scripts/python.exe scripts/build_synthetic_documents.py
```

Relevance labels are page-based here because each short page produces one chunk. Real documents with longer pages require span-level relevance review after chunking. Reference answers were AI-authored for preparation and have not been independently reviewed by the team.
