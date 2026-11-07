"""Optional offline FastAPI HANDOFF HARNESS, not the teammate Backend.

No server starts at import. Uvicorn is an external runner, not installed by this
file. The v1.0.0 question body/answer shape are preserved. Example scope headers
must be replaced by authorized server-owned student context in the real Backend.
"""
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path

from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from examples.backend_integration import Question
from rag_hackathon.faculty_runtime import FacultyRuntime
from rag_hackathon.generation.contracts import RAGResponse
from rag_hackathon.generation.providers import DeterministicMockProvider


def offline_runtime_from_env():
    if os.environ.get('LLM_PROVIDER', 'mock').lower() != 'mock':
        raise ValueError('This handoff harness supports offline mock only; live calls are not authorized')
    if any(os.environ.get(name, 'false').lower() == 'true' for name in ('ALLOW_FREE_API_CALLS','ALLOW_PAID_API_CALLS')):
        raise ValueError('Both live-call switches must remain false in this harness')
    index_path = Path(os.environ['RAG_INDEX_PATH'])
    rules_path = os.environ.get('RAG_OFFLINE_CASES_PATH')
    rules = []
    if rules_path:
        cases = json.loads(Path(rules_path).read_text(encoding='utf-8'))
        rules = [{'question': c['question'], **({'selections': c['selections']} if c.get('selections')
                    else {'refusal_reason': c.get('refusal_reason', 'missing_evidence')})} for c in cases]
    return FacultyRuntime.open(index_path, DeterministicMockProvider(rules), top_k=5)


def create_app(runtime_factory=offline_runtime_from_env):
    @asynccontextmanager
    async def lifespan(app):
        # One model/index/provider/RAGService for the entire process lifetime.
        runtime = await run_in_threadpool(runtime_factory)
        app.state.faculty_runtime = runtime
        try:
            yield
        finally:
            await run_in_threadpool(runtime.close)

    app = FastAPI(title='Offline faculty RAG handoff harness (not teammate app)', lifespan=lifespan)
    origins = [s.strip() for s in os.environ.get('RAG_ALLOWED_ORIGINS','').split(',') if s.strip()]
    if origins:
        app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['GET','POST'],
                           allow_headers=['Content-Type','X-RAG-Program','X-RAG-Plan'])

    @app.get('/health')
    async def health():
        provider = app.state.faculty_runtime.service.provider
        return {'status':'ready','mode':'mock' if getattr(provider,'is_mock',False) else 'remote',
                'contract_version':'1.0.0'}

    @app.get('/rag/programs')
    async def programs():
        return app.state.faculty_runtime.programs()

    @app.post('/rag/answer', response_model=RAGResponse)
    async def answer(request: Question, x_rag_program: str | None = Header(default=None),
                     x_rag_plan: str | None = Header(default=None)):
        return await run_in_threadpool(app.state.faculty_runtime.ask, request.question,
            language=request.language, program_id=x_rag_program, plan_version=x_rag_plan)

    return app
