import io
import json
from types import SimpleNamespace

import pytest
import httpx

from scripts.evaluate_faculty_live import (PayloadProbe, ReceiptProvider,
    InferenceBoundary, plan_for, sha, validate_approval)
from rag_hackathon.generation.contracts import GenerationRequest
from rag_hackathon.generation.providers import ProviderError


@pytest.mark.parametrize('change',[
    {'approved':False},{'plan_sha256':'stale'},{'approval_reference':''},
    {'groq_free_plan_confirmed':False},{'paid_calls_approved':True},
])
def test_live_approval_must_be_explicit_and_bound(tmp_path,change):
    plan=tmp_path/'plan.json';plan.write_text('{"cases":12}',encoding='utf-8')
    approval={'approved':True,'plan_sha256':sha(plan),'approval_reference':'test-only fictional grant',
        'groq_free_plan_confirmed':True,'paid_calls_approved':False,**change}
    target=tmp_path/'approval.json';target.write_text(json.dumps(approval),encoding='utf-8')
    with pytest.raises(RuntimeError):validate_approval(plan,target,{'cases':12})


def test_changed_source_plan_invalidates_grant(tmp_path):
    plan=tmp_path/'plan.json';plan.write_text('{"cases":12}',encoding='utf-8')
    target=tmp_path/'approval.json';target.write_text(json.dumps({'approved':True,
        'plan_sha256':sha(plan),'approval_reference':'test-only fictional grant',
        'groq_free_plan_confirmed':True,'paid_calls_approved':False}),encoding='utf-8')
    with pytest.raises(RuntimeError):validate_approval(plan,target,{'cases':11})


def test_payload_preflight_never_uses_transport(monkeypatch):
    probe=PayloadProbe()
    def forbidden(*args):pytest.fail('Payload preflight cannot invoke remote generation')
    monkeypatch.setattr(probe.adapter,'generate',forbidden)
    result=probe.generate(GenerationRequest('test','en',()))
    assert json.loads(result.content)['status']=='insufficient_evidence'
    assert probe.requests and probe.requests[0]['evidence']==[]


def test_receipt_provider_stops_after_error_without_retry():
    calls=[]
    def fail(request):calls.append('call');raise ProviderError('provider_rate_limited')
    adapter=SimpleNamespace(payload_for=lambda q:None,generate=fail,last_usage=None,
        last_http_status=429,last_returned_model=None,config=SimpleNamespace(model='fixed'))
    journal=io.StringIO()
    # In-memory test journals do not implement fsync; preserve the production
    # durable writer and replace it only for this transport-free unit test.
    provider=ReceiptProvider(adapter,journal);provider.write=lambda value:journal.write(json.dumps(value)+'\n')
    with pytest.raises(ProviderError):provider.generate(None)
    with pytest.raises(ProviderError):provider.generate(None)
    assert calls==['call'] and len(provider.records)==1
    assert provider.records[0]['error']=='provider_rate_limited'


def test_http_boundary_blocks_sixth_attempt_and_other_models(tmp_path):
    payload={'model':'openai/gpt-oss-120b','service_tier':'on_demand','stream':False,'max_completion_tokens':1024}
    with (tmp_path/'journal.jsonl').open('w',encoding='utf-8') as journal:
        boundary=InferenceBoundary(5,journal)
        for _ in range(5):
            boundary.reserve(httpx.Request('POST','https://api.groq.com/openai/v1/chat/completions',json=payload))
        with pytest.raises(ProviderError):
            boundary.reserve(httpx.Request('POST','https://api.groq.com/openai/v1/chat/completions',json=payload))
        assert boundary.attempts==5
    with (tmp_path/'wrong.jsonl').open('w',encoding='utf-8') as journal:
        boundary=InferenceBoundary(5,journal)
        with pytest.raises(ProviderError):
            boundary.reserve(httpx.Request('POST','https://api.groq.com/openai/v1/chat/completions',json={**payload,'model':'other'}))
        assert boundary.attempts==0


@pytest.mark.parametrize('limit',[None,6,5])
def test_five_case_plan_requires_explicit_ceiling_and_exact_scopes(tmp_path,monkeypatch,limit):
    import scripts.evaluate_faculty_live as runner
    ids=runner.FIVE_CASE_IDS
    cases=[{'id':i,'program_id':'verified','plan_version':'2021-1','language':'ar',
        'selections':[],'expected_status':'answered','expected_reason':'supported'} for i in ids]
    (tmp_path/'live_cases.json').write_text(json.dumps(cases),encoding='utf-8')
    selected=tmp_path/'selected.json';selected.write_text(json.dumps(cases),encoding='utf-8')
    monkeypatch.setattr(runner,'DEFAULT',tmp_path)
    for name in ('chunks.json','scope_manifest.json','dataset_manifest.json'):
        (tmp_path/name).write_text('{}',encoding='utf-8')
    if limit!=5:
        with pytest.raises(ValueError):plan_for(selected,tmp_path,limit)
    else:
        assert plan_for(selected,tmp_path,limit)['maximum_attempts']==5
        cases[0]['program_id']='foreign'
        selected.write_text(json.dumps(cases),encoding='utf-8')
        with pytest.raises(ValueError):plan_for(selected,tmp_path,limit)
