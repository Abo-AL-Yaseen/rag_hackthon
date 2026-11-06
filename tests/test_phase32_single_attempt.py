"""Offline tests for the new single-request guard. No real transport used."""
import json
from types import SimpleNamespace

import pytest

from scripts.verify_phase32_arabic import OneRequestProvider
from rag_hackathon.generation.contracts import GenerationRequest,ProviderResult
from rag_hackathon.generation.providers import ProviderError


@pytest.mark.parametrize('error',[False,True])
def test_single_request_guard_cannot_retry_even_after_failure(tmp_path,error):
    class FixtureProvider:
        is_mock=False  # Test double, never network.
        last_http_status=429 if error else 200
        last_usage=None if error else {'prompt_tokens':10,'completion_tokens':5,'total_tokens':15}
        last_rate_limits={}
        last_returned_model='fixture-model'
        config=SimpleNamespace(model='fixture-model')
        calls=0
        def payload_for(self,request): return {}
        def generate(self,request):
            self.calls+=1
            if error: raise ProviderError('provider_rate_limited')
            return ProviderResult('{}')
    path=tmp_path/'journal.jsonl'
    provider=FixtureProvider()
    with path.open('w',encoding='utf-8') as journal:
        observed=OneRequestProvider(provider,journal)
        request=GenerationRequest('fixture','ar',())
        if error:
            with pytest.raises(ProviderError): observed.generate(request)
        else: observed.generate(request)
        with pytest.raises(ProviderError,match='remote_calls_disabled'): observed.generate(request)
        assert provider.calls==observed.attempts==1
    records=[json.loads(line) for line in path.read_text().splitlines()]
    assert [r['event'] for r in records]==['reserved','completed']
