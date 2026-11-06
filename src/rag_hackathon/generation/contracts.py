from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..schema import Hit

Reason = Literal['supported', 'missing_evidence', 'out_of_scope', 'false_assumption',
                 'ambiguous', 'conflicting_sources', 'outdated_sources', 'unsupported_claim']


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class EvidenceReference(StrictModel):
    chunk_id: str = Field(min_length=1, max_length=200)
    excerpt: str = Field(min_length=1, max_length=1500)


class DraftClaim(StrictModel):
    text: str = Field(min_length=1, max_length=1500)
    evidence: list[EvidenceReference] = Field(min_length=1, max_length=4)


class GenerationDraft(StrictModel):
    status: Literal['answered', 'insufficient_evidence']
    reason: Reason
    claims: list[DraftClaim] = Field(max_length=4)

    @model_validator(mode='after')
    def consistent_decision(self):
        if self.status == 'answered' and (not self.claims or self.reason != 'supported'):
            raise ValueError('Answered decisions require claims and supported reason')
        if self.status == 'insufficient_evidence' and (self.claims or self.reason == 'supported'):
            raise ValueError('Refusal decisions require empty claims and a refusal reason')
        return self


@dataclass(frozen=True)
class GenerationRequest:
    question: str
    language: Literal['ar', 'en']
    evidence: tuple[Hit, ...]


@dataclass(frozen=True)
class ProviderResult:
    content: str


class LLMProvider(Protocol):
    is_mock: bool

    def generate(self, request: GenerationRequest) -> ProviderResult: ...


class Source(StrictModel):
    source_id: str
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int = Field(ge=1)
    supporting_excerpt: str = Field(min_length=1)
    version: str


class AnswerClaim(StrictModel):
    text: str
    source_ids: list[str] = Field(min_length=1)


class Latency(StrictModel):
    retrieval_ms: float = Field(ge=0, allow_inf_nan=False)
    generation_ms: float = Field(ge=0, allow_inf_nan=False)
    validation_ms: float = Field(ge=0, allow_inf_nan=False)
    total_ms: float = Field(ge=0, allow_inf_nan=False)


class ValidationInfo(StrictModel):
    citation_references: Literal['verified', 'not_applicable']
    support_check: Literal['exact_quote', 'not_applicable']
    semantic_faithfulness: Literal['not_evaluated'] = 'not_evaluated'


class RAGResponse(StrictModel):
    contract_version: Literal['1.0.0'] = '1.0.0'
    answer: str
    sources: list[Source]
    claims: list[AnswerClaim]
    status: Literal['answered', 'insufficient_evidence', 'error']
    reason: str
    language: Literal['ar', 'en']
    mode: Literal['mock', 'remote']
    latency: Latency
    validation: ValidationInfo

    @model_validator(mode='after')
    def response_invariants(self):
        if self.status == 'answered':
            ids = {s.source_id for s in self.sources}
            if not self.sources or not self.claims or len(ids) != len(self.sources):
                raise ValueError('Answered response requires unique sources and claims')
            if any(not set(c.source_ids) <= ids for c in self.claims):
                raise ValueError('Every claim must reference supplied sources')
        elif self.sources or self.claims:
            raise ValueError('Unanswered responses must not contain answer claims/sources')
        return self
