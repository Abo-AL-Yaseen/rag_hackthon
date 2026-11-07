from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool
from backend.schemas import ChatRequest
from rag_hackathon.generation.contracts import RAGResponse
from rag_hackathon.academic_decisions import intent

router = APIRouter(prefix='/api', tags=['chat'])

@router.post('/chat', response_model=RAGResponse)
async def chat(request: Request, body: ChatRequest) -> RAGResponse:
    state = request.app.state.backend
    if not state.rag_ready:
        raise HTTPException(status_code=503, detail='rag_not_ready')
    program = body.program_id.strip() if body.program_id is not None else None
    version = body.plan_version.strip() if body.plan_version is not None else None
    list_missing_plan=intent(body.question)=='course_list' and program is not None and version is None
    if ((program is None) != (version is None) and not list_missing_plan) or program == '' or version == '':
        raise HTTPException(status_code=422, detail='program_id and plan_version must be provided together and nonempty')
    if program is not None and not any(p['program_id']==program and (version in p['plan_versions'] or list_missing_plan) for p in state.programs()):
        raise HTTPException(status_code=422, detail='unknown program_id/plan_version')
    return await run_in_threadpool(state.runtime.ask, body.question, language=body.language,
                                  program_id=program, plan_version=version)
