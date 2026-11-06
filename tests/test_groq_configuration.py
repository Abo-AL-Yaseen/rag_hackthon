"""Groq configuration and wire tests; synthetic keys and HTTP mocks exclusively."""
import json
from pathlib import Path
import subprocess

from dotenv import dotenv_values
import httpx
import pytest

from rag_hackathon.generation.contracts import GenerationRequest
from rag_hackathon.generation.providers import (ProviderConfig, ProviderError, RemoteCallApproval,
                                               OpenAICompatibleProvider, provider_from_env,
                                               load_provider_environment)

ROOT=Path(__file__).resolve().parents[1]
REQUEST=GenerationRequest('What does the evidence establish?','en',())


def settings(**changes):
    result={'LLM_PROVIDER':'groq','GROQ_API_KEY':'synthetic-test-key',
            'GROQ_BASE_URL':'https://api.groq.com/openai/v1','GROQ_MODEL':'openai/gpt-oss-120b',
            'LLM_MODEL':'must-not-be-selected','LLM_API_KEY':'must-not-be-selected',
            'LLM_RESPONSE_FORMAT':'json_object','LLM_TEMPERATURE':'0','LLM_TOP_P':'1'}
    result.update(changes)
    return result


def test_groq_factory_uses_all_groq_settings_and_hides_key():
    provider=provider_from_env(settings())
    assert isinstance(provider,OpenAICompatibleProvider)
    assert provider.config.name=='groq'
    assert provider.config.model=='openai/gpt-oss-120b'
    assert provider.config.base_url=='https://api.groq.com/openai/v1'
    assert provider.config.api_key.get_secret_value()=='synthetic-test-key'
    assert 'synthetic-test-key' not in repr(provider.config)


@pytest.mark.parametrize('changes',[{'GROQ_API_KEY':''},{'GROQ_MODEL':''},
    {'GROQ_BASE_URL':'https://example.invalid/openai/v1'},{'ALLOW_PAID_API_CALLS':'true'},
    {'GROQ_REASONING_EFFORT':'none'},{'LLM_REASONING_ENABLED':'false'},
    {'LLM_INPUT_PRICE_CEILING':'.17','LLM_OUTPUT_PRICE_CEILING':'.25'}])
def test_invalid_groq_configuration_fails_closed(changes):
    with pytest.raises(ProviderError,match='provider_configuration'):
        provider_from_env(settings(**changes))


def test_correct_model_specific_payload_and_official_endpoint(caplog,capsys):
    cfg=ProviderConfig.from_env(settings())
    calls=[]
    def handle(request):
        calls.append(1)
        assert str(request.url)=='https://api.groq.com/openai/v1/chat/completions'
        assert request.headers['Authorization']=='Bearer synthetic-test-key'
        data=json.loads(request.content)
        assert data['model']==cfg.model
        assert data['response_format']=={'type':'json_object'}
        assert data['temperature']==0 and data['top_p']==1
        assert data['max_completion_tokens']==1024 and 'max_tokens' not in data
        assert data['service_tier']=='on_demand' and data['stream'] is False
        assert data['reasoning_effort']=='low' and data['include_reasoning'] is False
        assert not {'provider','models','reasoning','tools','reasoning_format'} & data.keys()
        return httpx.Response(200,json={'model':cfg.model,'usage':{'prompt_tokens':50,'completion_tokens':20,'total_tokens':70},
            'choices':[{'finish_reason':'stop','message':{'content':'{}'}}]})
    provider=OpenAICompatibleProvider(cfg,transport=httpx.MockTransport(handle))
    assert provider.generate(REQUEST).content=='{}'
    assert len(calls)==1 and provider.last_usage['total_tokens']==70
    assert 'synthetic-test-key' not in caplog.text+capsys.readouterr().out


@pytest.mark.parametrize('free,confirmed',[('false','false'),('true','false'),('false','true')])
def test_free_calls_require_both_enable_and_plan_confirmation(free,confirmed):
    cfg=ProviderConfig.from_env(settings(ALLOW_FREE_API_CALLS=free,GROQ_FREE_PLAN_CONFIRMED=confirmed))
    approval=RemoteCallApproval(base_url=cfg.base_url,model=cfg.model,max_attempts=2)
    with pytest.raises(ProviderError,match='remote_calls_disabled'): approval.consume(cfg)
    assert approval.remaining==2


def test_two_free_attempts_do_not_enable_paid_providers():
    cfg=ProviderConfig.from_env(settings(ALLOW_FREE_API_CALLS='true',GROQ_FREE_PLAN_CONFIRMED='true'))
    approval=RemoteCallApproval(base_url=cfg.base_url,model=cfg.model,max_attempts=2)
    approval.consume(cfg); approval.consume(cfg)
    with pytest.raises(ProviderError,match='remote_calls_disabled'): approval.consume(cfg)
    other=ProviderConfig.from_env({'LLM_PROVIDER':'together','TOGETHER_API_KEY':'fixture',
        'LLM_MODEL':'fixture','ALLOW_FREE_API_CALLS':'true','GROQ_FREE_PLAN_CONFIRMED':'true'})
    with pytest.raises(ProviderError):
        RemoteCallApproval(base_url=other.base_url,model=other.model,max_attempts=1).consume(other)


def test_free_provider_still_requires_operator_approval_without_network(monkeypatch):
    cfg=ProviderConfig.from_env(settings(ALLOW_FREE_API_CALLS='true',GROQ_FREE_PLAN_CONFIRMED='true'))
    monkeypatch.setattr(httpx.Client,'stream',lambda *a,**k:pytest.fail('No network without approval'))
    with pytest.raises(ProviderError,match='remote_calls_disabled'):
        OpenAICompatibleProvider(cfg).generate(REQUEST)


def test_private_file_loading_is_explicit_and_process_overrides(tmp_path,monkeypatch):
    path=tmp_path/'.env'
    path.write_text('\n'.join(k+'='+v for k,v in settings().items()),encoding='utf-8')
    before=__import__('os').environ.get('GROQ_API_KEY')
    values=load_provider_environment(path,environ={'GROQ_MODEL':'openai/gpt-oss-20b'})
    assert values['GROQ_MODEL']=='openai/gpt-oss-20b'
    assert __import__('os').environ.get('GROQ_API_KEY')==before
    for key in settings(): monkeypatch.delenv(key,raising=False)
    monkeypatch.setenv('GROQ_MODEL','openai/gpt-oss-20b')
    provider=provider_from_env(env_file=path)
    assert provider.config.model=='openai/gpt-oss-20b'
    assert provider_from_env({}).is_mock
    with pytest.raises(ProviderError): provider_from_env({},env_file=path)
    with pytest.raises(ProviderError): provider_from_env(env_file=tmp_path/'absent.env')


@pytest.mark.parametrize('status,code',[(401,'provider_authentication'),(429,'provider_rate_limited'),(500,'provider_error')])
def test_groq_errors_do_not_retry_fallback_or_log_keys(status,code,caplog,capsys):
    calls=[]
    def handle(request):
        calls.append(1)
        return httpx.Response(status,text='synthetic-test-key private provider error')
    provider=OpenAICompatibleProvider(ProviderConfig.from_env(settings()),transport=httpx.MockTransport(handle))
    with pytest.raises(ProviderError) as error: provider.generate(REQUEST)
    assert str(error.value)==code and calls==[1]
    assert 'synthetic-test-key' not in caplog.text+capsys.readouterr().out


def test_actual_gitignore_rules_exclude_private_environment(tmp_path):
    result=subprocess.run(['git','init','--quiet',str(tmp_path)],capture_output=True)
    assert result.returncode==0
    (tmp_path/'.gitignore').write_bytes((ROOT/'.gitignore').read_bytes())
    result=subprocess.run(['git','-C',str(tmp_path),'check-ignore','--no-index','.env','.env.local','.env.example'],
                          capture_output=True,text=True)
    assert result.returncode==0
    assert result.stdout.splitlines()==['.env','.env.local']


def test_public_environment_templates_contain_no_credentials():
    for path in [ROOT/'.env.example',ROOT/'config/groq.env.example']:
        values=dotenv_values(path)
        if any(v for k,v in values.items() if k.endswith('_API_KEY')):
            pytest.fail('A public environment template contains a credential; values suppressed')


def test_offline_audit_never_claims_to_verify_account_or_prints_credentials():
    from scripts.check_groq_config import audit
    result=audit(settings(ALLOW_FREE_API_CALLS='true',GROQ_FREE_PLAN_CONFIRMED='true'),private_file_exists=True)
    assert result['local_configuration_ready']
    assert result['account_free_plan_independently_verified'] is False
    assert result['live_inference_attempts']==0 and not result['inference_authorized_this_turn']
    assert 'synthetic-test-key' not in json.dumps(result)
