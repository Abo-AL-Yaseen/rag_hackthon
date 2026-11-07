"""Shared Backend test helpers (imported explicitly; not a pytest plugin)."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.catalog import load_catalog
from backend.config import BackendSettings
from backend.lifecycle import AppState
from rag_hackathon.schema import Chunk, Hit


class FakeRetriever:
    def __init__(self, hits: list[Hit] | None = None):
        self.hits = hits or []
        self.calls: list[tuple[str, int]] = []

    def search(self, question: str, k: int) -> list[Hit]:
        self.calls.append((question, k))
        return list(self.hits)[:k]

    def close(self) -> None:
        return None


def sample_hit(document_id: str = "doc_a", version: str = "2026") -> Hit:
    # Stable unique IDs per document_id so multi-hit fixtures stay valid for RAGService.
    suffix = {"doc_a": "a", "doc_b": "b"}.get(document_id, "c")
    chunk = Chunk(
        chunk_id=f"11111111-1111-4111-8111-11111111111{suffix}",
        document_id=document_id,
        source=f"{document_id}.pdf",
        page=1,
        text="Loans last twelve days.",
        start=0,
        end=22,
        version=version,
    )
    return Hit(chunk, 0.99)


def make_test_client(catalog_path: Path, service=None, *, index_open: bool = True) -> TestClient:
    settings = BackendSettings(
        index_path=None,
        catalog_path=catalog_path,
        mock_rules_path=None,
        cors_origins=("http://localhost:5173",),
        load_dotenv_file=None,
        host="127.0.0.1",
        port=8000,
        allow_paid_api_calls=False,
        allow_free_api_calls=False,
        llm_provider="mock",
    )
    catalog = load_catalog(catalog_path)
    state = AppState(
        settings=settings,
        catalog=catalog,
        service=service,
        provider=getattr(service, "provider", None) if service else None,
        index_open=bool(service) and index_open,
        index_detail="test-injected" if service and index_open else "test-not-ready",
        provider_mode="mock" if service else "uninitialized",
    )
    app = create_app(settings, state=state)
    return TestClient(app)
