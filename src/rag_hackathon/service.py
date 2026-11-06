"""Callable, serialized CPU RAG engine; no Backend/Frontend dependencies."""
from dataclasses import dataclass, field
import json
import math
import threading
import time
from types import MappingProxyType
from typing import Mapping, Protocol

from .generation.contracts import (AnswerClaim, GenerationDraft, GenerationRequest,
                                   Latency, RAGResponse, Source, ValidationInfo)
from .generation.providers import ProviderError
from .generation.selections import SelectionDraft, expand_selection
from .schema import Hit


class Retriever(Protocol):
    def search(self, question: str, k: int) -> list[Hit]: ...


@dataclass(frozen=True)
class RAGPolicy:
    top_k: int = 3
    max_question_chars: int = 2000
    max_context_chars: int = 12000
    reject_mixed_versions: bool = True
    current_versions: Mapping[str,str] = field(default_factory=dict)
    # Keys are 'ar'/'en'; messages must be server-configured, never user/provider text.
    refusal_messages: Mapping[str,str] = field(default_factory=dict)

    def __post_init__(self):
        if not 1 <= self.top_k <= 20 or not 1 <= self.max_question_chars <= 10000 or not 1 <= self.max_context_chars <= 32000:
            raise ValueError('Invalid bounded RAG policy')
        if any(k not in ('ar','en') or not v.strip() for k,v in self.refusal_messages.items()):
            raise ValueError('Refusal messages require ar/en and nonempty server-owned text')
        object.__setattr__(self,'current_versions',MappingProxyType(dict(self.current_versions)))
        object.__setattr__(self,'refusal_messages',MappingProxyType(dict(self.refusal_messages)))


REFUSALS = {
    'en': {
        'ambiguous':'Please clarify which document, policy or item you mean.',
        'conflicting_sources':'The available sources need reconciliation before I can give a definitive answer.',
        'outdated_sources':'The retrieved sources are outdated or have no approved current version.',
        'false_assumption':'I cannot support the assumption in this question from the available evidence.',
        'default':'I cannot answer this question from the available evidence.'},
    'ar': {
        'ambiguous':'يرجى توضيح المستند أو السياسة أو الموضوع المقصود.',
        'conflicting_sources':'تحتاج المصادر المتاحة إلى التوفيق بينها قبل تقديم إجابة مؤكدة.',
        'outdated_sources':'المصادر المسترجعة قديمة أو لا تتضمن نسخة حالية معتمدة.',
        'false_assumption':'لا تدعم الأدلة المتاحة الافتراض الوارد في هذا السؤال.',
        'default':'لا أستطيع الإجابة عن هذا السؤال من الأدلة المتاحة.'}}


class GroundingError(Exception):
    def __init__(self,code,detail=None):
        self.code = code
        self.detail = detail or code


def parse_draft(content):
    if not isinstance(content,str) or len(content.encode('utf-8')) > 65536:
        raise GroundingError('malformed_response')
    def unique_pairs(pairs):
        result = {}
        for key,value in pairs:
            if key in result:
                raise ValueError('Duplicate key')
            result[key] = value
        return result
    try:
        data = json.loads(content,object_pairs_hook=unique_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
        if isinstance(data,dict) and 'selection_ids' in data:
            return SelectionDraft.model_validate(data)
        return GenerationDraft.model_validate(data)
    except Exception:
        raise GroundingError('malformed_response','draft_schema_or_json_invalid') from None


def validate_claims(draft, hits):
    """Strict quote support; does NOT establish semantic relevance to question."""
    if isinstance(draft,SelectionDraft):
        try:
            draft=expand_selection(draft,hits)
        except KeyError:
            raise GroundingError('invalid_citation','selection_not_in_evidence') from None
    lookup = {h.chunk.chunk_id:h.chunk for h in hits}
    sources,claims = [],[]
    source_keys = {}
    for claim in draft.claims:
        ids = []
        for ref in claim.evidence:
            chunk = lookup.get(ref.chunk_id)
            if chunk is None:
                raise GroundingError('invalid_citation','unknown_chunk_id')
            if not ref.excerpt.strip() or ref.excerpt not in chunk.text:
                raise GroundingError('invalid_citation','excerpt_not_in_chunk')
            # Every linked excerpt must support the whole claim by exact identity.
            # No lexical-overlap/cosine score is promoted to semantic entailment.
            if claim.text != ref.excerpt:
                raise GroundingError('unsupported_claim','claim_excerpt_mismatch')
            key = (chunk.chunk_id,ref.excerpt)
            if key not in source_keys:
                source_id = f'S{len(sources)+1}'
                source_keys[key] = source_id
                sources.append(Source(source_id=source_id,chunk_id=chunk.chunk_id,
                                      document_id=chunk.document_id,document_name=chunk.source,
                                      page_number=chunk.page,supporting_excerpt=ref.excerpt,version=chunk.version))
            if source_keys[key] not in ids:
                ids.append(source_keys[key])
        claims.append(AnswerClaim(text=claim.text,source_ids=ids))
    return sources,claims


class RAGService:
    def __init__(self, retriever: Retriever, provider, *, policy=None, diagnostics=None):
        self.retriever, self.provider = retriever,provider
        self.policy = policy or RAGPolicy()
        self.diagnostics=diagnostics
        self.diagnostic_failures=0
        # One owning CPU engine/Qdrant Local client per worker/storage directory.
        self._lock = threading.Lock()

    def __call__(self, question, *, language='en'):
        return self.ask(question,language=language).model_dump(mode='json')

    def ask(self, question: str, *, language='en') -> RAGResponse:
        start = time.perf_counter()
        with self._lock:
            return self._ask(question,language,start)

    def _ask(self, question, language, start):
        valid_language = language in ('ar','en')
        language = language if language in ('ar','en') else 'en'
        timings = {'retrieval_ms':0.0,'generation_ms':0.0,'validation_ms':0.0}
        stage='request_validation'
        diagnostic_detail=None
        raw_draft=None
        selected=[]
        hits=[]
        mode = 'mock' if getattr(self.provider,'is_mock',False) else 'remote'
        def finish(status,reason,sources=None,claims=None):
            sources,claims = sources or [],claims or []
            if status == 'answered':
                answer = '\n'.join(c.text+' '+''.join(f'[{s}]' for s in c.source_ids) for c in claims)
            elif status == 'error':
                answer = 'تعذر إكمال الطلب بأمان. حاول لاحقاً.' if language=='ar' else 'The request could not be completed safely. Please try again later.'
            else:
                answer = self.policy.refusal_messages.get(language) or REFUSALS[language].get(reason,REFUSALS[language]['default'])
            response=RAGResponse(answer=answer,sources=sources,claims=claims,status=status,reason=reason,
                               language=language,mode=mode,
                               latency=Latency(**timings,total_ms=(time.perf_counter()-start)*1000),
                               validation=ValidationInfo(citation_references='verified' if sources else 'not_applicable',
                                                         support_check='exact_quote' if sources else 'not_applicable'))
            if self.diagnostics is not None:
                try:
                    self.diagnostics.record(raw_draft,selected,stage=stage,reason=reason,
                                            detail=diagnostic_detail,status=status,retrieved_hits=hits)
                except Exception:
                    self.diagnostic_failures+=1  # No private exception/logging or response change.
            response.latency.total_ms=(time.perf_counter()-start)*1000
            return response
        if not valid_language or not isinstance(question,str) or not question.strip() or len(question)>self.policy.max_question_chars:
            return finish('error','invalid_request')
        phase_start = time.perf_counter()
        stage='retrieval_validation'
        try:
            hits = self.retriever.search(question,self.policy.top_k)
            if len({h.chunk.chunk_id for h in hits}) != len(hits):
                raise ValueError('Duplicate retrieved ID')
            if any(h.chunk.page<1 or not h.chunk.source.strip() or not h.chunk.text.strip() or not math.isfinite(h.score) for h in hits):
                raise ValueError('Invalid retrieved evidence')
        except Exception:
            timings['retrieval_ms'] = (time.perf_counter()-phase_start)*1000
            return finish('error','retrieval_error')
        timings['retrieval_ms'] = (time.perf_counter()-phase_start)*1000
        if not hits:
            return finish('insufficient_evidence','missing_evidence')
        phase_start = time.perf_counter()
        stage='evidence_policy'
        current = [h for h in hits if h.chunk.document_id not in self.policy.current_versions
                   or h.chunk.version == self.policy.current_versions[h.chunk.document_id]]
        if not current:
            timings['validation_ms'] = (time.perf_counter()-phase_start)*1000
            return finish('insufficient_evidence','outdated_sources')
        versions = {}
        for h in current:
            versions.setdefault(h.chunk.document_id,set()).add(h.chunk.version)
        if self.policy.reject_mixed_versions:
            conflicted = {doc for doc,v in versions.items() if len(v)>1}
            # Do not let an unrelated conflicting document suppress clean evidence.
            # Unprioritized versions themselves are never sent to the provider.
            current = [h for h in current if h.chunk.document_id not in conflicted]
            if not current:
                timings['validation_ms'] = (time.perf_counter()-phase_start)*1000
                return finish('insufficient_evidence','conflicting_sources')
        selected,used = [],0
        for h in current:
            if used+len(h.chunk.text) <= self.policy.max_context_chars:
                selected.append(h)
                used += len(h.chunk.text)
        timings['validation_ms'] = (time.perf_counter()-phase_start)*1000
        if not selected:
            return finish('insufficient_evidence','missing_evidence')
        phase_start = time.perf_counter()
        stage='provider_transport'
        try:
            result = self.provider.generate(GenerationRequest(question.strip(),language,tuple(selected)))
        except ProviderError as exc:
            timings['generation_ms'] = (time.perf_counter()-phase_start)*1000
            return finish('error',exc.code)
        except TimeoutError:
            timings['generation_ms'] = (time.perf_counter()-phase_start)*1000
            return finish('error','provider_timeout')
        except Exception:
            timings['generation_ms'] = (time.perf_counter()-phase_start)*1000
            return finish('error','provider_error')
        timings['generation_ms'] = (time.perf_counter()-phase_start)*1000
        phase_start = time.perf_counter()
        stage='draft_parsing'
        try:
            raw_draft=result.content
            draft = parse_draft(raw_draft)
            if draft.status == 'insufficient_evidence':
                stage='provider_refusal'
                timings['validation_ms'] += (time.perf_counter()-phase_start)*1000
                return finish('insufficient_evidence',draft.reason)
            stage='claim_validation'
            sources,claims = validate_claims(draft,selected)
        except GroundingError as exc:
            diagnostic_detail=exc.detail
            timings['validation_ms'] += (time.perf_counter()-phase_start)*1000
            status = 'insufficient_evidence' if exc.code=='unsupported_claim' else 'error'
            return finish(status,exc.code)
        except Exception:
            timings['validation_ms'] += (time.perf_counter()-phase_start)*1000
            return finish('error','malformed_response')
        timings['validation_ms'] += (time.perf_counter()-phase_start)*1000
        stage='accepted'
        return finish('answered','supported',sources,claims)
