"""Optional adapter example for Backend review; no server/network at import time."""
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool
from typing import Literal

from rag_hackathon.generation.contracts import RAGResponse
from rag_hackathon.service import RAGService


class Question(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    question: str=Field(min_length=1,max_length=2000)
    language: Literal['ar','en']='en'


def make_app(service: RAGService) -> FastAPI:
    """Backend owns startup/shutdown, authentication, CORS, rate limits and hosting.

    Create exactly one engine/local Qdrant owner for this storage. Close its index
    at application shutdown. Do not create a model/client on every HTTP request.
    """
    app=FastAPI(title='RAG engine integration example')

    @app.post('/rag/answer',response_model=RAGResponse)
    async def answer(request: Question):
        return await run_in_threadpool(service.ask,request.question,language=request.language)

    return app
