"""Exactly one authorized inference opportunity; no API metadata call or retry."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rag_hackathon.diagnostics import LocalDiagnostics
from rag_hackathon.generation.contracts import GenerationRequest,RAGResponse
from rag_hackathon.generation.providers import (OpenAICompatibleProvider,ProviderConfig,
    ProviderError,RemoteCallApproval,load_provider_environment)
from rag_hackathon.generation.prompts import PROMPT_VERSION
from rag_hackathon.generation.selections import candidate_spans
from rag_hackathon.preparation import build_preparation_service
from rag_hackathon.rag_evaluation import RecordingRetriever,audit_sources
from rag_hackathon.service import RAGService


class OneRequestProvider:
    is_mock=False

    def __init__(self,provider,journal):
        if provider.is_mock:
            raise RuntimeError('Actual provider required')
        self.provider,self.journal=provider,journal
        self.attempts=0
        self.receipt=None

    def write(self,value):
        self.journal.write(json.dumps(value)+'\n')
        self.journal.flush()
        os.fsync(self.journal.fileno())

    def generate(self,request):
        if self.attempts:
            raise ProviderError('remote_calls_disabled')
        self.provider.payload_for(request)
        self.attempts=1
        receipt={'attempt':1,'error':None,'supplied_source_ids':[h.chunk.chunk_id for h in request.evidence]}
        self.write({'event':'reserved','attempt':1})
        start=time.perf_counter()
        try:
            return self.provider.generate(request)
        except ProviderError as error:
            receipt['error']=error.code
            raise
        finally:
            receipt.update({'provider_latency_ms':(time.perf_counter()-start)*1000,
                            'http_status':self.provider.last_http_status,'usage':self.provider.last_usage,
                            'rate_limits':self.provider.last_rate_limits,
                            'returned_model_matches':self.provider.last_returned_model==self.provider.config.model})
            self.receipt=receipt
            self.write({'event':'completed',**receipt})


def main():
    cfg=ProviderConfig.from_env(load_provider_environment(ROOT/'.env'))
    if (cfg.name!='groq' or cfg.model!='openai/gpt-oss-120b' or cfg.allow_paid_calls
            or not cfg.allow_free_calls or not cfg.groq_free_plan_confirmed
            or cfg.base_url.rstrip('/')!='https://api.groq.com/openai/v1'
            or cfg.response_format!='json_object' or cfg.max_output_tokens>1024
            or cfg.timeout_seconds>30 or cfg.max_input_bytes>12000 or PROMPT_VERSION!='evidence-selection-v2'):
        raise RuntimeError('Free-plan/local generation guard failed; zero API calls allowed')
    manifest=json.loads((ROOT/'docs/evidence/phase31_source_manifest.json').read_text())
    for name in ('src/rag_hackathon/service.py','src/rag_hackathon/generation/prompts.py',
                 'src/rag_hackathon/generation/selections.py','src/rag_hackathon/diagnostics.py'):
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=manifest[name]:
            raise RuntimeError('Tested Phase 3.1 code changed; no live verification allowed')
    case=next(c for c in json.loads((ROOT/'data/sample/phase3_questions.json').read_text(encoding='utf-8'))['questions'] if c['id']=='q01')
    historical=json.loads((ROOT/'docs/evidence/groq_live_smoke_results.json').read_text(encoding='utf-8'))
    if case['question']!=historical['tests'][0]['case']['question'] or case['language']!='ar':
        raise RuntimeError('Previously failing question changed')
    marker=ROOT/'.local/phase32-one-arabic.used'
    output=ROOT/'docs/evidence/phase32_live_arabic_result.json'
    journal_path=ROOT/'docs/evidence/phase32_live_arabic_attempt.jsonl'
    if marker.exists() or output.exists() or journal_path.exists():
        raise RuntimeError('This authorization is consumed or prior evidence exists; do not repeat')
    with patch('socket.socket.connect',side_effect=RuntimeError('Local preflight is offline')):
        base,index,chunks=build_preparation_service(ROOT,index_path=ROOT/'data/index/phase3')
        try:
            hits=index.search(case['question'],3)
            spans=candidate_spans(hits)
            expected=next(s for s in spans.values() if s.chunk_id==historical['tests'][0]['retrieved'][0]['chunk_id']
                          and '\u0627\u062b\u0646\u064a \u0639\u0634\u0631' in s.excerpt)
            OpenAICompatibleProvider(cfg).payload_for(GenerationRequest(case['question'],'ar',tuple(hits)))
            if RAGResponse.model_json_schema()!=json.loads((ROOT/'docs/rag_response.schema.json').read_text()):
                raise RuntimeError('Backend response schema changed')
        except Exception:
            index.close()
            raise
    marker.parent.mkdir(exist_ok=True)
    try:
        with marker.open('x',encoding='utf-8') as file:
            json.dump({'scope':'Phase 3.2 user authorization: ONE Arabic Groq Free inference request',
                       'created_utc':datetime.now(timezone.utc).isoformat(),'maximum_requests':1,
                       'paid_budget_usd':'0','prompt_version':PROMPT_VERSION,
                       'expected_selection_id':expected.selection_id},file)
        with journal_path.open('x',encoding='utf-8') as journal:
            approval=RemoteCallApproval(base_url=cfg.base_url,model=cfg.model,max_attempts=1)
            observed=OneRequestProvider(OpenAICompatibleProvider(cfg,approval=approval),journal)
            diagnostic=LocalDiagnostics(ROOT/'.local/phase32-diagnostics')
            retrieval=RecordingRetriever(index)
            engine=RAGService(retrieval,observed,policy=base.policy,diagnostics=diagnostic)
            response=engine.ask(case['question'],language='ar')  # The ONLY inference opportunity.
            trace=json.loads(diagnostic.last_path.read_text(encoding='utf-8')) if diagnostic.last_path else None
            sanitized=trace['sanitized_raw_model_draft'].get('draft') if trace else None
            selected_ids=sanitized.get('selection_ids') if isinstance(sanitized,dict) else None
            checks={'one_attempt':observed.attempts==1,
                    'http_200':observed.receipt is not None and observed.receipt['http_status']==200,
                    'model_matches':observed.receipt is not None and observed.receipt['returned_model_matches'],
                    'answered':response.status=='answered' and response.reason=='supported',
                    'native_expected_selection':selected_ids==[expected.selection_id],
                    'canonical_arabic_answer':len(response.claims)==1 and response.claims[0].text==expected.excerpt,
                    'correct_citation':len(response.sources)==1 and response.sources[0].chunk_id==expected.chunk_id
                        and response.sources[0].document_name=='synthetic_library.json' and response.sources[0].page_number==1
                        and response.sources[0].supporting_excerpt==expected.excerpt,
                    'real_generation_mode':response.mode=='remote',
                    'contract_valid':RAGResponse.model_validate(response.model_dump())==response,
                    'validation_accepted':trace is not None and trace['stage']=='accepted'}
            result={'created_utc':datetime.now(timezone.utc).isoformat(),'synthetic_corpus':True,
                    'generation':'real Groq Free inference','model':cfg.model,'prompt_version':PROMPT_VERSION,
                    'maximum_authorized_requests':1,'actual_attempts':observed.attempts,'remaining_authorized_requests':0,
                    'separate_api_preflight_requests':0,'question':case['question'],'response':response.model_dump(mode='json'),
                    'retrieved':[{'chunk_id':h.chunk.chunk_id,'document_name':h.chunk.source,'page':h.chunk.page,'score':h.score}
                                 for h in retrieval.last_hits],
                    'expected_selection_id':expected.selection_id,'selected_ids':selected_ids,
                    'citation_audit':audit_sources(response,retrieval.last_hits),'diagnostic':trace,'receipt':observed.receipt,
                    'automated_checks':checks,'automated_outcome':'PASS' if all(checks.values()) else 'FAIL',
                    'semantic_review':'pending direct inspection of original synthetic source',
                    'account_status_basis':'Existing explicit user Free-plan confirmation and unchanged local guards; no billing API query',
                    'paid_calls_enabled':False,'expected_free_plan_charge_usd':'0','recorded_provider_cost_usd':None,
                    'full_evaluation_executed':False}
            output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps({'attempts':observed.attempts,'outcome':result['automated_outcome'],'status':response.status,'remaining_authorized_requests':0}))
    finally:
        index.close()


if __name__=='__main__': main()
