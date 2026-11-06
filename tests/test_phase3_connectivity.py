from decimal import Decimal
import json
from pathlib import Path

import httpx
from pydantic import SecretStr
import pytest

from examples.direct_rag import answer_json,make_engine
from rag_hackathon.generation.accounting import CostBudget,Rates,parse_usage
from rag_hackathon.generation.contracts import GenerationRequest,RAGResponse
from rag_hackathon.generation.providers import OpenAICompatibleProvider,ProviderConfig,ProviderError
from rag_hackathon.live_evaluation import AuditedProvider,plan_digest,plan_estimate,require_approval,verify_bindings

ROOT=Path(__file__).resolve().parents[1]
REQUEST=GenerationRequest('What can the sources establish?','en',())


def cfg(**kwargs):
    values=dict(name='openrouter',base_url='https://openrouter.ai/api/v1',model='qwen/qwen3.5-9b',
                api_key=SecretStr('fixture-not-a-real-credential'))
    values.update(kwargs)
    return ProviderConfig(**values)


def rates(): return Rates(Decimal('.17'),Decimal('.25'),'official fixture snapshot','2026-11-06')


def test_configurable_parameters_and_routing_caps():
    env={'LLM_PROVIDER':'openrouter','OPENROUTER_API_KEY':'fixture-not-a-real-credential',
         'LLM_MODEL':'qwen/qwen3.5-9b','API_TIMEOUT_SECONDS':'12','MAX_OUTPUT_TOKENS':'512',
         'LLM_TEMPERATURE':'0.2','LLM_TOP_P':'0.9','LLM_RESPONSE_FORMAT':'json_object',
         'LLM_REASONING_ENABLED':'false','LLM_MAX_INPUT_BYTES':'12000',
         'LLM_INPUT_PRICE_CEILING':'.17','LLM_OUTPUT_PRICE_CEILING':'.25'}
    config=ProviderConfig.from_env(env)
    payload=OpenAICompatibleProvider(config).payload_for(REQUEST)
    assert config.timeout_seconds==12 and payload['max_tokens']==512
    assert payload['temperature']==.2 and payload['top_p']==.9
    assert payload['response_format']=={'type':'json_object'}
    assert payload['reasoning']=={'enabled':False}
    assert payload['provider']['allow_fallbacks'] is False
    assert payload['provider']['max_price']=={'prompt':.17,'completion':.25,'request':0}


@pytest.mark.parametrize('changes',[{'temperature':float('nan')},{'top_p':2},{'response_format':'anything'},
                                    {'reasoning_enabled':True,'name':'together'},
                                    {'input_price_ceiling':.17}])
def test_invalid_generation_configuration(changes):
    with pytest.raises(ProviderError,match='provider_configuration'): cfg(**changes)


@pytest.mark.parametrize('exc,code',[(httpx.ConnectError,'provider_error'),(httpx.ConnectTimeout,'provider_timeout'),
                                    (httpx.ReadTimeout,'provider_timeout'),(httpx.WriteTimeout,'provider_timeout')])
def test_network_errors_have_one_attempt_and_no_secret_text(exc,code):
    calls=[]
    def handler(request):
        calls.append(1)
        raise exc('private header fixture-not-a-real-credential',request=request)
    provider=OpenAICompatibleProvider(cfg(),transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderError) as error: provider.generate(REQUEST)
    assert str(error.value)==code and calls==[1] and provider.last_usage is None


def test_usage_retained_on_truncated_response_and_cost_not_double_counted():
    usage={'prompt_tokens':100,'completion_tokens':20,'total_tokens':120,
           'completion_tokens_details':{'reasoning_tokens':12},'cost':.0001}
    provider=OpenAICompatibleProvider(cfg(),transport=httpx.MockTransport(lambda _:httpx.Response(200,json={
        'model':'qwen/qwen3.5-9b','usage':usage,
        'choices':[{'finish_reason':'length','message':{'content':'partial'}}]})))
    with pytest.raises(ProviderError): provider.generate(REQUEST)
    assert provider.last_usage['reasoning_tokens']==12
    assert rates().estimate(100,20)==Decimal('0.000022')
    assert provider.last_returned_model=='qwen/qwen3.5-9b'


@pytest.mark.parametrize('usage',[None,{}, {'prompt_tokens':True,'completion_tokens':1,'total_tokens':2},
                                 {'prompt_tokens':2,'completion_tokens':-1,'total_tokens':1},
                                 {'prompt_tokens':2,'completion_tokens':1,'total_tokens':99}])
def test_missing_or_invalid_usage_is_unknown_not_zero(usage): assert parse_usage(usage) is None


def test_budget_reservation_and_unknown_usage_stop():
    budget=CostBudget(rates(),max_usd='.10',max_attempts=26)
    for _ in range(26): budget.reserve()
    assert budget.committed==Decimal('0.077376')
    with pytest.raises(RuntimeError): budget.reserve()
    another=CostBudget(rates(),max_usd='.10',max_attempts=26)
    ticket=another.reserve()
    assert another.settle(ticket,None) is None
    assert another.committed==another.per_call and another.stopped
    with pytest.raises(RuntimeError): another.reserve()


def test_oversized_input_rejected_before_network_and_approval():
    provider=OpenAICompatibleProvider(cfg(max_input_bytes=16),transport=httpx.MockTransport(
        lambda _:pytest.fail('No request permitted')))
    with pytest.raises(ProviderError): provider.generate(REQUEST)


def test_audited_http_mock_records_numeric_usage_only():
    provider=OpenAICompatibleProvider(cfg(),transport=httpx.MockTransport(lambda _:httpx.Response(200,json={
        'model':'qwen/qwen3.5-9b','usage':{'prompt_tokens':100,'completion_tokens':20,'total_tokens':120},
        'choices':[{'finish_reason':'stop','message':{'content':'{}'}}]})))
    audited=AuditedProvider(provider,CostBudget(rates(),max_usd='.10',max_attempts=2))
    audited.generate(REQUEST)
    assert audited.records[0]['estimated_cost_from_usage_usd']=='0.000022'
    assert 'fixture-not-a-real-credential' not in json.dumps(audited.records)


def test_approval_is_false_by_default_and_single_use(tmp_path):
    plan_path=ROOT/'config/phase3_live_plan.json'
    approval_path=tmp_path/'approval.json'
    approval={'approved':False,'plan_sha256':plan_digest(plan_path),'approval_reference':'unit-test-only',
              'provider_key_spend_limit_confirmed':True}
    approval_path.write_text(json.dumps(approval))
    with pytest.raises(RuntimeError): require_approval(plan_path,approval_path)
    assert not approval_path.with_name('approval.json.used').exists()
    approval['approved']=True
    approval_path.write_text(json.dumps(approval))
    assert require_approval(plan_path,approval_path)['max_attempts']==26
    with pytest.raises(FileExistsError): require_approval(plan_path,approval_path)


def test_public_schema_unchanged_and_direct_backend_example():
    assert RAGResponse.model_json_schema()==json.loads((ROOT/'docs/rag_response.schema.json').read_text())
    class EmptyRetriever:
        def search(self,*args): return []
    engine=make_engine(EmptyRetriever(),environment={})
    result=answer_json(engine,'Question?')
    assert result['contract_version']=='1.0.0' and result['status']=='insufficient_evidence'
    RAGResponse.model_validate(result)


def test_plan_cost_is_explicit_estimate_and_case_count_matches():
    plan=json.loads((ROOT/'config/phase3_live_plan.json').read_text())
    data=json.loads((ROOT/'data/sample/phase3_questions.json').read_text(encoding='utf-8'))
    assert len(data['questions'])==24
    assert plan['max_attempts']==len(data['questions'])+plan['smoke_calls']
    assert plan_estimate(plan)['all_attempts_upper_estimate_usd']=='0.077376'
    assert len(data['unsupported_multi_turn_probes'])==2


def test_changed_corpus_or_cases_cannot_reuse_approval(tmp_path):
    from rag_hackathon.ingestion import corpus_hash
    from test_grounded_service import hit
    import hashlib
    paths={'evaluation_sha256':'data/sample/phase3_questions.json',
           'prompt_sha256':'src/rag_hackathon/generation/prompts.py',
           'provider_sha256':'src/rag_hackathon/generation/providers.py'}
    plan={}
    for key,name in paths.items():
        p=tmp_path/name
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text('fixture')
        plan[key]=hashlib.sha256(p.read_bytes()).hexdigest()
    chunks=[hit().chunk]
    plan['corpus_sha256']=corpus_hash(chunks)
    verify_bindings(plan,tmp_path,chunks)
    (tmp_path/paths['evaluation_sha256']).write_text('different cases')
    with pytest.raises(RuntimeError,match='changed'): verify_bindings(plan,tmp_path,chunks)
