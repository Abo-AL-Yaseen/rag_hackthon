"""Metadata checks use HTTP mocks only; never authenticate to a real provider."""
from decimal import Decimal
import json

import httpx
from pydantic import SecretStr
import pytest

from rag_hackathon.openrouter_preflight import check_key, check_model, PreflightError


def key_data(**changes):
    data={'limit':.10,'limit_remaining':.10,'usage':0,'limit_reset':None,
          'label':'must-not-escape','hash':'must-not-escape'}
    data.update(changes)
    return data


def transport(data):
    return httpx.MockTransport(lambda _:httpx.Response(200,json={'data':data}))


def test_key_cap_saves_numeric_fields_only():
    result=check_key(SecretStr('fixture-only'),minimum_remaining='.005952',transport=transport(key_data()))
    assert Decimal(result['limit_usd'])==Decimal('.10') and result['verified']
    assert 'must-not-escape' not in json.dumps(result) and 'fixture-only' not in json.dumps(result)


@pytest.mark.parametrize('changes',[{'limit':None},{'limit':1},{'limit_reset':'daily'},
                                   {'limit_remaining':.09,'usage':.01},{'usage':-1},
                                   {'is_management_key':True},{'limit_remaining':float('nan')}])
def test_invalid_or_previously_used_keys_block_inference(changes):
    with pytest.raises(PreflightError):
        check_key(SecretStr('fixture-only'),minimum_remaining='.005952',transport=transport(key_data(**changes)))


def test_usage_after_run_allows_used_key_and_returns_remaining():
    result=check_key(SecretStr('fixture-only'),minimum_remaining=0,require_unused=False,
                     transport=transport(key_data(limit_remaining=.099,usage=.001)))
    assert result['remaining_usd']=='0.099'


def endpoint(**changes):
    data={'provider_name':'fixture provider','status':0,
          'supported_parameters':['max_tokens','temperature','top_p','response_format','reasoning'],
          'pricing':{'prompt':'.00000017','completion':'.00000025'}}
    data.update(changes)
    return data


PLAN={'model':'qwen/qwen3.5-9b','base_url':'https://openrouter.ai/api/v1',
      'input_usd_per_million':'.17','output_usd_per_million':'.25'}


def test_public_model_check_has_no_auth_header():
    def handle(request):
        assert 'authorization' not in request.headers
        return httpx.Response(200,json={'data':{'id':PLAN['model'],'endpoints':[endpoint()]}})
    result=check_model(PLAN,transport=httpx.MockTransport(handle))
    assert result['endpoints'][0]['eligible_at_approved_limits']


@pytest.mark.parametrize('changes',[{'status':-5},{'pricing':{'prompt':'.000001','completion':'.000001'}},
                                   {'supported_parameters':[]}])
def test_unavailable_expensive_or_incompatible_routes_block(changes):
    with pytest.raises(PreflightError):
        check_model(PLAN,transport=transport({'id':PLAN['model'],'endpoints':[endpoint(**changes)]}))


def test_absent_key_does_not_make_a_request():
    with pytest.raises(PreflightError,match='credential_missing'):
        check_key(SecretStr(''),minimum_remaining=0,transport=httpx.MockTransport(
            lambda _:pytest.fail('No request without a configured key')))


def test_live_runner_stops_after_two_http_mock_calls(tmp_path,monkeypatch):
    from pathlib import Path
    from scripts import evaluate_phase3 as runner
    from rag_hackathon.generation.providers import OpenAICompatibleProvider, ProviderConfig
    from rag_hackathon.live_evaluation import plan_digest
    import rag_hackathon.openrouter_preflight as preflight
    from rag_hackathon.service import RAGService
    from test_grounded_service import FixedRetriever, FixedProvider, hit, draft
    root=Path(__file__).resolve().parents[1]
    plan_path=root/'config/phase3_live_plan.json'
    config=ProviderConfig(name='openrouter',base_url=PLAN['base_url'],model=PLAN['model'],
                          api_key=SecretStr('fixture-only'),allow_paid_calls=True,top_p=1,
                          response_format='json_object',reasoning_enabled=False,max_input_bytes=12000,
                          input_price_ceiling=.17,output_price_ceiling=.25)
    monkeypatch.setattr(ProviderConfig,'from_env',lambda _:config)
    monkeypatch.setattr(runner,'verify_bindings',lambda *args:None)
    monkeypatch.setattr(preflight,'check_model',lambda _: {'model':PLAN['model']})
    def checked_key(*args,**kwargs):
        return {'usage_usd':'0' if kwargs.get('require_unused',True) else '.000044',
                'remaining_usd':'.10' if kwargs.get('require_unused',True) else '.099956'}
    monkeypatch.setattr(preflight,'check_key',checked_key)
    calls=[]
    def handle(request):
        calls.append(json.loads(request.content))
        assert len(calls)<=2
        content=draft() if len(calls)==1 else json.dumps({'status':'insufficient_evidence','reason':'missing_evidence','claims':[]})
        return httpx.Response(200,json={'model':PLAN['model'],
            'usage':{'prompt_tokens':100,'completion_tokens':20,'total_tokens':120},
            'choices':[{'finish_reason':'stop','message':{'content':content}}]})
    monkeypatch.setattr(runner,'OpenAICompatibleProvider',lambda cfg,approval:OpenAICompatibleProvider(
        cfg,approval=approval,transport=httpx.MockTransport(handle)))
    approval_path=tmp_path/'approval.json'
    approval_path.write_text(json.dumps({'approved':True,'scope':'two_smoke_attempts_only',
        'plan_sha256':plan_digest(plan_path),'approval_reference':'unit-test-only',
        'provider_key_spend_limit_confirmed':True}))
    cases=json.loads((root/'data/sample/phase3_questions.json').read_text(encoding='utf-8'))['questions']
    retriever=FixedRetriever([hit()])
    service=RAGService(retriever,FixedProvider(draft()))
    output=tmp_path/'smoke.json'
    runner.live_run(plan_path,approval_path,service,retriever,[hit().chunk],cases,output)
    result=json.loads(output.read_text(encoding='utf-8'))
    assert len(calls)==2 and result['cases']==[]
    assert [c['id'] for c in result['smoke']]==['q01','q14']
    assert len(result['usage_audit'])==2 and result['remaining_lifetime_attempts']==24
    assert result['actual_key_usage_delta_usd']=='0.000044'
