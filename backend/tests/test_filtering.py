"""Filtering must affect retrieval hits, not merely prompt text, without cross-request leaks."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from backend.filtering import ScopedAllowlistRetriever, ask_with_document_filter, _document_allowlist
from backend.tests.helpers import FakeRetriever, make_test_client, sample_hit
from rag_hackathon.generation.providers import DeterministicMockProvider
from rag_hackathon.service import RAGPolicy, RAGService


def test_allowlist_filters_retrieved_documents():
    hits = [sample_hit("doc_a"), sample_hit("doc_b")]
    base = FakeRetriever(hits)
    scoped = ScopedAllowlistRetriever(base, oversample=2, max_candidates=10)

    token = _document_allowlist.set(frozenset({"doc_b"}))
    try:
        result = scoped.search("q", k=3)
    finally:
        _document_allowlist.reset(token)

    assert [h.chunk.document_id for h in result] == ["doc_b"]
    assert base.calls and base.calls[0][1] >= 3


def test_unfiltered_passes_through():
    base = FakeRetriever([sample_hit("doc_a"), sample_hit("doc_b")])
    scoped = ScopedAllowlistRetriever(base, oversample=2, max_candidates=10)
    result = scoped.search("q", k=2)
    assert [h.chunk.document_id for h in result] == ["doc_a", "doc_b"]


def test_request_scoped_filter_isolation():
    base = FakeRetriever([sample_hit("doc_a"), sample_hit("doc_b")])
    scoped = ScopedAllowlistRetriever(base, oversample=4, max_candidates=20)
    provider = DeterministicMockProvider([])
    service = RAGService(scoped, provider, policy=RAGPolicy(top_k=3))

    def run(allow_id: str) -> str:
        response = ask_with_document_filter(
            service,
            "unknown question",
            "en",
            frozenset({allow_id}),
        )
        assert response.status in {"insufficient_evidence", "error", "answered"}
        return allow_id

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(run, ["doc_a", "doc_b", "doc_a", "doc_b"]))
    assert results == ["doc_a", "doc_b", "doc_a", "doc_b"]
    assert len(base.calls) == 4
    assert all(k > 3 for _, k in base.calls)


def test_chat_endpoint_applies_program_filter(populated_catalog, mock_service):
    service, base = mock_service
    base.hits = [sample_hit("doc_a")]
    with make_test_client(populated_catalog, service=service) as client:
        ok = client.post(
            "/api/chat",
            json={
                "question": "How long are loans?",
                "language": "en",
                "program_id": "eng",
                "plan_version": "2024",
            },
        )
        blocked = client.post(
            "/api/chat",
            json={
                "question": "How long are loans?",
                "language": "en",
                "program_id": "eng",
                "plan_version": "2025",
            },
        )
    assert ok.status_code == 200
    assert ok.json()["status"] == "answered"
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "insufficient_evidence"
