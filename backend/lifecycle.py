"""One FacultyRuntime owner per lifespan; this integration is OFFLINE only."""
from __future__ import annotations
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from backend.catalog import ProgramCatalog
from backend.config import BackendSettings
from rag_hackathon.faculty_runtime import FacultyRuntime
from rag_hackathon.generation.academic_extractive import LocalAcademicEvidenceProvider
from rag_hackathon.uploaded_documents import UploadedDocuments
logger = logging.getLogger("backend")

@dataclass
class AppState:
    settings: BackendSettings
    catalog: ProgramCatalog | None = None  # Legacy synthetic fixtures only.
    runtime: Any | None = None
    service: Any | None = None
    provider: Any | None = None
    index_open: bool = False
    index_detail: str | None = "index not opened"
    provider_mode: str = "uninitialized"
    startup_errors: list[str] = field(default_factory=list)
    uploads: Any | None = None

    @property
    def rag_ready(self) -> bool:
        return self.runtime is not None and self.service is not None and self.index_open

    def programs(self) -> list[dict]:
        if self.runtime is None:
            return self.catalog.list_programs() if self.catalog is not None else []
        grouped: dict[str, dict] = {}
        for plan in self.runtime.programs():
            item = grouped.setdefault(plan['program_id'], {
                'program_id': plan['program_id'],
                'name': plan.get('name_ar') or plan.get('name_en') or plan['program_id'],
                'name_ar': plan.get('name_ar'), 'name_en': plan.get('name_en'),
                'plan_versions': [], 'language': 'ar',
            })
            if plan['plan_version'] not in item['plan_versions']:
                item['plan_versions'].append(plan['plan_version'])
        return list(grouped.values())

def _load_mock_rules(path: Path | None) -> list:
    if path is None:
        return []
    raw = json.loads(path.read_text(encoding='utf-8'))
    if isinstance(raw, dict) and 'rules' in raw:
        if raw.get('synthetic') is not True or raw.get('scripted') is not True:
            raise ValueError('Mock rules must be explicitly synthetic and scripted')
        raw = raw['rules']
    if not isinstance(raw, list):
        raise ValueError('Unrecognized mock rules format')
    return [{'question': c['question'], **({'selections': c['selections']} if c.get('selections') else
        {'refusal_reason': c.get('refusal_reason', c.get('expected_reason', 'missing_evidence'))})} for c in raw]

def build_state(settings: BackendSettings | None = None) -> AppState:
    settings = settings or BackendSettings.from_env()
    state = AppState(settings=settings)
    if settings.allow_paid_api_calls or settings.allow_free_api_calls or settings.llm_provider != 'mock':
        state.startup_errors.append('offline_only: disable both API flags and select mock')
        state.index_detail = 'offline provider settings required'
        return state
    try:
        # Never load private .env or attach a consumed live grant here.
        # Real retrieved evidence decisions, without exact-question fixture lookup.
        # This remains a non-LLM local mode; never attach remote credentials/grants.
        state.provider = LocalAcademicEvidenceProvider()
        state.provider_mode = 'mock'
        if settings.index_path is None:
            state.index_detail = 'RAG_INDEX_PATH not set'
            return state
        state.runtime = FacultyRuntime.open(settings.index_path, state.provider, top_k=5)
        state.service = state.runtime.service
        if settings.admin_document_token is not None:
            state.uploads=UploadedDocuments(state.runtime,settings.admin_upload_root,settings.admin_index_root)
        state.index_open = True
        state.index_detail = 'open (scoped FacultyRuntime)'
        logger.info('Faculty runtime ready; one local owner, non-scripted local excerpts, no LLM')
    except Exception as exc:
        detail = f'runtime_init_failed:{type(exc).__name__}'
        state.startup_errors.append(detail)
        logger.error('Faculty startup failed: %s', type(exc).__name__)
        shutdown_state(state)
        state.index_detail = detail
    return state

def shutdown_state(state: AppState) -> None:
    if state.uploads is not None:
        state.uploads.close();state.uploads=None
    if state.runtime is not None:
        state.runtime.close()
        state.runtime = None
    state.service = None
    state.provider = None
    state.index_open = False
    state.index_detail = 'closed'
    state.provider_mode = 'uninitialized'

def python_version_string() -> str:
    return '.'.join(map(str, sys.version_info[:3]))
