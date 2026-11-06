"""Attempt accounting and safe telemetry; no live requests in these tests."""
import json
from types import SimpleNamespace

import httpx
import pytest

from rag_hackathon.generation.providers import OpenAICompatibleProvider,ProviderError
from rag_hackathon.generation.contracts import ProviderResult,GenerationRequest
from rag_hackathon.service import RAGService
from scripts.run_groq_smoke import SmokeProvider,run
from test_grounded_service import FixedRetriever,hit,draft
from test_groq_configuration import settings
from rag_hackathon.generation.providers import ProviderConfig


def test_numeric_rate_headers_and_status_are_allowlisted():
    provider=OpenAICompatibleProvider(ProviderConfig.from_env(settings()),transport=httpx.MockTransport(
        lambda _:httpx.Response(429,headers={'x-ratelimit-limit-tokens':'8000',
            'x-ratelimit-reset-tokens':'1m2.4s','x-ratelimit-remaining-tokens':'private-value',
            'authorization':'private-value'},text='private response body')))
    with pytest.raises(ProviderError): provider.generate(GenerationRequest('question','en',()))
    assert provider.last_http_status==429
    assert provider.last_rate_limits=={'x-ratelimit-limit-tokens':'8000','x-ratelimit-reset-tokens':'1m2.4s'}


class SimulatedRemote:
    is_mock=False  # Test double only; never invokes HTTP.
    config=SimpleNamespace(model='openai/gpt-oss-120b')
    last_usage={'prompt_tokens':100,'completion_tokens':20,'total_tokens':120}
    last_http_status=200
    last_rate_limits={}
    last_returned_model='openai/gpt-oss-120b'
    def payload_for(self,request): return {}
    def generate(self,request): return ProviderResult(draft())


def test_attempt_guard_has_exactly_two_durable_reservations(tmp_path):
    path=tmp_path/'audit.jsonl'
    with path.open('w',encoding='utf-8') as stream:
        provider=SmokeProvider(SimulatedRemote(),stream)
        request=GenerationRequest('question','en',(hit(),))
        provider.generate(request); provider.generate(request)
        with pytest.raises(ProviderError,match='remote_calls_disabled'): provider.generate(request)
    rows=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
    assert sum(row['event']=='attempt_reserved' for row in rows)==2
    assert len(provider.records)==2


@pytest.mark.parametrize('fails',[False,True])
def test_runner_only_runs_two_cases_and_stops_on_error(tmp_path,fails):
    class Remote(SimulatedRemote):
        def generate(self,request):
            if fails: raise ProviderError('provider_rate_limited')
            return super().generate(request)
    cases=[{'id':ident,'question':'question','language':lang,'reference_answer':'twelve days',
            'answerable':True,'relevant_sources':[{'document_id':'library','page':1}]} for ident,lang in [('q01','ar'),('q02','en'),('extra','en')]]
    with (tmp_path/'journal.jsonl').open('w',encoding='utf-8') as journal:
        provider=SmokeProvider(Remote(),journal)
        engine=RAGService(FixedRetriever([hit()]),provider)
        run(engine,provider,cases,[hit().chunk],tmp_path/'result.json')
    result=json.loads((tmp_path/'result.json').read_text(encoding='utf-8'))
    assert result['attempts']==(1 if fails else 2)
    assert result['full_evaluation_executed'] is False
    assert [r['case']['id'] for r in result['tests']]==(['q01'] if fails else ['q01','q02'])
