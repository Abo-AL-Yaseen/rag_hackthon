"""Run with: python -m backend  (requires uvicorn installed in the 3.11.x venv)."""
from __future__ import annotations

from backend.config import BackendSettings


def main() -> None:
    settings = BackendSettings.from_env()
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "uvicorn is not installed. Use the Python 3.11.9 .venv and install the "
            "phase1 lock (fastapi is locked; add uvicorn in that same environment) "
            "before serving. Do not install into Python 3.14."
        ) from exc
    # Single worker only: Qdrant Local directories are not safe across processes.
    uvicorn.run(
        "backend.app:app",
        host=settings.host,
        port=settings.port,
        workers=1,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
