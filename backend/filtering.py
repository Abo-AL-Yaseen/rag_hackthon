"""Per-request document allowlist wrapper around the engine Retriever protocol.

RAGService.ask() does not accept program_id/plan_version. DenseRetriever.search()
has no Qdrant metadata filter API. Backend therefore scopes retrieval by wrapping
the shared retriever and filtering Hit.document_id after an oversampled search.

Filter scope is set inside the worker thread via contextvars so concurrent
requests cannot leak allowlists into each other. Prompt-only filtering is not used.
"""
from __future__ import annotations

from contextvars import ContextVar
from typing import Protocol

from rag_hackathon.schema import Hit

# None => no program filter (full index). frozenset => allowlisted document_ids only.
_document_allowlist: ContextVar[frozenset[str] | None] = ContextVar(
    "backend_document_allowlist",
    default=None,
)


class RetrieverProto(Protocol):
    def search(self, question: str, k: int) -> list[Hit]: ...


class ScopedAllowlistRetriever:
    """Delegates to a shared DenseRetriever; applies the active request allowlist."""

    def __init__(self, base: RetrieverProto, *, oversample: int = 8, max_candidates: int = 40):
        if oversample < 1 or max_candidates < 1:
            raise ValueError("Positive oversample and max_candidates required")
        self._base = base
        self._oversample = oversample
        self._max_candidates = max_candidates

    def search(self, question: str, k: int) -> list[Hit]:
        allowlist = _document_allowlist.get()
        if allowlist is None:
            return self._base.search(question, k)
        if not allowlist:
            return []
        candidate_k = min(max(k * self._oversample, k), self._max_candidates)
        hits = self._base.search(question, candidate_k)
        return [h for h in hits if h.chunk.document_id in allowlist][:k]


def ask_with_document_filter(service, question: str, language: str, allowlist: frozenset[str] | None):
    """Run RAGService.ask while binding a request-scoped document allowlist.

    Must be invoked inside the threadpool worker so the ContextVar lives on the
    same thread that performs retrieval.
    """
    token = _document_allowlist.set(allowlist)
    try:
        return service.ask(question, language=language)
    finally:
        _document_allowlist.reset(token)
