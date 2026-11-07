"""FastAPI application factory for the RAG Backend transport."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from backend.config import BackendSettings
from backend.lifecycle import AppState, build_state, shutdown_state
from backend.routes import chat, health, programs, sources, courses, documents

logger = logging.getLogger("backend")


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    # Never enable debug body logging that could capture secrets or document text.


def create_app(settings: BackendSettings | None = None, *, state: AppState | None = None) -> FastAPI:
    configure_logging()
    settings = settings or BackendSettings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app_state = state if state is not None else await run_in_threadpool(build_state, settings)
        app.state.backend = app_state
        if app_state.startup_errors:
            logger.warning("Backend started degraded: %s", ",".join(app_state.startup_errors))
        try:
            yield
        finally:
            await run_in_threadpool(shutdown_state, app_state)

    app = FastAPI(
        title="IEEE RAG Hackathon Backend",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Accept", "Authorization"],
    )
    app.include_router(health.router)
    app.include_router(programs.router)
    app.include_router(chat.router)
    app.include_router(sources.router)
    app.include_router(courses.router)
    app.include_router(documents.router)
    return app


app = create_app()
