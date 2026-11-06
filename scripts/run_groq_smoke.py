"""Single-use two-attempt runner. No retries, evaluation loop, model change or billing API."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rag_hackathon.generation.providers import (OpenAICompatibleProvider,ProviderConfig,ProviderError,
    RemoteCallApproval,load_provider_environment)
from rag_hackathon.generation.prompts import PROMPT_VERSION
from rag_hackathon.preparation import build_preparation_service
from rag_hackathon.rag_evaluation import RecordingRetriever,audit_sources
from rag_hackathon.evaluation import precision_recall_at_k
from rag_hackathon.service import RAGService
from rag_hackathon.diagnostics import LocalDiagnostics


class SmokeProvider:
    is_mock=False

    def __init__(self,provider,journal):
        if provider.is_mock:
            raise RuntimeError('Real provider required')
        self.provider,self.journal=provider,journal
        self.attempts=0
        self.records=[]

    def write(self,record):
        self.journal.write(json.dumps(record,ensure_ascii=False)+'\n')
        self.journal.flush()
        os.fsync(self.journal.fileno())

    def generate(self,request):
        if self.attempts>=2:
            raise ProviderError('remote_calls_disabled')
        self.provider.payload_for(request)
        self.attempts+=1
        record={'attempt':self.attempts,'question':request.question,'language':request.language,
                'evidence_sent':[h.as_dict() for h in request.evidence],'error':None}
        self.write({'event':'attempt_reserved','attempt':self.attempts})
        start=time.perf_counter()
        try:
            return self.provider.generate(request)
        except ProviderError as error:
            record['error']=error.code
            raise
        finally:
            record.update({'provider_latency_ms':(time.perf_counter()-start)*1000,
                           'http_status':self.provider.last_http_status,
                           'rate_limits':self.provider.last_rate_limits,
                           'usage':self.provider.last_usage,
                           'returned_model_matches':self.provider.last_returned_model==self.provider.config.model})
            self.records.append(record)
            self.write({'event':'attempt_completed',**record})


def run(engine,provider,cases,chunks,output):
    records=[]
    recording=RecordingRetriever(engine.retriever)
    engine.retriever=recording
    for case in cases:
        if provider.attempts>=2:
            break
        before=provider.attempts
        response=engine.ask(case['question'],language=case['language'])
        receipt=provider.records[-1] if provider.attempts>before else None
        relevant=[c.chunk_id for c in chunks if any(c.document_id==s['document_id'] and c.page==s['page'] for s in case['relevant_sources'])]
        ids=[h.chunk.chunk_id for h in recording.last_hits]
        records.append({'case':case,'response':response.model_dump(mode='json'),
                        'retrieved':[h.as_dict() for h in recording.last_hits],
                        'retrieval_metrics':{str(k):precision_recall_at_k(ids,relevant,k) for k in (1,3)},
                        'citation_audit':audit_sources(response,recording.last_hits),'receipt':receipt,
                        'semantic_review':'pending direct evidence inspection',
                        'provider_reported_cost_usd':None})
        output.write_text(json.dumps({'synthetic':True,'generation':'real Groq inference',
            'model':'openai/gpt-oss-120b','prompt_version':PROMPT_VERSION,
            'attempts':provider.attempts,'maximum_authorized_attempts':2,'remaining_smoke_attempts':2-provider.attempts,
            'account_status_basis':'Explicit user confirmation of Free plan plus local free-call guards; no independent billing API verification',
            'paid_budget_usd':'0','provider_reported_cost_usd':None,
            'cost_note':'No monetary cost field returned by the API is assumed. Free-plan $0 is based on confirmed account status, not a provider invoice.',
            'tests':records,'full_evaluation_executed':False},ensure_ascii=False,indent=2),encoding='utf-8')
        if (response.status=='error' or receipt is None or receipt['error']
                or receipt['usage'] is None or not receipt['returned_model_matches']):
            break
    return records


def main():
    cfg=ProviderConfig.from_env(load_provider_environment(ROOT/'.env'))
    if (cfg.name!='groq' or cfg.model!='openai/gpt-oss-120b' or cfg.allow_paid_calls
        or not cfg.allow_free_calls or not cfg.groq_free_plan_confirmed
        or cfg.response_format!='json_object' or cfg.max_output_tokens>1024
        or cfg.timeout_seconds>30 or cfg.max_input_bytes>12000):
        raise RuntimeError('Approved free configuration does not match; no inference permitted')
    preflight=json.loads((ROOT/'docs/evidence/groq_live_preflight.json').read_text())
    if preflight.get('passed') is not True or preflight.get('user_confirmed_free_plan') is not True:
        raise RuntimeError('Successful read-only preflight and Free-plan confirmation required')
    output=ROOT/'docs/evidence/groq_live_smoke_results.json'
    journal=ROOT/'docs/evidence/groq_live_smoke_attempts.jsonl'
    if output.exists() or journal.exists():
        raise RuntimeError('Prior run evidence exists; no repeated authorization')
    cases=json.loads((ROOT/'data/sample/phase3_questions.json').read_text(encoding='utf-8'))['questions']
    cases=[next(c for c in cases if c['id']==ident) for ident in ('q01','q02')]
    # All local initialization and pre-retrieval must succeed with networking blocked.
    with patch('socket.socket.connect',side_effect=RuntimeError('Local preflight must remain offline')):
        base,index,chunks=build_preparation_service(ROOT,index_path=ROOT/'data/index/phase3')
        try:
            for case in cases:
                hits=index.search(case['question'],3)
                if not hits or not any(h.chunk.document_id==s['document_id'] and h.chunk.page==s['page'] for h in hits for s in case['relevant_sources']):
                    raise RuntimeError('Expected synthetic evidence missing; do not spend an attempt')
        except Exception:
            index.close()
            raise
    marker=ROOT/'.local/groq-free-smoke.used'
    marker.parent.mkdir(exist_ok=True)
    try:
        # Exclusive persistent consumption prevents re-running this user's two-attempt grant.
        with marker.open('x',encoding='utf-8') as file:
            json.dump({'scope':'two Groq Free attempts, q01 Arabic and q02 English',
                       'created_utc':datetime.now(timezone.utc).isoformat(),
                       'provider_source_sha256':hashlib.sha256((ROOT/'src/rag_hackathon/generation/providers.py').read_bytes()).hexdigest(),
                       'max_attempts':2,'paid_budget_usd':'0'},file)
        with journal.open('x',encoding='utf-8') as stream:
            approval=RemoteCallApproval(base_url=cfg.base_url,model=cfg.model,max_attempts=2)
            provider=SmokeProvider(OpenAICompatibleProvider(cfg,approval=approval),stream)
            engine=RAGService(index,provider,policy=base.policy,
                              diagnostics=LocalDiagnostics(ROOT/'.local/rag-diagnostics'))
            records=run(engine,provider,cases,chunks,output)
            print(json.dumps({'attempts':provider.attempts,'statuses':[r['response']['status'] for r in records],
                              'full_evaluation_executed':False}))
    finally:
        index.close()


if __name__=='__main__':
    main()
