from __future__ import annotations

from fastapi import APIRouter, Request

from backend.schemas import ProgramSummary

router = APIRouter(prefix="/api", tags=["programs"])


@router.get("/programs", response_model=list[ProgramSummary])
def list_programs(request: Request) -> list[ProgramSummary]:
    """Return only verified catalog entries. Empty list is honest, not fabricated."""
    return [ProgramSummary.model_validate(item) for item in request.app.state.backend.programs()]
