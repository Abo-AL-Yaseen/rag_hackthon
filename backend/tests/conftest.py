"""Backend unit/mocked-integration fixtures. No live Groq. No real index required."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.filtering import ScopedAllowlistRetriever
from backend.tests.helpers import FakeRetriever, sample_hit
from rag_hackathon.generation.providers import DeterministicMockProvider
from rag_hackathon.service import RAGPolicy, RAGService


@pytest.fixture
def empty_catalog(tmp_path: Path):
    path = tmp_path / "programs.json"
    path.write_text(
        json.dumps({"catalog_version": "1.0.0", "verified": True, "programs": []}),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def populated_catalog(tmp_path: Path):
    path = tmp_path / "programs.json"
    path.write_text(
        json.dumps(
            {
                "catalog_version": "1.0.0",
                "verified": True,
                "programs": [
                    {
                        "program_id": "eng",
                        "name": "Engineering Fixture",
                        "plan_version": "2024",
                        "document_ids": ["doc_a"],
                    },
                    {
                        "program_id": "eng",
                        "name": "Engineering Fixture",
                        "plan_version": "2025",
                        "document_ids": ["doc_b"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def mock_service():
    rules = [
        {
            "question": "How long are loans?",
            "selections": [
                {
                    "document_id": "doc_a",
                    "page": 1,
                    "excerpt": "Loans last twelve days.",
                }
            ],
        }
    ]
    base = FakeRetriever([sample_hit("doc_a")])
    scoped = ScopedAllowlistRetriever(base, oversample=2, max_candidates=10)
    provider = DeterministicMockProvider(rules)
    service = RAGService(scoped, provider, policy=RAGPolicy(top_k=3))
    return service, base
