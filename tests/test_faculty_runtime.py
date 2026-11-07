from concurrent.futures import ThreadPoolExecutor
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from examples.faculty_backend_handoff import create_app
from examples.faculty_backend_handoff import offline_runtime_from_env
from rag_hackathon.faculty_runtime import FacultyRuntime
from rag_hackathon.generation.contracts import RAGResponse
from rag_hackathon.generation.providers import DeterministicMockProvider
from rag_hackathon.schema import Chunk, Hit


class FakeIndex:
    def __init__(self, documents, hits):
        self.documents = documents
        self.hits = hits
        self.closed = 0

    def for_program(self, program, plan, *, prefer_matching_plan=False):
        def search(question, k):
            return [h for h in self.hits if self.documents[h.chunk.document_id]['program_id']==program
                    and self.documents[h.chunk.document_id]['plan_version']==plan][:k]
        return SimpleNamespace(search=search)

    def for_regulations(self):
        return SimpleNamespace(search=lambda q,k:[])

    def close(self):
        self.closed += 1


@pytest.fixture
def runtime():
    docs=[];hits=[];rules=[]
    for i, program in enumerate(('civil','geomatics','computer')):
        ident=program+'_row';quote=f'Course {program}: {i+2} credits.'
        docs.append({'document_id':ident,'scope':'program','program_id':program,'plan_version':'2021-1',
            'kind':'course','course_code':'10871112','quality_flags':[],
            'reference_quote':quote,'program_name_ar':program,'program_name_en':program})
        chunk=Chunk(ident,ident,program+'.html',1,quote,0,len(quote),'2021-1')
        hits.append(Hit(chunk,0.9))
        rules.append({'question':program+' credits','selections':[{'document_id':ident,'page':1,'excerpt':quote}]})
    mapping={d['document_id']:d for d in docs};index=FakeIndex(mapping,hits)
    result=FacultyRuntime(index,docs,DeterministicMockProvider(rules))
    yield result
    if not index.closed:result.close()


def test_one_engine_is_reused_for_sequential_program_changes(runtime):
    engine=runtime.service
    for program in ('civil','geomatics','computer','civil'):
        payload=runtime(program+' credits',program_id=program,plan_version='2021-1')
        RAGResponse.model_validate(payload)
        assert payload['sources'][0]['document_id']==program+'_row'
        assert runtime.service is engine


def test_concurrent_selections_do_not_mutate_shared_retriever(runtime):
    def ask(program):
        return runtime(program+' credits',program_id=program,plan_version='2021-1')
    selected=['civil','geomatics','computer']*8
    with ThreadPoolExecutor(max_workers=6) as pool:
        results=list(pool.map(ask,selected))
    assert all(result['sources'][0]['document_id']==program+'_row' for program,result in zip(selected,results))


@pytest.mark.parametrize('program,plan,reason',[('civil',None,'ambiguous'),('civil','2025-1','outdated_sources'),
                                               ('unavailable','2021-1','outdated_sources')])
def test_missing_or_unknown_selection_refuses_without_fallback(runtime,program,plan,reason):
    response=runtime('civil credits',program_id=program,plan_version=plan)
    assert response['status']=='insufficient_evidence' and response['reason']==reason
    assert not response['sources']


def test_uncertain_prerequisites_refuse_before_provider_generation(runtime):
    runtime._documents['civil_row']['quality_flags']=['intergroup_AND_OR_not_explicit']
    response=runtime('شو المتطلب السابق لمساق 10871112؟',language='ar',program_id='civil',plan_version='2021-1')
    assert response['reason']=='ambiguous' and not response['sources']
    assert 'غير واضحة' in response['answer']
    # The same row still supports a credit-hours question.
    assert runtime('civil credits',program_id='civil',plan_version='2021-1')['status']=='answered'


def test_missing_prerequisite_cell_does_not_mean_no_prerequisite(runtime):
    runtime._documents['civil_row']['reference_quote']='المتطلبات السابقة: غير مذكور في الخانة المنشورة'
    response=runtime('شو المتطلب السابق 10871112؟',language='ar',program_id='civil',plan_version='2021-1')
    assert response['reason']=='missing_evidence' and not response['sources']


def test_invalid_language_preserves_engine_error_contract(runtime):
    response=runtime('civil credits',language='fr',program_id='civil',plan_version='2021-1')
    assert response['status']=='error' and response['reason']=='invalid_request' and response['language']=='en'


@pytest.mark.parametrize('question',[
    'According to plan 2025-1, how many credits is 10871112?',
    'بخطة ٢٠٢٥-١ كم ساعة مساق 10871112؟',
    'Compare plans 2021-1 and 2025-1 for 10871112',
])
def test_question_cannot_override_selected_plan(runtime,monkeypatch,question):
    def forbidden(*args):pytest.fail('Conflicting plan must refuse before generation')
    monkeypatch.setattr(runtime.service.provider,'generate',forbidden)
    response=runtime(question,program_id='civil',plan_version='2021-1')
    assert response['status']=='insufficient_evidence' and response['reason']=='ambiguous'
    assert not response['sources'] and not response['claims']


@pytest.mark.parametrize('question',[
    'شو لازم أكون مخلص قبل ما أنزل مساق 10871112؟',
    'بصير آخذ مساق 10871112؟',
    'What do I need to complete before taking course 10871112?',
])
def test_colloquial_and_english_eligibility_do_not_bypass_uncertainty(runtime,monkeypatch,question):
    runtime._documents['civil_row']['quality_flags']=['intergroup_AND_OR_not_explicit']
    def forbidden(*args):pytest.fail('Uncertain prerequisites must refuse before generation')
    monkeypatch.setattr(runtime.service.provider,'generate',forbidden)
    response=runtime(question,program_id='civil',plan_version='2021-1')
    assert response['reason']=='ambiguous' and not response['sources']


def test_fastapi_lifespan_and_v1_body(runtime):
    calls=[]
    app=create_app(lambda:(calls.append('init') or runtime))
    with TestClient(app) as client:
        assert client.get('/health').json()['contract_version']=='1.0.0'
        for program in ('civil','geomatics','computer'):
            response=client.post('/rag/answer',headers={'X-RAG-Program':program,'X-RAG-Plan':'2021-1'},
                                 json={'question':program+' credits','language':'ar'})
            assert response.status_code==200
            RAGResponse.model_validate(response.json())
            assert response.json()['sources'][0]['document_id']==program+'_row'
        assert client.post('/rag/answer',json={'question':'x','language':'en','provider':'groq'}).status_code==422
        assert len(client.get('/rag/programs').json())==3
    assert calls==['init'] and runtime._index.closed==1


@pytest.mark.parametrize('key,value',[('LLM_PROVIDER','groq'),('ALLOW_FREE_API_CALLS','true'),
                                     ('ALLOW_PAID_API_CALLS','true')])
def test_offline_handoff_refuses_live_settings_before_initialization(monkeypatch,key,value):
    for name,default in [('LLM_PROVIDER','mock'),('ALLOW_FREE_API_CALLS','false'),('ALLOW_PAID_API_CALLS','false')]:
        monkeypatch.setenv(name,default)
    monkeypatch.setenv(key,value)
    with pytest.raises(ValueError):offline_runtime_from_env()
