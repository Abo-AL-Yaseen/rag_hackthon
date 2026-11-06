"""Approval-gated audit helpers. Public RAG response remains v1.0.0 unchanged."""
from dataclasses import asdict
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import time

from .generation.accounting import CostBudget, Rates
from .generation.providers import ProviderError


def plan_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_bindings(plan,root,chunks):
    from .ingestion import corpus_hash
    root=Path(root)
    paths={'evaluation_sha256':root/'data/sample/phase3_questions.json',
           'prompt_sha256':root/'src/rag_hackathon/generation/prompts.py',
           'provider_sha256':root/'src/rag_hackathon/generation/providers.py'}
    if any(plan.get(k)!=hashlib.sha256(p.read_bytes()).hexdigest() for k,p in paths.items()) or plan.get('corpus_sha256')!=corpus_hash(chunks):
        raise RuntimeError('Corpus, cases, prompt or adapter changed; obtain a new plan-bound approval')


def plan_estimate(plan):
    rates=Rates(Decimal(plan['input_usd_per_million']),Decimal(plan['output_usd_per_million']),
                plan['rates_source'],plan['checked_date'])
    per_call=rates.estimate(plan['input_token_estimate_bound'],plan['max_output_tokens'])
    return {'per_call_upper_estimate_usd':str(per_call),
            'all_attempts_upper_estimate_usd':str(per_call*plan['max_attempts']),
            'requested_spending_cap_usd':plan['max_inference_usd'],
            'limitation':'Input native token count and final bill are unknown before live calls; use provider-side key limit.'}


def require_approval(plan_path,approval_path):
    """Consumes one local operator approval atomically. Never from HTTP input."""
    plan=json.loads(Path(plan_path).read_text())
    approval_path=Path(approval_path)
    approval=json.loads(approval_path.read_text())
    if (approval.get('approved') is not True or approval.get('plan_sha256')!=plan_digest(plan_path)
            or not approval.get('approval_reference') or approval.get('provider_key_spend_limit_confirmed') is not True):
        raise RuntimeError('Explicit plan-bound approval and provider spending limit confirmation required')
    if Decimal(plan_estimate(plan)['all_attempts_upper_estimate_usd'])>Decimal(plan['max_inference_usd']):
        raise RuntimeError('Plan cannot fit the approved estimate cap')
    # Atomic exclusive creation prevents accidentally repeating an approved batch.
    marker=approval_path.with_name(approval_path.name+'.used')
    with marker.open('x',encoding='utf-8') as f:
        f.write(json.dumps({'plan_sha256':plan_digest(plan_path),'status':'consumed; review before any new authorization'}))
    return plan


class AuditedProvider:
    """Per-attempt numeric sidecar; no keys, headers or raw HTTP error bodies."""
    def __init__(self,provider,budget:CostBudget,journal=None):
        self.provider,self.budget,self.journal=provider,budget,journal
        self.is_mock=provider.is_mock
        self.records=[]

    def _write(self,value):
        if self.journal is not None:
            self.journal.write(json.dumps(value)+'\n')
            self.journal.flush()
            import os
            os.fsync(self.journal.fileno())

    def generate(self,request):
        self.provider.payload_for(request)  # reject excessive input before reservation
        try:
            ticket=self.budget.reserve()
        except RuntimeError:
            raise ProviderError('remote_calls_disabled') from None
        record={'attempt':ticket+1,'usage':None,'estimated_cost_from_usage_usd':None,
                'reserved_usd':str(self.budget.per_call),'error':None,'latency_ms':None,
                'requested_model':self.provider.config.model,'returned_model_matches':None}
        self._write({'event':'reserved','attempt':ticket+1,'reserved_usd':record['reserved_usd']})
        start=time.perf_counter()
        try:
            return self.provider.generate(request)
        except ProviderError as exc:
            record['error']=exc.code
            self.budget.stopped=True
            raise
        except Exception:
            record['error']='provider_error'
            self.budget.stopped=True
            raise ProviderError('provider_error') from None
        finally:
            record['latency_ms']=(time.perf_counter()-start)*1000
            usage=self.provider.last_usage
            record['usage']=usage
            cost=self.budget.settle(ticket,usage)
            record['estimated_cost_from_usage_usd']=str(cost) if cost is not None else None
            matches=self.provider.last_returned_model==self.provider.config.model
            record['returned_model_matches']=matches
            if not matches:
                self.budget.stopped=True
            self.records.append(record)
            self._write({'event':'completed',**record})
