"""Application lifespan: load encoder/index once, never rebuild embeddings on startup."""
from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.catalog import ProgramCatalog, load_catalog
from backend.config import BackendSettings
from backend.filtering import ScopedAllowlistRetriever

logger = logging.getLogger("backend")


@dataclass
class AppState:
    settings: BackendSettings
    catalog: ProgramCatalog
    retriever: Any | None = None
    encoder: Any | None = None
    provider: Any | None = None
    service: Any | None = None
    index_open: bool = False
    index_detail: str | None = "index not opened"
    provider_mode: str = "uninitialized"
    startup_errors: list[str] = field(default_factory=list)

    @property
    def rag_ready(self) -> bool:
        return self.service is not None and self.index_open


def _load_mock_rules(path: Path | None) -> list:
    if path is None:
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "rules" in raw:
        if raw.get("synthetic") is not True or raw.get("scripted") is not True:
            raise ValueError("Mock rules must be explicitly synthetic and scripted")
        return list(raw["rules"])
    if isinstance(raw, list):
        return raw
    raise ValueError("Unrecognized mock rules format")


def build_state(settings: BackendSettings | None = None) -> AppState:
    settings = settings or BackendSettings.from_env()
    catalog = load_catalog(settings.catalog_path)
    state = AppState(settings=settings, catalog=catalog)

    if settings.allow_paid_api_calls:
        # Hard stop: hackathon policy keeps paid calls disabled.
        state.startup_errors.append("ALLOW_PAID_API_CALLS must remain false")
        logger.error("Refusing startup provider init while ALLOW_PAID_API_CALLS is enabled")
        return state

    try:
        from rag_hackathon.generation.providers import provider_from_env

        mock_rules = _load_mock_rules(settings.mock_rules_path)
        provider_kwargs: dict[str, Any] = {"mock_rules": mock_rules}
        if settings.load_dotenv_file is not None:
            provider_kwargs["env_file"] = settings.load_dotenv_file
        state.provider = provider_from_env(**provider_kwargs)
        state.provider_mode = "mock" if getattr(state.provider, "is_mock", False) else "remote"
        if state.provider_mode == "remote":
            # Live remote providers need operator RemoteCallApproval; none is attached here.
            logger.warning(
                "LLM provider mode is remote but no RemoteCallApproval is attached; "
                "generation will fail closed until an operator authorizes free-tier calls"
            )
    except Exception as exc:
        state.startup_errors.append(f"provider_init_failed:{type(exc).__name__}")
        logger.exception("Provider initialization failed")
        return state

    if settings.index_path is None:
        state.index_detail = "RAG_INDEX_PATH not set"
        logger.warning("RAG_INDEX_PATH unset; /api/chat will report rag_not_ready")
        return state

    index_path = settings.index_path
    if not index_path.exists():
        state.index_detail = "configured index path does not exist"
        logger.warning("Index path missing: %s", index_path)
        return state
    if not (index_path / "dataset_manifest.json").is_file():
        state.index_detail = "dataset_manifest.json missing; refusing to rebuild on startup"
        logger.warning("Incomplete index at %s", index_path)
        return state

    try:
        from rag_hackathon.service import RAGPolicy, RAGService
        from rag_hackathon.workspace import cached_encoder, open_index

        # Never call ingest() here. Opening an existing store only.
        state.encoder = cached_encoder()
        state.retriever = open_index(index_path, encoder=state.encoder)
        scoped = ScopedAllowlistRetriever(state.retriever)
        state.service = RAGService(scoped, state.provider, policy=RAGPolicy(top_k=3))
        state.index_open = True
        state.index_detail = "open"
        logger.info("RAG index opened for single-worker Qdrant Local use")
    except Exception as exc:
        state.index_detail = f"index_open_failed:{type(exc).__name__}"
        state.startup_errors.append(state.index_detail)
        logger.exception("Failed to open RAG index (no rebuild attempted)")
        _safe_close_retriever(state)
    return state


def shutdown_state(state: AppState) -> None:
    _safe_close_retriever(state)
    state.service = None
    state.provider = None
    state.encoder = None
    state.index_open = False
    state.index_detail = "closed"
    state.provider_mode = "uninitialized"


def _safe_close_retriever(state: AppState) -> None:
    retriever = state.retriever
    state.retriever = None
    if retriever is None:
        return
    try:
        retriever.close()
    except Exception:
        logger.exception("Error while closing Qdrant retriever")


def python_version_string() -> str:
    return ".".join(map(str, sys.version_info[:3]))
