"""Opt-in local diagnostics with no question, source text, draft prose or secrets.

Retain a sanitized representation of the raw draft, never an unredacted body.
All arbitrary strings/unknown fields are withheld, even for public fixtures.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import unicodedata
import uuid

from .generation.selections import candidate_spans

REASONS={'supported','missing_evidence','out_of_scope','false_assumption','ambiguous',
         'conflicting_sources','outdated_sources','unsupported_claim','invalid_citation',
         'malformed_response','provider_timeout','provider_error','invalid_request',
         'retrieval_error','provider_authentication','provider_rate_limited',
         'remote_calls_disabled','provider_configuration'}
STAGES={'request_validation','retrieval_validation','evidence_policy','provider_transport',
        'draft_parsing','provider_refusal','claim_validation','accepted'}
DETAILS={'claim_excerpt_mismatch','unknown_chunk_id','excerpt_not_in_chunk',
         'selection_not_in_evidence','draft_schema_or_json_invalid'}
FIELDS={'status','reason','claims','text','evidence','chunk_id','excerpt','selection_ids'}


def opaque_source_id(value):
    # Canonical ingestion IDs are UUIDs. Arbitrary metadata/PII is pseudonymized.
    if re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}',value):
        return value
    return 'id_'+hashlib.sha256(value.encode('utf-8')).hexdigest()[:24]


def _digits(value):
    result=[]
    for char in value:
        try:
            result.append(str(unicodedata.decimal(char)))
        except ValueError:
            result.append(char)
    return ''.join(result)


def sanitized_raw_draft(raw, hits):
    known_chunks={h.chunk.chunk_id for h in hits}
    known_selections=set(candidate_spans(hits))
    if not isinstance(raw,str):
        return {'representation':'no_draft','comparisons':[]}
    size=len(raw.encode('utf-8',errors='replace'))
    if size>65536:
        return {'representation':'oversized_body_withheld','bytes':size,'comparisons':[]}
    try:
        data=json.loads(raw)
    except Exception:
        return {'representation':'unparseable_body_withheld','bytes':size,'comparisons':[]}

    def scrub(value,field=None,depth=0):
        if depth>8:
            return '[depth_limit]'
        if field in ('text','excerpt'):
            return {'redacted':True,'characters':len(value) if isinstance(value,str) else None}
        if field=='status':
            return value if value in ('answered','insufficient_evidence') else '[invalid_status]'
        if field=='reason':
            return value if isinstance(value,str) and value in REASONS else '[invalid_reason]'
        if field=='chunk_id':
            return opaque_source_id(value) if isinstance(value,str) and value in known_chunks else '[unrecognized_id]'
        if field=='selection_ids':
            return [v if isinstance(v,str) and v in known_selections else '[unrecognized_id]' for v in value[:4]] if isinstance(value,list) else '[invalid_ids]'
        if isinstance(value,dict):
            result={k:scrub(v,k,depth+1) for k,v in list(value.items())[:24] if k in FIELDS}
            result['withheld_unknown_fields']=sum(k not in FIELDS for k in value)
            return result
        if isinstance(value,list):
            return [scrub(v,depth=depth+1) for v in value[:8]]
        return '[withheld_value]'

    comparisons=[]
    claims=data.get('claims',[]) if isinstance(data,dict) else []
    if isinstance(claims,list):
        for claim in claims[:4]:
            if not isinstance(claim,dict) or not isinstance(claim.get('text'),str):
                continue
            refs=claim.get('evidence',[])
            if not isinstance(refs,list):
                continue
            for ref in refs[:4]:
                if not isinstance(ref,dict) or not isinstance(ref.get('excerpt'),str):
                    continue
                a,b=claim['text'],ref['excerpt']
                comparisons.append({'exact_equal':a==b,
                                    'nfc_equal':unicodedata.normalize('NFC',a)==unicodedata.normalize('NFC',b),
                                    'digit_script_equal':_digits(a)==_digits(b)})
    return {'representation':'sanitized_json_structure','bytes':size,
            'draft':scrub(data),'comparisons':comparisons,
            'warning':'Text/unknown values withheld; comparisons are diagnostics, never support evidence.'}


class LocalDiagnostics:
    def __init__(self,directory):
        self.directory=Path(directory)
        self.last_path=None

    def record(self,raw,hits,*,stage,reason,detail,status,retrieved_hits=None):
        if stage not in STAGES or reason not in REASONS or status not in ('answered','insufficient_evidence','error'):
            raise ValueError('Unknown diagnostic outcome')
        value={'created_utc':datetime.now(timezone.utc).isoformat(),'stage':stage,'reason':reason,
               'detail':detail if detail in DETAILS else None,'status':status,
               'retrieved_source_ids':[opaque_source_id(h.chunk.chunk_id) for h in (hits if retrieved_hits is None else retrieved_hits)],
               'supplied_source_ids':[opaque_source_id(h.chunk.chunk_id) for h in hits],
               'sanitized_raw_model_draft':sanitized_raw_draft(raw,hits)}
        self.directory.mkdir(parents=True,exist_ok=True)
        path=self.directory/(str(uuid.uuid4())+'.json')
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w',encoding='utf-8') as file:
            json.dump(value,file,ensure_ascii=False,indent=2)
        self.last_path=path
