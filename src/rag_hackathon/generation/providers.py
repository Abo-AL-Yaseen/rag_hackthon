"""Offline scripted mock and gated OpenAI-compatible Chat Completions adapter."""
from dataclasses import dataclass, field
import json
import math
import os
import re
import threading
from typing import Mapping
from urllib.parse import urlsplit

import httpx
from pydantic import SecretStr

from .contracts import GenerationRequest, ProviderResult
from .prompts import messages_for
from .accounting import parse_usage


class ProviderError(Exception):
    """Only allowlisted codes cross the service boundary; no raw provider errors."""
    def __init__(self, code='provider_error'):
        safe = {'provider_error','provider_timeout','malformed_response','remote_calls_disabled',
                'provider_configuration','provider_rate_limited','provider_authentication'}
        self.code = code if code in safe else 'provider_error'
        super().__init__(self.code)


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    base_url: str
    model: str
    api_key: SecretStr = field(repr=False)
    allow_paid_calls: bool = False
    timeout_seconds: float = 30
    max_output_tokens: int = 1024
    max_response_bytes: int = 65536
    temperature: float = 0.0
    top_p: float | None = None
    response_format: str = 'text'
    reasoning_enabled: bool | None = None
    max_input_bytes: int = 32000
    input_price_ceiling: float | None = None
    output_price_ceiling: float | None = None
    allow_free_calls: bool = False
    groq_free_plan_confirmed: bool = False
    groq_reasoning_effort: str | None = None

    def __post_init__(self):
        url = urlsplit(self.base_url)
        if (url.scheme != 'https' or not url.hostname or url.username or url.password
                or url.query or url.fragment or not self.model.strip()
                or not self.api_key.get_secret_value().strip()
                or not math.isfinite(self.timeout_seconds) or not 0 < self.timeout_seconds <= 120
                or not 1 <= self.max_output_tokens <= 4096 or not 1 <= self.max_response_bytes <= 262144
                or not math.isfinite(self.temperature) or not 0<=self.temperature<=2
                or self.top_p is not None and (not math.isfinite(self.top_p) or not 0<self.top_p<=1)
                or self.response_format not in ('text','json_object') or not 1<=self.max_input_bytes<=64000
                or self.reasoning_enabled is not None and (type(self.reasoning_enabled) is not bool or self.name!='openrouter')):
            raise ProviderError('provider_configuration')
        prices=(self.input_price_ceiling,self.output_price_ceiling)
        if any(p is not None for p in prices) and (self.name!='openrouter' or
                any(p is None or not math.isfinite(p) or p<0 for p in prices)):
            raise ProviderError('provider_configuration')
        if self.name=='groq' and (self.base_url.rstrip('/')!='https://api.groq.com/openai/v1'
                                  or self.allow_paid_calls):
            raise ProviderError('provider_configuration')
        if self.groq_reasoning_effort is not None and (self.name!='groq'
                or self.model not in ('openai/gpt-oss-120b','openai/gpt-oss-20b')
                or self.groq_reasoning_effort not in ('low','medium','high')):
            raise ProviderError('provider_configuration')

    @classmethod
    def from_env(cls, env: Mapping[str,str] | None = None):
        env = os.environ if env is None else env
        name = env.get('LLM_PROVIDER','mock').lower()
        prefix = {'openrouter':'OPENROUTER','together':'TOGETHER','compatible':'LLM','groq':'GROQ'}.get(name)
        if prefix is None:
            raise ProviderError('provider_configuration')
        defaults = {'openrouter':'https://openrouter.ai/api/v1','together':'https://api.together.ai/v1',
                    'groq':'https://api.groq.com/openai/v1'}
        try:
            thinking=env.get('LLM_REASONING_ENABLED','').lower()
            if thinking not in ('','true','false'):
                raise ValueError('Invalid boolean')
            model=env.get('GROQ_MODEL','') if name=='groq' else env.get('LLM_MODEL','')
            effort=env.get('GROQ_REASONING_EFFORT','low') if name=='groq' and model in ('openai/gpt-oss-120b','openai/gpt-oss-20b') else None
            return cls(name,env.get(prefix+'_BASE_URL',defaults.get(name,'')),model,
                       SecretStr(env.get(prefix+'_API_KEY','')),env.get('ALLOW_PAID_API_CALLS','false').lower()=='true',
                       float(env.get('API_TIMEOUT_SECONDS','30')),int(env.get('MAX_OUTPUT_TOKENS','1024')),
                       temperature=float(env.get('LLM_TEMPERATURE','0')),
                       top_p=float(env['LLM_TOP_P']) if env.get('LLM_TOP_P') else None,
                       response_format=env.get('LLM_RESPONSE_FORMAT','text'),
                       reasoning_enabled=None if not thinking else thinking=='true',
                       max_input_bytes=int(env.get('LLM_MAX_INPUT_BYTES','32000')),
                       input_price_ceiling=float(env['LLM_INPUT_PRICE_CEILING']) if env.get('LLM_INPUT_PRICE_CEILING') else None,
                       output_price_ceiling=float(env['LLM_OUTPUT_PRICE_CEILING']) if env.get('LLM_OUTPUT_PRICE_CEILING') else None,
                       allow_free_calls=env.get('ALLOW_FREE_API_CALLS','false').lower()=='true',
                       groq_free_plan_confirmed=env.get('GROQ_FREE_PLAN_CONFIRMED','false').lower()=='true',
                       groq_reasoning_effort=effort)
        except (ValueError, TypeError):
            raise ProviderError('provider_configuration') from None


class RemoteCallApproval:
    """Explicit server-owned approval, bound to endpoint/model and attempt count.

    Creating this object is an operator action after user approval, not a request
    parameter. Attempts count even on timeout/error; there are no automatic retries.
    Token/attempt caps are not a dollar-cost guarantee; verify current rates first.
    """
    def __init__(self, *, base_url: str, model: str, max_attempts: int):
        if not model or max_attempts < 1:
            raise ValueError('Explicit model and positive attempt cap required')
        self.base_url, self.model = base_url.rstrip('/'),model
        self.remaining = max_attempts
        self.lock = threading.Lock()

    def consume(self, config):
        with self.lock:
            enabled=(config.allow_free_calls and config.groq_free_plan_confirmed and not config.allow_paid_calls
                     if config.name=='groq' else config.allow_paid_calls)
            if (not enabled or self.remaining < 1
                    or config.base_url.rstrip('/') != self.base_url or config.model != self.model):
                raise ProviderError('remote_calls_disabled')
            self.remaining -= 1


class OpenAICompatibleProvider:
    is_mock = False

    def __init__(self, config: ProviderConfig, *, approval=None, transport=None):
        if transport is not None and not isinstance(transport,httpx.MockTransport):
            raise ProviderError('provider_configuration')
        self.config, self.approval, self.transport = config,approval,transport
        self.last_usage=None
        self.last_returned_model=None
        self.last_http_status=None
        self.last_rate_limits={}
        if transport is not None:
            self.is_mock = True

    def payload_for(self,request):
        payload={'model':self.config.model,'messages':messages_for(request),
                 'temperature':self.config.temperature,'max_tokens':self.config.max_output_tokens,'stream':False}
        if len(json.dumps(payload['messages'],ensure_ascii=False).encode())>self.config.max_input_bytes:
            raise ProviderError('provider_configuration')
        if self.config.top_p is not None:
            payload['top_p']=self.config.top_p
        if self.config.response_format=='json_object':
            payload['response_format']={'type':'json_object'}
        if self.config.reasoning_enabled is not None:
            payload['reasoning']={'enabled':self.config.reasoning_enabled}
        if self.config.input_price_ceiling is not None:
            payload['provider']={'allow_fallbacks':False,'require_parameters':True,
                                 'max_price':{'prompt':self.config.input_price_ceiling,
                                              'completion':self.config.output_price_ceiling,'request':0}}
        if self.config.name=='groq':
            payload['max_completion_tokens']=payload.pop('max_tokens')
            payload['service_tier']='on_demand'
            if self.config.groq_reasoning_effort is not None:
                payload['reasoning_effort']=self.config.groq_reasoning_effort
                payload['include_reasoning']=False
        return payload

    def generate(self, request: GenerationRequest):
        self.last_usage=None
        self.last_returned_model=None
        self.last_http_status=None
        self.last_rate_limits={}
        payload=self.payload_for(request)
        if self.transport is None:
            if self.approval is None:
                raise ProviderError('remote_calls_disabled')
            self.approval.consume(self.config)
        # No key, raw response, request contents or provider exception is logged.
        try:
            with httpx.Client(transport=self.transport, timeout=self.config.timeout_seconds,
                              follow_redirects=False, trust_env=False) as client:
                with client.stream('POST',self.config.base_url.rstrip('/')+'/chat/completions',
                                   headers={'Authorization':'Bearer '+self.config.api_key.get_secret_value()},
                                   json=payload) as response:
                    self.last_http_status=response.status_code
                    for name in ('retry-after','x-ratelimit-limit-requests','x-ratelimit-limit-tokens',
                                 'x-ratelimit-remaining-requests','x-ratelimit-remaining-tokens',
                                 'x-ratelimit-reset-requests','x-ratelimit-reset-tokens'):
                        value=response.headers.get(name,'')
                        if value and len(value)<=80 and re.fullmatch(r'[0-9.hms]+',value):
                            self.last_rate_limits[name]=value
                    if response.status_code in (401,403):
                        raise ProviderError('provider_authentication')
                    if response.status_code == 429:
                        raise ProviderError('provider_rate_limited')
                    if response.status_code != 200:
                        raise ProviderError('provider_error')
                    body = bytearray()
                    for block in response.iter_bytes(chunk_size=4096):
                        if len(body)+len(block) > self.config.max_response_bytes:
                            raise ProviderError('malformed_response')
                        body.extend(block)
            data = json.loads(body)
            self.last_usage=parse_usage(data.get('usage')) if isinstance(data,dict) else None
            returned_model=data.get('model') if isinstance(data,dict) else None
            if isinstance(returned_model,str) and returned_model==self.config.model:
                self.last_returned_model=returned_model
            choice = data['choices'][0]
            if choice.get('finish_reason') != 'stop' or choice['message'].get('tool_calls'):
                raise ProviderError('malformed_response')
            content = choice['message']['content']
            if not isinstance(content,str) or not content.strip():
                raise ProviderError('malformed_response')
            return ProviderResult(content)
        except ProviderError:
            raise
        except httpx.TimeoutException:
            raise ProviderError('provider_timeout') from None
        except (json.JSONDecodeError, KeyError, IndexError, TypeError, UnicodeError):
            raise ProviderError('malformed_response') from None
        except Exception:
            raise ProviderError('provider_error') from None


class DeterministicMockProvider:
    """Scripted question->excerpt decisions ONLY; no semantic intelligence claim.

    No reference answer is returned from storage. Selected quote text must exist
    in the request's retrieved evidence or this mock refuses. Unregistered inputs
    always refuse. Production adapters do not import or use fixture rules.
    """
    is_mock = True

    def __init__(self, rules=()):
        self.rules = {}
        for rule in rules:
            key = rule['question'].strip()
            if key in self.rules:
                raise ValueError('Duplicate mock question')
            self.rules[key] = rule

    def generate(self, request):
        rule = self.rules.get(request.question.strip())
        reason = rule.get('refusal_reason') if rule else 'missing_evidence'
        claims = []
        if rule and not reason:
            for selection in rule.get('selections',[]):
                hit = next((h for h in request.evidence if h.chunk.document_id==selection['document_id']
                            and h.chunk.page==selection['page'] and selection['excerpt'] in h.chunk.text),None)
                if hit is None:
                    claims = []
                    reason = 'missing_evidence'
                    break
                excerpt = selection['excerpt']
                claims.append({'text':excerpt,'evidence':[{'chunk_id':hit.chunk.chunk_id,'excerpt':excerpt}]})
        if not claims:
            return ProviderResult(json.dumps({'status':'insufficient_evidence','reason':reason or 'missing_evidence','claims':[]}))
        return ProviderResult(json.dumps({'status':'answered','reason':'supported','claims':claims},ensure_ascii=False))


def load_provider_environment(env_file, *, environ=None):
    """Explicit private-file loading, process overrides file; no global mutation/logging."""
    from pathlib import Path
    from dotenv import dotenv_values
    try:
        path=Path(env_file)
        if not path.is_file():
            raise ProviderError('provider_configuration')
        values=dotenv_values(path,interpolate=False,verbose=False)
        values={k:v for k,v in values.items() if v is not None}
        return {**values,**(os.environ if environ is None else environ)}
    except ProviderError:
        raise
    except Exception:
        raise ProviderError('provider_configuration') from None


def provider_from_env(env=None, *, mock_rules=(), approval=None, env_file=None):
    """Process settings by default; explicit env_file opts in to private dotenv loading."""
    if env_file is not None:
        if env is not None:
            raise ProviderError('provider_configuration')
        env=load_provider_environment(env_file)
    env = os.environ if env is None else env
    if env.get('LLM_PROVIDER','mock').lower()=='mock':
        return DeterministicMockProvider(mock_rules)
    return OpenAICompatibleProvider(ProviderConfig.from_env(env),approval=approval)
