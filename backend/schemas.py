"""HTTP request/response models. Successful RAG answers remain RAGResponse v1.0.0."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """User-facing chat body. Extra fields (secrets, model, index) are forbidden."""

    model_config = ConfigDict(extra="forbid", strict=True)

    question: str = Field(min_length=1, max_length=2000)
    language: Literal["ar", "en"] = "en"
    program_id: str | None = None
    plan_version: str | None = None


class ProgramSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    program_id: str
    name: str
    plan_versions: list[str]
    language: str | None = None


class IndexStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    configured: bool
    path: str | None = None
    open: bool = False
    detail: str | None = None


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "degraded"]
    rag_ready: bool
    index: IndexStatus
    provider_mode: Literal["mock", "remote", "uninitialized"]
    catalog_programs: int
    catalog_verified: bool
    python_version: str
    qdrant_local_workers: Literal["single"]
