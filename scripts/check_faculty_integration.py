"""Offline ASGI integration check using the EXISTING faculty index.

This tests the optional handoff harness, not an unavailable teammate Backend or
Frontend. Never ingests data, rebuilds vectors, loads .env or calls an LLM.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import socket
import statistics
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',
    ALLOW_FREE_API_CALLS='false',ALLOW_PAID_API_CALLS='false',GROQ_FREE_PLAN_CONFIRMED='false',LLM_PROVIDER='mock')

from fastapi.testclient import TestClient
from examples.faculty_backend_handoff import create_app
from rag_hackathon.faculty_runtime import FacultyRuntime
from rag_hackathon.generation.contracts import RAGResponse
from rag_hackathon.generation.providers import DeterministicMockProvider
from rag_hackathon.service import RAGService
from rag_hackathon.workspace import cached_encoder


def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def hashes(folder):
    return {str(p.relative_to(folder)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob('*') if p.is_file() and p.name!='.lock'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index',type=Path,default=ROOT/'data/index/engineering_faculty_20261107_v1')
    parser.add_argument('--output',type=Path,default=ROOT/'.local/final_integration_20261107')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    before=hashes(args.index)
    manifest=json.loads((args.index/'dataset_manifest.json').read_text())
    binding=json.loads((args.index/'scope_manifest.json').read_text(encoding='utf-8'))
    docs={d['document_id']:d for d in binding['documents']}
    cases=[]
    def add(ident,q,program,plan,document=None,status='answered',reason='supported',guard=False):
        d=docs[document] if document else None
        cases.append({'id':ident,'question':q,'language':'ar','program_id':program,'plan_version':plan,
          'expected_status':status,'expected_reason':reason,'guard_must_skip_provider':guard,
          **({'selections':[{'document_id':document,'page':d['engine_page_number'],'excerpt':d['reference_quote']}]} if d else {})})
    add('civil_credit','بخطة الهندسة المدنية 2021-1، كم ساعة مساق 10871112؟','civil-engineering','2021-1','eng_civil-engineering_2021-1_10871112_ar')
    add('geomatics_credit','بخطة هندسة المساحة والجيوماتكس 2025-1، كم ساعة مساق 10871112؟','geomatics-engineering','2025-1','eng_geomatics-engineering_2025-1_10871112_ar')
    add('architecture_credit','بخطة الهندسة المعمارية 2025-1، كم ساعة مساق 11221102؟','architectural-engineering','2025-1','eng_architectural-engineering_2025-1_11221102_ar')
    add('computer_prerequisite','بخطة هندسة الحاسوب 2021-1، شو متطلب تركيب بيانات وخوارزميات 10636211؟','computer-engineering','2021-1','eng_computer-engineering_2021-1_10636211_ar')
    add('computer_graduation','حسب خطة هندسة الحاسوب المنشورة 2021-1 تحديداً، كم مجموع ساعات التخرج؟','computer-engineering','2021-1','eng_computer-engineering_2021-1_summary_ar')
    add('civil_graduation','حسب خطة الهندسة المدنية المنشورة 2021-1 تحديداً، كم مجموع ساعات التخرج؟','civil-engineering','2021-1','eng_civil-engineering_2021-1_summary_ar')
    add('regulation_withdrawal','لحد إمتى بقدر أسحب مادة بعد أسبوع السحب والإضافة؟',None,None,'policy_late_withdrawal')
    add('uncertain_and_or','بخطة هندسة الحاسوب، شو المتطلبات السابقة لتحليل الأنظمة والإشارات 10641373؟','computer-engineering','2021-1','eng_computer-engineering_2021-1_10641373_ar',
        status='insufficient_evidence',reason='ambiguous',guard=True)
    add('uncertain_colored','شو المتطلب السابق لمختبر فيزياء عامة للهندسة 10221115 في الهندسة المدنية؟','civil-engineering','2021-1','eng_civil-engineering_2021-1_10221115_ar',
        status='insufficient_evidence',reason='ambiguous',guard=True)
    add('blank_prerequisite','شو المتطلب السابق لتصميم دوائر رقمية 1 10636221 بخطة هندسة الحاسوب؟','computer-engineering','2021-1','eng_computer-engineering_2021-1_10636221_ar',
        status='insufficient_evidence',reason='missing_evidence',guard=True)
    add('missing_course','كم ساعة مساق 99999999 بخطة الهندسة المدنية؟','civil-engineering','2021-1',
        status='insufficient_evidence',reason='missing_evidence',guard=True)
    add('wrong_plan','كم ساعة مساق 10871112؟','civil-engineering','2025-1',
        status='insufficient_evidence',reason='outdated_sources',guard=True)
    add('missing_plan','شو متطلب المساق 10636211؟','computer-engineering',None,
        status='insufficient_evidence',reason='ambiguous',guard=True)
    add('unselected_program','كم ساعة مساق 10871112؟',None,None,
        status='insufficient_evidence',reason='missing_evidence',guard=True)
    add('outside_faculty','شو خطة تخصص طب الأسنان؟',None,None,status='insufficient_evidence',reason='out_of_scope')
    rules=[{'question':c['question'],**({'selections':c['selections']} if c.get('selections') else
        {'refusal_reason':c['expected_reason']})} for c in cases if c['id'] not in ('wrong_plan','unselected_program')]
    provider=DeterministicMockProvider(rules)
    save(args.output/'offline_cases.json',cases)
    external_attempts=[];original=socket.socket.connect
    def local_only(sock,address):
        if isinstance(address,tuple) and address[0] in ('127.0.0.1','::1'):
            return original(sock,address)
        external_attempts.append('blocked')
        raise AssertionError('Integration validation blocks external connections')
    factory_calls=[];state={};results=[]
    def factory():
        factory_calls.append('initialize')
        runtime=FacultyRuntime.open(args.index,provider)
        state['runtime']=runtime;state['engine_id']=id(runtime.service)
        return runtime
    app=create_app(factory)
    with patch('socket.socket.connect',new=local_only), \
         patch('rag_hackathon.faculty_runtime.RAGService',wraps=RAGService) as service_init, \
         patch('rag_hackathon.workspace.cached_encoder',wraps=cached_encoder) as model_init, \
         patch.object(provider,'generate',wraps=provider.generate) as generate:
        tick=time.perf_counter()
        with TestClient(app) as client:
            startup_ms=(time.perf_counter()-tick)*1000
            assert client.get('/health').json()=={'status':'ready','mode':'mock','contract_version':'1.0.0'}
            assert len(client.get('/rag/programs').json())==15
            for c in cases:
                headers={}
                if c['program_id'] is not None:headers['X-RAG-Program']=c['program_id']
                if c['plan_version'] is not None:headers['X-RAG-Plan']=c['plan_version']
                initial_calls=generate.call_count;tick=time.perf_counter()
                response=client.post('/rag/answer',headers=headers,json={'question':c['question'],'language':'ar'})
                http_ms=(time.perf_counter()-tick)*1000
                assert response.status_code==200,(c['id'],response.status_code)
                payload=response.json();RAGResponse.model_validate(payload)
                assert payload['contract_version']=='1.0.0' and payload['mode']=='mock'
                assert payload['status']==c['expected_status'] and payload['reason']==c['expected_reason'],(c['id'],payload)
                if c['guard_must_skip_provider']:assert generate.call_count==initial_calls,c['id']
                if payload['status']=='answered':
                    assert len(payload['sources'])==1
                    source=payload['sources'][0];expected=c['selections'][0]
                    assert source['document_id']==expected['document_id'] and source['supporting_excerpt']==expected['excerpt']
                    d=docs[source['document_id']]
                    assert d['scope']=='regulations' or (d['program_id']==c['program_id'] and d['plan_version']==c['plan_version'])
                    assert source['page_number']==d['engine_page_number'] and source['document_name']==d['source_file']
                    if d['scope']=='program':assert 'study_plan='+c['plan_version'] in d['source_url']
                else:assert not payload['sources'] and not payload['claims']
                assert id(state['runtime'].service)==state['engine_id']
                results.append({'case_id':c['id'],'program_id':c['program_id'],'plan_version':c['plan_version'],
                    'passed':True,'http_ms':http_ms,'provider_invocations':generate.call_count-initial_calls,
                    'payload':payload,'source_locators':[state['runtime'].source_locator(s['document_id']) for s in payload['sources']]})
            assert client.post('/rag/answer',json={'question':'x','language':'ar','program_id':'civil-engineering'}).status_code==422
            assert client.post('/rag/answer',json={'question':'x','language':'fr'}).status_code==422
            assert client.post('/rag/answer',json={'question':'   ','language':'ar'}).json()['reason']=='invalid_request'
            positive=cases[:3]
            def concurrent_request(c):
                r=client.post('/rag/answer',headers={'X-RAG-Program':c['program_id'],'X-RAG-Plan':c['plan_version']},
                              json={'question':c['question'],'language':'ar'})
                assert r.status_code==200
                p=r.json();RAGResponse.model_validate(p)
                assert p['sources'][0]['document_id']==c['selections'][0]['document_id']
                return {'case_id':c['id'],'engine_ms':p['latency']['total_ms'],'passed':True}
            with ThreadPoolExecutor(max_workers=6) as pool:
                concurrent_results=list(pool.map(concurrent_request,positive*6))
            assert factory_calls==['initialize'] and service_init.call_count==1 and model_init.call_count==1
            lifecycle={'runtime_initializations':len(factory_calls),'rag_service_initializations':service_init.call_count,
                       'embedding_model_initializations':model_init.call_count}
        assert state['runtime']._index._closed
    after=hashes(args.index);assert before==after,'Index bytes changed unexpectedly'
    save(args.output/'http_results.json',results)
    save(args.output/'concurrency_results.json',concurrent_results)
    save(args.output/'index_preservation.json',{'unchanged':True,'file_hashes':before})
    latencies=[r['http_ms'] for r in results]
    engine=[r['payload']['latency']['total_ms'] for r in results]
    summary={'team_backend':'BLOCKED: no teammate application or branch available in inspected repository',
       'team_frontend':'BLOCKED: no Frontend source/package.json available',
       'fastapi_handoff_harness':'PASS (in-process ASGI, not a deployed team application)',
       'http_cases_passed':len(results),'concurrent_requests_passed':len(concurrent_results),
       'programs_tested':sorted({c['program_id'] for c in cases if c['program_id'] and c['expected_status']=='answered'}),
       'startup_ms':startup_ms,'http_latency_ms':{'min':min(latencies),'median':statistics.median(latencies),'max':max(latencies)},
       'engine_latency_ms':{'min':min(engine),'median':statistics.median(engine),'max':max(engine)},
       **lifecycle,'chunks':manifest['chunks'],'index_path':str(args.index.resolve()),
       'dataset_path':str((ROOT/'data/processed/engineering_faculty_20261107').resolve()),
       'index_preserved':True,'embeddings_rebuilt':False,'contract_version':'1.0.0','schema_failures':0,
       'foreign_program_or_plan_hits':0,'credit_precedence':'Explicit matching official study plan; handbook totals do not override it',
       'uncertain_prerequisites':'Refused before provider invocation','remote_llm_calls':0,'paid_calls':0,
       'external_connection_attempts':len(external_attempts),'generation':'SCRIPTED OFFLINE MOCK; no general LLM accuracy claim',
       'server_runner':'uvicorn unavailable in existing .venv','regression_suite':'pending'}
    assert not external_attempts
    save(args.output/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
