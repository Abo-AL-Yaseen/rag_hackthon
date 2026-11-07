"""Server-bound program/plan filtering before Qdrant ranking.

This adapter preserves Hit/Chunk and the RAG v1.0.0 callable. The owner is the
existing DenseRetriever. Scope metadata is private dataset metadata, never an
end-user question field. Every document must have exactly one declared scope.
"""
import hashlib
import json
import re
import threading
import unicodedata
from pathlib import Path

from qdrant_client import models

from ..schema import Chunk, Hit


class ScopedIndex:
    """One owning Qdrant client shared by serialized, immutable scoped views."""

    def __init__(self, owner, documents, *, expected_chunk_sha256=None):
        self._owner = owner
        self._lock = threading.RLock()
        self._closed = False
        self._documents = {}
        self._programs = {}
        if not documents:
            raise ValueError('Nonempty explicit scope metadata required')
        for record in documents:
            ident = record.get('document_id')
            scope = record.get('scope')
            program = record.get('program_id')
            version = record.get('plan_version')
            if not ident or ident in self._documents:
                raise ValueError('Unique document scope identities required')
            if scope == 'regulations':
                if program is not None or version is not None:
                    raise ValueError('Shared regulations cannot declare a program or plan')
            elif scope == 'program':
                if not isinstance(program, str) or not program or not isinstance(version, str) or not version:
                    raise ValueError('Program documents require explicit program and plan version')
                self._programs.setdefault(program, set()).add(version)
            else:
                raise ValueError('Unknown scope; refusing unclassified documents')
            self._documents[ident] = dict(record)
        self._expected_chunk_sha256 = expected_chunk_sha256

    @classmethod
    def open(cls, index_path, *, encoder=None):
        """Verify scope/snapshot coverage before opening the existing local index."""
        from ..workspace import open_index
        target = Path(index_path)
        snapshot = (target / 'chunks.json').read_bytes()
        scope_bytes = (target / 'scope_manifest.json').read_bytes()
        binding = json.loads(scope_bytes)
        dataset_manifest = json.loads((target / 'dataset_manifest.json').read_text(encoding='utf-8'))
        digest = hashlib.sha256(snapshot).hexdigest()
        if (binding.get('format_version') != 1 or binding.get('chunks_sha256') != digest
                or dataset_manifest.get('scope_manifest_sha256') != hashlib.sha256(scope_bytes).hexdigest()):
            raise ValueError('Missing or incompatible scope/snapshot binding')
        raw_chunks = json.loads(snapshot)
        chunk_documents = {c['document_id'] for c in raw_chunks}
        declared = [d['document_id'] for d in binding['documents']]
        if len(set(declared)) != len(declared) or set(declared) != chunk_documents:
            raise ValueError('Scope metadata must cover every indexed document exactly once')
        # Validate declarations before allocating the Qdrant owner.
        result = cls(None, binding['documents'], expected_chunk_sha256=digest)
        result._owner = open_index(target, encoder=encoder, _scope_authorized=True)
        return result

    def for_program(self, program_id, plan_version, *, prefer_matching_plan=False):
        """Require exact server-selected program AND published plan version."""
        if program_id not in self._programs or plan_version not in self._programs[program_id]:
            raise ValueError('Unknown or missing program/plan; select an explicit indexed scope')
        def enabled(d):
            if d.get('retrieval_enabled', True):
                return True
            # An explicitly selected official plan can take precedence over a
            # mismatching handbook summary. Keep the conservative default and
            # do not enable other quarantined data or a different plan.
            return (prefer_matching_plan is True and d.get('kind') == 'plan_summary'
                    and d.get('withheld_reason') == 'graduation_conflict'
                    and d.get('program_id') == program_id and d.get('plan_version') == plan_version)
        allowed = frozenset(ident for ident, d in self._documents.items()
            if enabled(d) and (d['scope'] == 'regulations' or
            (d['program_id'] == program_id and d['plan_version'] == plan_version)))
        return _ScopedRetriever(self, allowed, program_id, plan_version, prefer_matching_plan=prefer_matching_plan)

    def for_regulations(self):
        """An unselected student context can retrieve shared regulations only."""
        allowed = frozenset(i for i, d in self._documents.items()
                            if d['scope'] == 'regulations' and d.get('retrieval_enabled', True))
        return _ScopedRetriever(self, allowed, None, None)

    def close(self):
        with self._lock:
            if not self._closed:
                self._closed = True
                if self._owner is not None:
                    self._owner.close()


class _ScopedRetriever:
    def __init__(self, parent, allowed, program_id, plan_version, *, prefer_matching_plan=False):
        self._parent = parent
        self._allowed = allowed
        self.program_id = program_id
        self.plan_version = plan_version
        self._prefer_matching_plan = prefer_matching_plan

    def search(self, question, k=3):
        if not isinstance(k, int) or not 1 <= k <= 20:
            raise ValueError('Bounded positive k required')
        parent = self._parent
        with parent._lock:
            if parent._closed:
                raise RuntimeError('Scoped index is closed')
            if not self._allowed:
                return []
            # Course identifiers are structured data, not semantic prose. Keep
            # their exact meaning within the selected program/version. Arabic
            # decimal digits are accepted without changing stored course IDs.
            requested = {''.join(str(unicodedata.decimal(c)) for c in code)
                         for code in re.findall(r'(?<!\d)\d{6,10}(?!\d)', question)}
            course_ids = {}
            for ident in self._allowed:
                code = parent._documents[ident].get('course_code')
                if code:
                    course_ids.setdefault(code, set()).add(ident)
            if requested and not requested <= course_ids.keys():
                # Do not substitute an unrelated local course, a foreign plan,
                # or one part of a comparison containing a missing identifier.
                return []
            owner = parent._owner
            vector = owner.encoder.queries([question])[0]
            # Prefilter the entire vector store. Never retrieve globally and
            # discard foreign hits after ranking, which can lose valid evidence.
            def query(allowed, count):
                if not allowed or not count:
                    return []
                return owner.client.query_points(
                    owner.collection, query=vector.tolist(), limit=count, with_payload=True,
                    query_filter=models.Filter(must=[models.FieldCondition(
                        key='document_id', match=models.MatchAny(any=sorted(allowed)))])).points
            wants_graduation_total = (self._prefer_matching_plan and not requested and
                bool(re.search(r'graduat|تخرج', question, re.IGNORECASE)) and
                bool(re.search(r'credit|hour|ساع|معتمد', question, re.IGNORECASE)))
            summaries = {ident for ident in self._allowed
                if parent._documents[ident].get('kind') == 'plan_summary'} if wants_graduation_total else set()
            if requested:
                exact = set().union(*(course_ids[code] for code in requested))
                points = query(exact, k)
                points += query(self._allowed - exact, k - len(points))
            elif summaries:
                # Credit totals come from the explicitly selected official
                # plan, rather than a broad handbook rule or a course row.
                points = query(summaries, k)
                points += query(self._allowed - summaries, k - len(points))
            else:
                points = query(self._allowed, k)
            hits = []
            for point in points:
                chunk = Chunk(**point.payload)
                if chunk.document_id not in self._allowed:
                    raise ValueError('Foreign document returned despite program/plan prefilter')
                hits.append(Hit(chunk, float(point.score)))
            return hits
