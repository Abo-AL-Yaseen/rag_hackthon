from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from backend.filtering import ask_with_document_filter
from backend.schemas import ChatRequest
from rag_hackathon.generation.contracts import RAGResponse

router = APIRouter(prefix="/api", tags=["chat"])


def _resolve_allowlist(state, request: ChatRequest) -> frozenset[str] | None:
    has_program = request.program_id is not None
    has_plan = request.plan_version is not None
    if has_program != has_plan:
        raise HTTPException(
            status_code=422,
            detail="program_id and plan_version must be provided together or omitted together",
        )
    if not has_program:
        return None
    program_id = request.program_id.strip() if request.program_id else ""
    plan_version = request.plan_version.strip() if request.plan_version else ""
    if not program_id or not plan_version:
        raise HTTPException(status_code=422, detail="program_id and plan_version must be nonempty")
    plan = state.catalog.resolve(program_id, plan_version)
    if plan is None:
        raise HTTPException(status_code=422, detail="unknown program_id/plan_version")
    return plan.document_ids


@router.post("/chat", response_model=RAGResponse)
async def chat(request: Request, body: ChatRequest) -> RAGResponse:
    state = request.app.state.backend
    if not state.rag_ready or state.service is None:
        raise HTTPException(status_code=503, detail="rag_not_ready")

    allowlist = _resolve_allowlist(state, body)
    # Sync RAG + Qdrant Local must run off the event loop; single worker owns the store.
    return await run_in_threadpool(
        ask_with_document_filter,
        state.service,
        body.question,
        body.language,
        allowlist,
    )
