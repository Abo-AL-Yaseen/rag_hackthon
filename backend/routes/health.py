from __future__ import annotations

from fastapi import APIRouter, Request

from backend.lifecycle import python_version_string
from backend.schemas import HealthResponse, IndexStatus

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    state = request.app.state.backend
    settings = state.settings
    index = IndexStatus(
        configured=settings.index_path is not None,
        path=str(settings.index_path) if settings.index_path else None,
        open=state.index_open,
        detail=state.index_detail,
    )
    rag_ready = state.rag_ready
    status = "ok" if rag_ready else "degraded"
    provider_mode = state.provider_mode if state.provider_mode in {"mock", "remote", "uninitialized"} else "uninitialized"
    return HealthResponse(
        status=status,
        rag_ready=rag_ready,
        index=index,
        provider_mode=provider_mode,  # type: ignore[arg-type]
        catalog_programs=len({p.program_id for p in state.catalog.plans}),
        catalog_verified=state.catalog.verified,
        python_version=python_version_string(),
        qdrant_local_workers="single",
    )
