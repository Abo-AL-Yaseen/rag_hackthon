"""Server-owned settings. Never accept these fields from end-user HTTP bodies."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = Path(__file__).resolve().parent / "catalog" / "programs.json"
DEFAULT_CORS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_path(name: str, default: Path | None = None) -> Path | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    return Path(raw)


@dataclass(frozen=True)
class BackendSettings:
    index_path: Path | None
    catalog_path: Path
    mock_rules_path: Path | None
    cors_origins: tuple[str, ...]
    load_dotenv_file: Path | None
    host: str
    port: int
    allow_paid_api_calls: bool
    allow_free_api_calls: bool
    llm_provider: str

    @classmethod
    def from_env(cls) -> "BackendSettings":
        cors_raw = os.environ.get("BACKEND_CORS_ORIGINS", "").strip()
        cors = tuple(o.strip() for o in cors_raw.split(",") if o.strip()) or DEFAULT_CORS
        dotenv = _env_path("BACKEND_ENV_FILE")
        if dotenv is None and (ROOT / ".env").is_file():
            # Opt-in private load only when BACKEND_LOAD_DOTENV=true.
            dotenv = (ROOT / ".env") if _env_bool("BACKEND_LOAD_DOTENV") else None
        return cls(
            index_path=_env_path("RAG_INDEX_PATH"),
            catalog_path=_env_path("PROGRAM_CATALOG_PATH", DEFAULT_CATALOG) or DEFAULT_CATALOG,
            mock_rules_path=_env_path("MOCK_RULES_PATH"),
            cors_origins=cors,
            load_dotenv_file=dotenv,
            host=os.environ.get("BACKEND_HOST", "127.0.0.1").strip() or "127.0.0.1",
            port=int(os.environ.get("BACKEND_PORT", "8000")),
            allow_paid_api_calls=_env_bool("ALLOW_PAID_API_CALLS", False),
            allow_free_api_calls=_env_bool("ALLOW_FREE_API_CALLS", False),
            llm_provider=os.environ.get("LLM_PROVIDER", "mock").strip().lower() or "mock",
        )
