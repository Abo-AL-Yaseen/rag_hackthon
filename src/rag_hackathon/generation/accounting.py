"""Numeric usage/cost audit, kept outside the public v1 RAG response contract."""
from dataclasses import dataclass
from decimal import Decimal
import math
import threading


def parse_usage(value):
    if not isinstance(value,dict):
        return None
    keys=('prompt_tokens','completion_tokens','total_tokens')
    if any(type(value.get(k)) is not int or value[k]<0 for k in keys):
        return None
    if value['total_tokens']!=value['prompt_tokens']+value['completion_tokens']:
        return None
    result={k:value[k] for k in keys}
    details=value.get('completion_tokens_details') or {}
    reasoning=details.get('reasoning_tokens') if isinstance(details,dict) else None
    if type(reasoning) is int and 0<=reasoning<=value['completion_tokens']:
        result['reasoning_tokens']=reasoning  # subset, never billed twice
    cost=value.get('cost')
    if type(cost) in (float,int) and math.isfinite(cost) and cost>=0:
        result['reported_cost_credits']=cost
    return result


@dataclass(frozen=True)
class Rates:
    input_per_million: Decimal
    output_per_million: Decimal
    source: str
    checked_date: str

    def __post_init__(self):
        if any(not v.is_finite() or v<0 for v in (self.input_per_million,self.output_per_million)):
            raise ValueError('Finite nonnegative rates required')

    def estimate(self,prompt_tokens,completion_tokens):
        if any(type(x) is not int or x<0 for x in (prompt_tokens,completion_tokens)):
            raise ValueError('Nonnegative integer token counts required')
        return (prompt_tokens*self.input_per_million+completion_tokens*self.output_per_million)/Decimal(1_000_000)


class CostBudget:
    """Reserve before calls. Unknown usage/errors keep their full reservation.

    Native tokens are unknown before inference; input_bound is a documented
    conservative estimate. Pair with provider-side spending/price limits.
    """
    def __init__(self,rates,*,max_usd,max_attempts,input_bound=16000,output_bound=1024):
        self.rates=rates
        self.max_usd=Decimal(str(max_usd))
        if not self.max_usd.is_finite() or self.max_usd<=0 or max_attempts<1:
            raise ValueError('Positive finite budget and attempt limit required')
        self.max_attempts=max_attempts
        self.input_bound,self.output_bound=input_bound,output_bound
        self.per_call=rates.estimate(input_bound,output_bound)
        self.committed=Decimal(0)
        self.reservations=[]
        self.stopped=False
        self.lock=threading.Lock()

    def reserve(self):
        with self.lock:
            if self.stopped or len(self.reservations)>=self.max_attempts or self.committed+self.per_call>self.max_usd:
                raise RuntimeError('Call budget exhausted or stopped')
            self.committed+=self.per_call
            self.reservations.append(self.per_call)
            return len(self.reservations)-1

    def settle(self,number,usage):
        with self.lock:
            if usage is None:
                self.stopped=True
                return None
            actual=self.rates.estimate(usage['prompt_tokens'],usage['completion_tokens'])
            if usage['prompt_tokens']>self.input_bound or usage['completion_tokens']>self.output_bound or actual>self.reservations[number]:
                self.stopped=True
            # A reservation is kept for unknown fees; actual is an estimate from
            # documented uncached rates, not an assertion about the final invoice.
            return actual
