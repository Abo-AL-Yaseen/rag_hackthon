"""Verified program/plan catalog loader. Never fabricates study-plan data."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class ProgramPlan:
    program_id: str
    name: str
    plan_version: str
    document_ids: frozenset[str]
    language: str | None = None


@dataclass(frozen=True)
class ProgramCatalog:
    catalog_version: str
    verified: bool
    plans: tuple[ProgramPlan, ...]
    _by_key: Mapping[tuple[str, str], ProgramPlan]

    def list_programs(self) -> list[dict]:
        """Public catalog payload; document_ids stay server-side for filtering."""
        grouped: dict[str, dict] = {}
        for plan in self.plans:
            entry = grouped.setdefault(
                plan.program_id,
                {
                    "program_id": plan.program_id,
                    "name": plan.name,
                    "plan_versions": [],
                    "language": plan.language,
                },
            )
            if plan.plan_version not in entry["plan_versions"]:
                entry["plan_versions"].append(plan.plan_version)
        return list(grouped.values())

    def resolve(self, program_id: str, plan_version: str) -> ProgramPlan | None:
        return self._by_key.get((program_id, plan_version))


def load_catalog(path: Path) -> ProgramCatalog:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("verified") is not True:
        raise ValueError("Program catalog must set verified=true; refusing unverified data")
    programs = raw.get("programs")
    if not isinstance(programs, list):
        raise ValueError("Program catalog.programs must be a list")
    plans: list[ProgramPlan] = []
    keys: dict[tuple[str, str], ProgramPlan] = {}
    for item in programs:
        if not isinstance(item, dict):
            raise ValueError("Invalid program catalog entry")
        program_id = str(item.get("program_id", "")).strip()
        name = str(item.get("name", "")).strip()
        plan_version = str(item.get("plan_version", "")).strip()
        docs = item.get("document_ids")
        if not program_id or not name or not plan_version:
            raise ValueError("program_id, name, and plan_version are required")
        if not isinstance(docs, list) or not docs or any(not str(d).strip() for d in docs):
            raise ValueError("document_ids must be a nonempty list of trusted index document IDs")
        key = (program_id, plan_version)
        if key in keys:
            raise ValueError(f"Duplicate program/plan mapping: {program_id}/{plan_version}")
        plan = ProgramPlan(
            program_id=program_id,
            name=name,
            plan_version=plan_version,
            document_ids=frozenset(str(d).strip() for d in docs),
            language=(str(item["language"]).strip() if item.get("language") else None),
        )
        plans.append(plan)
        keys[key] = plan
    return ProgramCatalog(
        catalog_version=str(raw.get("catalog_version", "1.0.0")),
        verified=True,
        plans=tuple(plans),
        _by_key=MappingProxyType(keys),
    )
