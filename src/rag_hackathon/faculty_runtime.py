"""One process-owned faculty engine, with request-local program selection.

No provider settings or .env file are loaded here. Default generation is an
empty offline mock; a Backend must inject an independently authorized provider.
"""
from contextvars import ContextVar
from contextlib import contextmanager
from dataclasses import dataclass
import json
from pathlib import Path
import re
import time
import unicodedata

from .generation.contracts import Latency, RAGResponse, ValidationInfo
from .generation.providers import DeterministicMockProvider
from .retrieval.scoped import ScopedIndex
from .service import RAGService, RAGPolicy, REFUSALS
from .academic_decisions import intent, program_mentions, MESSAGES
from .runtime_catalog import RuntimeCatalog
from .course_catalog import CourseCatalog


@dataclass
class _Selection:
    retriever: object
    uncertainty: str | None = None
    evidence_languages: set | None = None


def _course_codes(question):
    return {''.join(str(unicodedata.decimal(c)) for c in code)
            for code in re.findall(r'(?<!\d)\d{6,10}(?!\d)', question)}


def _asks_prerequisites(question):
    return bool(re.search(r'prereq|co.?requis|eligib|before.{0,30}(?:taking|register|enrol)|'
                          r'need.{0,30}(?:pass|complete)|متطلب|سابق|شرط|شروط|'
                          r'(?:بقدر|بصير|يجوز|يمكن).{0,25}(?:أسجل|اسجل|تسجيل|آخذ|اخذ|أنزل|انزل)|'
                          r'لازم.{0,35}(?:مخلص|ناجح|ماخذ|آخذ|اخذ)|'
                          r'قبل.{0,35}(?:آخذ|اخذ|أنزل|انزل|أسجل|اسجل)',
                          question, re.IGNORECASE))


def _mentioned_plan_versions(question):
    # Published plan identifiers are structured values. Keep the original
    # question and evidence intact; normalize decimal digits only for comparison.
    digits = ''.join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in question)
    return {f'{year}-{int(revision)}' for year, revision in
            re.findall(r'(?<!\d)((?:19|20)\d{2})\s*[-–‑]\s*(\d{1,2})(?!\d)', digits)}


class _SelectedRetriever:
    def __init__(self, runtime):
        self.runtime = runtime

    def search(self, question, k):
        selection = self.runtime._selection.get()
        if selection is None:
            raise RuntimeError('Faculty calls must go through the owning runtime')
        hits = selection.retriever.search(question, k)
        selection.evidence_languages = {self.runtime._documents[h.chunk.document_id].get('language') for h in hits}
        if not _asks_prerequisites(question):
            return hits
        codes = _course_codes(question)
        candidates = [h for h in hits if self.runtime._documents[h.chunk.document_id].get('course_code') in codes] if codes else hits[:1]
        for hit in candidates:
            doc = self.runtime._documents[hit.chunk.document_id]
            if doc.get('kind') != 'course':
                continue
            flags = set(doc.get('quality_flags', []))
            if flags.intersection({'intergroup_AND_OR_not_explicit', 'colored_prerequisite_semantics_unverified',
                                   'duplicate_published_prerequisite_code'}):
                selection.uncertainty = 'ambiguous'
                return []
            quote = doc.get('reference_quote', '')
            if 'غير مذكور في الخانة المنشورة' in quote or 'Not listed in the published cell' in quote:
                selection.uncertainty = 'missing_evidence'
                return []
        return hits


class FacultyRuntime:
    """Initialize once at Backend startup; call ask in a worker thread.

    A ContextVar carries immutable per-request view selection into the one
    RAGService. Neither service.retriever nor its program is mutated per call.
    The service lock serializes generation and the index lock protects Qdrant.
    """
    def __init__(self, index, documents, provider=None, *, top_k=5):
        self._index = index
        self._documents = {d['document_id']: dict(d) for d in documents}
        self._selection = ContextVar(f'faculty_selection_{id(self)}', default=None)
        self._views = {}
        self._programs = {}
        for d in documents:
            if d['scope'] == 'program':
                key = (d['program_id'], d['plan_version'])
                if key not in self._views:
                    self._views[key] = index.for_program(*key, prefer_matching_plan=True)
                    self._programs[key] = {'program_id': key[0], 'plan_version': key[1],
                        'name_ar': d.get('program_name_ar'), 'name_en': d.get('program_name_en')}
        self._general = index.for_regulations()
        self.service = RAGService(_SelectedRetriever(self), provider or DeterministicMockProvider(),
                                  policy=RAGPolicy(top_k=top_k))
        self._catalog=RuntimeCatalog(self.programs(),documents)
        self.course_catalog=CourseCatalog(documents,self.programs())

    @classmethod
    def open(cls, index_path, provider=None, *, encoder=None, top_k=5):
        path = Path(index_path)
        index = ScopedIndex.open(path, encoder=encoder)
        try:
            binding = json.loads((path/'scope_manifest.json').read_text(encoding='utf-8'))
            result=cls(index, binding['documents'], provider, top_k=top_k)
            reviewed=path.parent.parent/'processed'/'engineering_faculty_20261107'/'courses.json'
            if reviewed.is_file():
                result.course_catalog=CourseCatalog(binding['documents'],result.programs(),json.loads(reviewed.read_text(encoding='utf-8')))
            return result
        except Exception:
            index.close()
            raise

    def programs(self):
        return [dict(self._programs[k]) for k in sorted(self._programs)]

    def source_locator(self, document_id):
        """Trusted URL/page/table metadata for a Backend-owned source resolver."""
        if document_id in self._catalog.locators:
            return dict(self._catalog.locators[document_id])
        if document_id in self.course_catalog.locators:
            return dict(self.course_catalog.locators[document_id])
        doc = self._documents[document_id]
        return {key: doc.get(key) for key in ('source_url','document_title','physical_pdf_page',
            'engine_page_number','table_index','row_index','program_id','plan_version','article')}

    def ask(self, question, *, language='en', program_id=None, plan_version=None):
        start = time.perf_counter()
        if (language not in ('ar', 'en') or not isinstance(question, str) or not question.strip()
                or len(question) > self.service.policy.max_question_chars):
            # The engine rejects invalid input before touching the retriever.
            return self.service.ask(question, language=language)
        if intent(question)=='catalog':
            result=self._catalog.ask(question,language)
            return result if result else self._decision('missing_evidence','language_evidence',language,start)
        if intent(question)=='course_list':
            return self._course_list(question,language,program_id,plan_version,start)
        if (program_id is None) != (plan_version is None):
            return self._decision('ambiguous', 'scope', language, start)
        key = (program_id, plan_version)
        if program_id is not None and (not isinstance(program_id, str) or not isinstance(plan_version, str)):
            return self._refusal('ambiguous', language, start)
        if program_id is not None and key not in self._views:
            return self._refusal('outdated_sources', language, start)
        mentioned = _mentioned_plan_versions(question)
        named = program_mentions(question, self.programs())
        if len(named)>1 or len(mentioned)>1 or (program_id is not None and named and named!={program_id}):
            return self._decision('ambiguous', 'conflict', language, start)
        if program_id is not None and mentioned and mentioned != {plan_version}:
            # Do not silently answer a textual request for another plan using
            # the selected context, even when the same course code exists.
            return self._decision('ambiguous', 'conflict', language, start)
        if program_id is None and named and len(mentioned)==1:
            candidate=(next(iter(named)), next(iter(mentioned)))
            if candidate not in self._views:
                return self._decision('ambiguous', 'scope', language, start)
            program_id,plan_version=candidate
            key=candidate
        need=intent(question)
        if need=='out_of_scope':
            return self._decision('out_of_scope', need, language, start)
        if need=='schedule':
            return self._decision('missing_evidence', need, language, start)
        if need in ('course','graduation') and program_id is None:
            return self._decision('ambiguous', 'scope', language, start)
        if need=='warning' and program_id is None:
            return self._decision('ambiguous', 'warning', language, start)
        if need=='load':
            return self._decision('ambiguous', 'load', language, start)
        selection = _Selection(self._views[key] if program_id is not None else self._general)
        token = self._selection.set(selection)
        try:
            result = self.service.ask(question, language=language)
            if selection.uncertainty:
                result.reason = selection.uncertainty
                if language == 'ar':
                    result.answer = 'المتطلبات السابقة غير واضحة أو غير مذكورة في الخطة المنشورة. يرجى مراجعة القسم قبل التسجيل.'
                else:
                    result.answer = 'Prerequisites are unclear or not listed in the published plan. Please check with the department before registration.'
            elif result.status=='insufficient_evidence' and result.reason=='missing_evidence':
                if selection.evidence_languages and language not in selection.evidence_languages:
                    result.answer=MESSAGES['language_evidence'][language]
                elif need=='course':
                    result.answer=MESSAGES['missing'][language]
            result.latency.total_ms = (time.perf_counter()-start)*1000
            return result
        finally:
            self._selection.reset(token)

    def __call__(self, question, **kwargs):
        return self.ask(question, **kwargs).model_dump(mode='json')

    def _refusal(self, reason, language, start):
        return RAGResponse(answer=REFUSALS[language].get(reason, REFUSALS[language]['default']),
            sources=[], claims=[], status='insufficient_evidence', reason=reason, language=language,
            mode='mock' if getattr(self.service.provider, 'is_mock', False) else 'remote',
            latency=Latency(retrieval_ms=0, generation_ms=0, validation_ms=0,
                            total_ms=(time.perf_counter()-start)*1000),
            validation=ValidationInfo(citation_references='not_applicable', support_check='not_applicable'))

    def _decision(self, reason, message, language, start):
        response=self._refusal(reason, language, start)
        response.answer=MESSAGES[message][language]
        return response

    def _course_list(self,question,language,program,version,start):
        if (program is not None and not isinstance(program,str)) or (version is not None and not isinstance(version,str)):
            return self._refusal('ambiguous',language,start)
        named=program_mentions(question,self.programs());mentioned=_mentioned_plan_versions(question)
        if len(named)>1 or (program and named and named!={program}) or (version and mentioned and mentioned!={version}):
            return self._decision('ambiguous','conflict',language,start)
        program=program or (next(iter(named)) if len(named)==1 else None)
        version=version or (next(iter(mentioned)) if len(mentioned)==1 else None)
        versions=sorted({p['plan_version'] for p in self.programs() if p['program_id']==program})
        if program and versions and version is None:
            response=self._refusal('ambiguous',language,start)
            response.answer=('اختار نسخة خطتك الدراسية من النسخ المتاحة لهذا التخصص: ' if language=='ar' else 'Please select your study-plan version from the available versions for this program: ')+', '.join(versions)
            return response
        if not program or not version:return self._decision('ambiguous','scope',language,start)
        if (program,version) not in self._views:return self._refusal('outdated_sources',language,start)
        from .academic_decisions import normalize
        if re.search(r'السنه|الفصل|first.year|year\s*\d|semester',normalize(question)):
            response=self._refusal('missing_evidence',language,start)
            response.answer=('الخطة المتاحة لا تحتوي تصنيفًا موثقًا حسب السنة أو الفصل. أقدر أعرض كامل المساقات حسب مجموعات المتطلبات المنشورة، دون افتراض السنة من رمز المساق.' if language=='ar' else 'The available plan has no verified year/semester grouping. I can show all course entries by their published requirement groups, without inferring year from course codes.')
            return response
        result=self.course_catalog.ask(question,program,version,language)
        if result:return result
        response=self._refusal('missing_evidence',language,start)
        response.answer=('لا توجد قائمة مساقات موثوقة كافية في الخطة المتاحة. راجع القسم الأكاديمي؛ لا أستطيع اختراع قائمة كاملة.' if language=='ar' else 'The available plan does not contain a sufficient verified course list. Please check with the academic department; I cannot invent a complete list.')
        return response

    def close(self):
        self._index.close()

    @contextmanager
    def embedding_session(self):
        """Reuse the cached CPU model under its existing owner lock; no downloads."""
        with self._index._lock:
            yield self._index._owner.encoder
