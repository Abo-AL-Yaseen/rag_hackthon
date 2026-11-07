"""Prepare an offline faculty evaluation; live execution requires new approval.

Never reuse the historical synthetic smoke runner's authorization. This runner
uses FacultyRuntime and the existing scoped index, with no ingestion or fallback.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import threading
import time
from unittest.mock import patch

import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rag_hackathon.faculty_runtime import FacultyRuntime
from rag_hackathon.generation.contracts import ProviderResult
from rag_hackathon.generation.providers import (OpenAICompatibleProvider, ProviderConfig,
    RemoteCallApproval, ProviderError, load_provider_environment)

DEFAULT=ROOT/'.local/final_qa_20261107'
SETTINGS={'LLM_PROVIDER':'groq','GROQ_BASE_URL':'https://api.groq.com/openai/v1',
    'GROQ_MODEL':'openai/gpt-oss-120b','GROQ_REASONING_EFFORT':'low',
    'ALLOW_FREE_API_CALLS':'true','ALLOW_PAID_API_CALLS':'false','GROQ_FREE_PLAN_CONFIRMED':'true',
    'API_TIMEOUT_SECONDS':'30','MAX_OUTPUT_TOKENS':'1024','LLM_TEMPERATURE':'0','LLM_TOP_P':'1',
    'LLM_RESPONSE_FORMAT':'json_object','LLM_MAX_INPUT_BYTES':'24000',
    'LLM_REASONING_ENABLED':'','LLM_INPUT_PRICE_CEILING':'','LLM_OUTPUT_PRICE_CEILING':''}
BOUND_CODE=('scripts/evaluate_faculty_live.py','src/rag_hackathon/faculty_runtime.py',
    'src/rag_hackathon/academic_decisions.py','src/rag_hackathon/runtime_catalog.py',
    'src/rag_hackathon/course_catalog.py',
    'src/rag_hackathon/generation/academic_extractive.py',
    'src/rag_hackathon/retrieval/scoped.py','src/rag_hackathon/service.py',
    'src/rag_hackathon/generation/providers.py','src/rag_hackathon/generation/prompts.py',
    'src/rag_hackathon/generation/selections.py','src/rag_hackathon/generation/contracts.py')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def save(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def index_hashes(path):return {str(p.relative_to(path)):sha(p) for p in path.rglob('*') if p.is_file() and p.name!='.lock'}

FIVE_CASE_IDS=('L01','L02','L05','L07','L10')

def plan_for(cases_path,index,maximum_attempts=None):
    cases=load(cases_path)
    five_case=len(cases)==5 and maximum_attempts==5
    if five_case:
        originals={c['id']:c for c in load(DEFAULT/'live_cases.json')}
        if tuple(c['id'] for c in cases)!=FIVE_CASE_IDS:
            raise ValueError('Five-case approval is restricted to L01,L02,L05,L07,L10')
        for c in cases:
            reference=originals[c['id']]
            if any(c[k]!=reference[k] for k in ('program_id','plan_version','language','selections','expected_status','expected_reason')):
                raise ValueError('Five-case scope and reference bindings must match the verified pack')
    elif not 10<=len(cases)<=12 or len({c['id'] for c in cases})!=len(cases):
        raise ValueError('Require original 10-12 cases or explicit restricted five-case approval')
    limit=len(cases) if maximum_attempts is None else maximum_attempts
    if type(limit) is not int or not 1<=limit<=len(cases):
        raise ValueError('Bounded integer attempt ceiling required')
    return {'cases_sha256':sha(cases_path),'index_path':str(index.resolve()),
        'index_bindings':{name:sha(index/name) for name in ('chunks.json','scope_manifest.json','dataset_manifest.json')},
        'code_bindings':{name:sha(ROOT/name) for name in BOUND_CODE},
        'settings':SETTINGS,'maximum_attempts':limit,'paid_budget_usd':'0',
        'billing_basis':'Operator must verify the account is on Groq Free; local flags do not verify billing.',
        'model_basis':'Existing repository configuration; availability is unverified until an authorized run.'}

class PayloadProbe:
    is_mock=True
    def __init__(self):
        self.adapter=OpenAICompatibleProvider(ProviderConfig.from_env({**SETTINGS,'GROQ_API_KEY':'offline-placeholder'}))
        self.requests=[]
    def generate(self,request):
        payload=self.adapter.payload_for(request)
        self.requests.append({'bytes':len(json.dumps(payload,ensure_ascii=False).encode('utf-8')),
            'evidence':[h.as_dict() for h in request.evidence]})
        return ProviderResult('{"status":"insufficient_evidence","reason":"missing_evidence","claims":[]}')

def prepare(cases_path,index,out,maximum_attempts=None):
    plan=plan_for(cases_path,index,maximum_attempts)
    out.mkdir(parents=True,exist_ok=True)
    before=index_hashes(index);probe=PayloadProbe();rows=[]
    with patch('socket.socket.connect',side_effect=RuntimeError('Preparation blocks all networking')):
        rt=FacultyRuntime.open(index,probe)
        try:
            for c in load(cases_path):
                initial=len(probe.requests)
                response=rt.ask(c['question'],language=c['language'],program_id=c['program_id'],plan_version=c['plan_version'])
                request=probe.requests[-1] if len(probe.requests)>initial else None
                refs=c.get('selections',[])
                required_found=all(any(h['document_id']==s['document_id'] and s['excerpt'] in h['text'] for h in request['evidence']) for s in refs) if request else not refs
                rows.append({'case_id':c['id'],'provider_would_be_called':request is not None,
                    'payload_bytes':request['bytes'] if request else 0,'required_evidence_found':required_found,
                    'preflight_reason':response.reason,'passed':required_found and response.status!='error'})
        finally:rt.close()
    if before!=index_hashes(index):raise RuntimeError('Index changed')
    save(out/'live_preflight.json',{'passed':all(r['passed'] for r in rows),'cases':rows,
        'remote_calls':0,'index_unchanged':True,'generation':'NO LLM: payload validation only'})
    if not all(r['passed'] for r in rows):raise RuntimeError('Local preflight failed; review live_preflight.json')
    save(out/'live_plan.json',plan)
    template=out/'approval.template.json'
    if not template.exists():
        save(template,{'approved':False,'plan_sha256':sha(out/'live_plan.json'),
            'approval_reference':'','groq_free_plan_confirmed':False,'paid_calls_approved':False})
    print(json.dumps({'preflight':'PASS','cases':len(rows),'maximum_attempts':plan['maximum_attempts'],
        'would_call_provider':sum(r['provider_would_be_called'] for r in rows),'remote_calls':0,
        'plan_sha256':sha(out/'live_plan.json'),'approval':'NOT GRANTED'}))

def validate_approval(plan_path,approval_path,expected_plan):
    plan=load(plan_path);approval=load(approval_path)
    if (plan!=expected_plan or approval.get('approved') is not True
        or approval.get('plan_sha256')!=sha(plan_path)
        or not isinstance(approval.get('approval_reference'),str) or not approval['approval_reference'].strip()
        or approval.get('groq_free_plan_confirmed') is not True or approval.get('paid_calls_approved') is not False):
        raise RuntimeError('New explicit plan-bound user approval and Free-account confirmation required')
    return plan

class ReceiptProvider:
    is_mock=False
    def __init__(self,adapter,journal):self.adapter=adapter;self.journal=journal;self.records=[];self.stopped=False
    def write(self,value):
        self.journal.write(json.dumps(value,ensure_ascii=False)+'\n');self.journal.flush();os.fsync(self.journal.fileno())
    def generate(self,request):
        if self.stopped:raise ProviderError('remote_calls_disabled')
        self.adapter.payload_for(request)
        record={'attempt':len(self.records)+1,'error':None,
            'evidence':[h.as_dict() for h in request.evidence] if request is not None else []}
        self.write({'event':'attempt_reserved','attempt':record['attempt']})
        start=time.perf_counter()
        try:
            result=self.adapter.generate(request)
            record['draft_content']=result.content
            return result
        except ProviderError as error:
            record['error']=error.code;self.stopped=True;raise
        finally:
            record.update(usage=self.adapter.last_usage,http_status=self.adapter.last_http_status,
                returned_model_matches=self.adapter.last_returned_model==self.adapter.config.model,
                provider_ms=(time.perf_counter()-start)*1000,
                rate_limits=getattr(self.adapter,'last_rate_limits',{}))
            if not record['returned_model_matches'] or record['usage'] is None:self.stopped=True
            self.records.append(record);self.write({'event':'attempt_completed',**record})


class InferenceBoundary:
    """Independent cap at HTTP send; rejects all other URLs/models/methods."""
    def __init__(self,maximum_attempts,journal):
        self.maximum_attempts=maximum_attempts;self.attempts=0
        self.journal=journal;self.lock=threading.Lock()

    def reserve(self,request):
        with self.lock:
            payload=json.loads(request.content)
            if (request.method!='POST' or str(request.url)!='https://api.groq.com/openai/v1/chat/completions'
                or payload.get('model')!='openai/gpt-oss-120b' or payload.get('service_tier')!='on_demand'
                or payload.get('stream') is not False or payload.get('max_completion_tokens',4097)>1024
                or self.attempts>=self.maximum_attempts):
                raise ProviderError('remote_calls_disabled')
            self.attempts+=1
            self.journal.write(json.dumps({'event':'http_attempt_reserved','attempt':self.attempts})+'\n')
            self.journal.flush();os.fsync(self.journal.fileno())

def live(args):
    if args.approval_file is None or args.env_file is None:
        raise RuntimeError('--approval-file and --env-file required; no historical authorization applies')
    plan_path=args.output/'live_plan.json'
    plan=validate_approval(plan_path,args.approval_file,plan_for(args.cases,args.index,args.max_attempts))
    settings=load_provider_environment(args.env_file)
    if any(settings.get(k,'')!=v for k,v in SETTINGS.items()):
        raise RuntimeError('Settings differ from the reviewed plan; remote evaluation disabled')
    config=ProviderConfig.from_env(settings)
    marker=args.output/'live.used'
    if marker.exists():raise RuntimeError('Authorization already consumed; no rerun permitted')
    before=index_hashes(args.index)
    # Finish model/index initialization while all networking is disabled.
    with patch('socket.socket.connect',side_effect=RuntimeError('Startup must remain offline')):
        rt=FacultyRuntime.open(args.index)
    try:
        with marker.open('x',encoding='utf-8') as f:
            json.dump({'plan_sha256':sha(plan_path),'maximum_attempts':plan['maximum_attempts'],
                'created_utc':datetime.now(timezone.utc).isoformat()},f)
        with (args.output/'live_attempts.jsonl').open('x',encoding='utf-8') as journal:
            approval=RemoteCallApproval(base_url=config.base_url,model=config.model,max_attempts=plan['maximum_attempts'])
            provider=ReceiptProvider(OpenAICompatibleProvider(config,approval=approval),journal)
            boundary=InferenceBoundary(plan['maximum_attempts'],journal)
            original_send=httpx.Client.send
            last_send=[None]
            def bounded_send(client,request,*positional,**keywords):
                # Pace successful calls before transmission; never retry one.
                if last_send[0] is not None:
                    time.sleep(max(0,31-(time.monotonic()-last_send[0])))
                boundary.reserve(request)
                last_send[0]=time.monotonic()
                return original_send(client,request,*positional,**keywords)
            rt.service.provider=provider
            rows=[]
            for c in load(args.cases):
                initial=len(provider.records)
                with patch('httpx.Client.send',new=bounded_send):
                    response=rt.ask(c['question'],language=c['language'],program_id=c['program_id'],plan_version=c['plan_version'])
                receipt=provider.records[-1] if len(provider.records)>initial else None
                rows.append({'case_id':c['id'],'response':response.model_dump(mode='json'),'receipt':receipt,
                    'status_matches_reference':response.status==c['expected_status'],
                    'reason_matches_reference':response.reason==c['expected_reason'],
                    'semantic_answer_review':'PENDING: manually compare every claim and cited source with frozen references'})
                save(args.output/'live_results.json',{'rows':rows,'attempts':boundary.attempts,
                    'maximum_attempts':plan['maximum_attempts'],'paid_calls':0,'no_retries_or_fallback':True,
                    'cost_basis':'Free account confirmation, not an independently verified bill',
                    'llm_quality_score':'PENDING human review; schema/copy validity is insufficient'})
                if response.status=='error' or provider.stopped:break
    finally:
        rt.close()
        save(args.output/'live_index_preservation.json',{'unchanged':before==index_hashes(args.index)})

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases',type=Path,default=DEFAULT/'live_cases.json')
    p.add_argument('--index',type=Path,default=ROOT/'data/index/engineering_faculty_20261107_v1')
    p.add_argument('--output',type=Path,default=DEFAULT)
    p.add_argument('--max-attempts',type=int)
    p.add_argument('--live',action='store_true');p.add_argument('--approval-file',type=Path);p.add_argument('--env-file',type=Path)
    args=p.parse_args()
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1')
    if args.live:live(args)
    else:prepare(args.cases,args.index,args.output,args.max_attempts)

if __name__=='__main__':main()
