"""Prepare offline by default. Live execution requires explicit plan-bound approval."""
import argparse
from dataclasses import asdict
from datetime import datetime,timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from rag_hackathon.generation.accounting import CostBudget,Rates
from rag_hackathon.generation.prompts import messages_for,PROMPT_VERSION
from rag_hackathon.generation.providers import (DeterministicMockProvider,OpenAICompatibleProvider,
                                               ProviderConfig,RemoteCallApproval)
from rag_hackathon.live_evaluation import AuditedProvider,plan_digest,plan_estimate,require_approval,verify_bindings
from rag_hackathon.preparation import build_preparation_service
from rag_hackathon.rag_evaluation import RecordingRetriever,audit_sources,reference_scores
from rag_hackathon.evaluation import precision_recall_at_k
from rag_hackathon.resources import MemoryMonitor
from rag_hackathon.service import RAGService


def evaluate_cases(service,cases,chunks,*,audit=None,stop_on_error=False):
    recording=RecordingRetriever(service.retriever)
    service.retriever=recording
    records=[]
    for case in cases:
        before=len(audit.records) if audit else 0
        start=time.perf_counter()
        response=service.ask(case['question'],language=case['language'])
        elapsed=(time.perf_counter()-start)*1000
        relevant=[c.chunk_id for c in chunks if any(c.document_id==r['document_id'] and c.page==r['page']
                                                  for r in case['relevant_sources'])]
        ids=[h.chunk.chunk_id for h in recording.last_hits]
        retrieval={str(k):precision_recall_at_k(ids,relevant,k) for k in (1,3)}
        receipt=audit.records[-1] if audit and len(audit.records)>before else None
        records.append({**case,'response':response.model_dump(mode='json'),'retrieved':[h.as_dict() for h in recording.last_hits],
                        'retrieval_metrics':retrieval,'citation_audit':audit_sources(response,recording.last_hits),
                        'reference_diagnostic':reference_scores('\n'.join(c.text for c in response.claims),[case['reference_answer']]) if case['answerable'] else None,
                        'latency_ms':elapsed,'usage_audit':receipt,
                        'status_matches_fixture':response.status==case['expected_status'],
                        'semantic_correctness':None,'semantic_faithfulness':None})
        if stop_on_error and (response.status=='error' or audit and audit.budget.stopped):
            break
    return records


def summarize(records):
    import numpy as np
    positives=[r for r in records if r['answerable']]
    negatives=[r for r in records if not r['answerable']]
    return {'cases_run':len(records),'positives':len(positives),'negatives':len(negatives),
            'status_matches_fixture':sum(r['status_matches_fixture'] for r in records),
            'positive_answered':sum(r['response']['status']=='answered' for r in positives),
            'negative_refused':sum(r['response']['status']=='insufficient_evidence' for r in negatives),
            'false_refusals':sum(r['response']['status']=='insufficient_evidence' for r in positives),
            'errors':sum(r['response']['status']=='error' for r in records),
            'recall_at_1':float(np.mean([r['retrieval_metrics']['1']['recall'] for r in positives])) if positives else None,
            'recall_at_3':float(np.mean([r['retrieval_metrics']['3']['recall'] for r in positives])) if positives else None,
            'precision_at_3':float(np.mean([r['retrieval_metrics']['3']['precision'] for r in positives])) if positives else None,
            'latency_ms_p50':float(np.percentile([r['latency_ms'] for r in records],50)) if records else None,
            'latency_ms_p95':float(np.percentile([r['latency_ms'] for r in records],95)) if records else None,
            'semantic_correctness':None,'semantic_faithfulness':None}


def live_run(plan_path,approval_path,service,index,chunks,cases,output):
    # This function is not executed during preparation or automated evaluation.
    from dotenv import dotenv_values
    from rag_hackathon.openrouter_preflight import check_model, check_key
    plan=json.loads(plan_path.read_text())
    authorization=json.loads(Path(approval_path).read_text(encoding='utf-8'))
    if authorization.get('scope')!='two_smoke_attempts_only':
        raise RuntimeError('This entry requires approval scoped to two smoke attempts only')
    verify_bindings(plan,ROOT,chunks)
    env={**dotenv_values(ROOT/'.env'),**os.environ}  # only this explicit live entry loads private .env
    cfg=ProviderConfig.from_env(env)
    if (cfg.name!=plan['provider'] or cfg.base_url.rstrip('/')!=plan['base_url'] or cfg.model!=plan['model']
        or not cfg.allow_paid_calls or cfg.max_output_tokens!=plan['max_output_tokens']
        or cfg.max_input_bytes!=plan['max_messages_utf8_bytes']
        or cfg.timeout_seconds!=plan['timeout_seconds'] or cfg.temperature!=plan['temperature'] or cfg.top_p!=plan['top_p']
        or cfg.reasoning_enabled is not False or cfg.response_format!='json_object'
        or cfg.input_price_ceiling!=float(plan['input_usd_per_million'])
        or cfg.output_price_ceiling!=float(plan['output_usd_per_million'])):
        raise RuntimeError('Private settings must match the exact approved plan, price caps and token/byte limits')
    if len(cases)!=plan['evaluation_cases'] or plan['smoke_calls']!=2:
        raise RuntimeError('Evaluation changed; re-plan and obtain approval')
    # Current user authorization covers only two calls, never the full evaluation.
    smoke_cases = [next(c for c in cases if c['id'] == case_id) for case_id in ('q01','q14')]
    public_check = check_model(plan)
    key_before = check_key(cfg.api_key, minimum_remaining='0.005952')
    preflight_path = output.with_suffix('.preflight.json')
    preflight_path.parent.mkdir(parents=True, exist_ok=True)
    preflight_path.write_text(json.dumps({'model':public_check,'key':key_before},indent=2),encoding='utf-8')
    approved=require_approval(plan_path,approval_path)
    rates=Rates(Decimal(plan['input_usd_per_million']),Decimal(plan['output_usd_per_million']),plan['rates_source'],plan['checked_date'])
    budget=CostBudget(rates,max_usd=plan['max_inference_usd'],max_attempts=2,
                      input_bound=plan['input_token_estimate_bound'],output_bound=plan['max_output_tokens'])
    approval=RemoteCallApproval(base_url=cfg.base_url,model=cfg.model,max_attempts=2)
    output.parent.mkdir(parents=True,exist_ok=True)
    journal_path=output.with_suffix('.jsonl')
    with journal_path.open('x',encoding='utf-8') as journal:
        provider=AuditedProvider(OpenAICompatibleProvider(cfg,approval=approval),budget,journal)
        engine=RAGService(index,provider,policy=service.policy)
        smoke=evaluate_cases(engine,smoke_cases,chunks,audit=provider,stop_on_error=True)
        measured=[]  # Full 24-case evaluation requires a separate post-smoke user review.
        key_after=None
        account_check_error=None
        try:
            key_after=check_key(cfg.api_key, minimum_remaining=0, require_unused=False)
        except Exception:
            account_check_error='post_run_budget_check_failed; spending requires account reconciliation'
        result={'created_utc':datetime.now(timezone.utc).isoformat(),'synthetic':True,'mode':'live',
                'notice':'Actual provider inference on synthetic preparation cases, not hackathon performance.',
                'plan_sha256':plan_digest(plan_path),'smoke':smoke,'cases':measured,'summary':summarize(measured),
                'usage_audit':provider.records,'reserved_upper_estimate_usd':str(budget.committed),
                'stopped_for_unknown_usage_or_error':budget.stopped,'semantic_review':'pending independent human review',
                'authorization_scope':'two_smoke_attempts_only; 24-case evaluation blocked pending review',
                'key_before':key_before,'key_after':key_after,'account_check_error':account_check_error,
                'actual_key_usage_delta_usd':str(Decimal(key_after['usage_usd'])-Decimal(key_before['usage_usd'])) if key_after else None,
                'remaining_provider_budget_usd':key_after['remaining_usd'] if key_after else None,
                'remaining_lifetime_attempts':26-len(provider.records),
                'billing_note':'Key usage is a point-in-time provider report and may lag settlement. Compare response cost/usage and reconcile before further calls.'}
        output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('STOPPED after at most two smoke attempts. The 24-case evaluation was NOT run. Review evidence before further authorization.')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--execute-live',action='store_true')
    parser.add_argument('--approval-file',type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'docs/evidence/phase3_live_results.json')
    args=parser.parse_args()
    if args.execute_live and not args.approval_file:
        parser.error('Live calls require an explicit plan-bound approval file; none is granted yet')
    plan_path=ROOT/'config/phase3_live_plan.json'
    plan=json.loads(plan_path.read_text())
    data=json.loads((ROOT/'data/sample/phase3_questions.json').read_text(encoding='utf-8'))
    cases=data['questions']
    # Local preflight and baseline always block external networking.
    with patch('socket.socket.connect',side_effect=RuntimeError('Offline preparation: no LLM connections')),MemoryMonitor() as memory:
        service,index,chunks=build_preparation_service(ROOT,index_path=ROOT/'data/index/phase3')
        try:
            rules=json.loads((ROOT/'data/sample/phase3_mock_rules.json').read_text(encoding='utf-8'))['rules']
            class Capture:
                is_mock=True
                def __init__(self): self.inner=DeterministicMockProvider(rules); self.requests=[]
                def generate(self,request):
                    self.requests.append(request)
                    return self.inner.generate(request)
            capture=Capture()
            service.provider=capture
            records=evaluate_cases(service,cases,chunks)
            sizes=[len(json.dumps(messages_for(r),ensure_ascii=False).encode()) for r in capture.requests]
            if sizes and max(sizes)>plan['max_messages_utf8_bytes']:
                raise RuntimeError('Plan input byte allowance insufficient; revise estimate before approval')
            from rag_hackathon.ingestion import corpus_hash
            bindings={'evaluation_sha256':hashlib.sha256((ROOT/'data/sample/phase3_questions.json').read_bytes()).hexdigest(),
                      'corpus_sha256':corpus_hash(chunks),
                      'prompt_sha256':hashlib.sha256((ROOT/'src/rag_hackathon/generation/prompts.py').read_bytes()).hexdigest(),
                      'provider_sha256':hashlib.sha256((ROOT/'src/rag_hackathon/generation/providers.py').read_bytes()).hexdigest()}
            if args.execute_live:
                verify_bindings(plan,ROOT,chunks)
            else:
                plan.update(bindings)
                plan_path.write_text(json.dumps(plan,indent=2)+'\n')
            prepared={'created_utc':datetime.now(timezone.utc).isoformat(),'mode':'offline_scripted_baseline',
                      'synthetic':True,'real_llm_calls':0,'actual_inference_cost_usd':'0',
                      'prompt_version':PROMPT_VERSION,'summary':summarize(records),'cases':records,
                      'unsupported_multi_turn_probes':data['unsupported_multi_turn_probes'],
                      'max_observed_messages_utf8_bytes':max(sizes) if sizes else 0,
                      'plan_sha256':plan_digest(plan_path),'proposed_cost':plan_estimate(plan),
                      'usage_note':'All API usage/cost-per-response fields are null until actual calls. Mock has no native LLM tokens.'}
        except Exception:
            index.close()
            raise
    prepared['memory']=memory.result()
    (ROOT/'docs/evidence/phase3_offline_evaluation.json').write_text(json.dumps(prepared,ensure_ascii=False,indent=2),encoding='utf-8')
    review={'status':'pending human review; no semantic scores inferred','cases':[
        {'id':r['id'],'reference_answer':r['reference_answer'],'response':r['response'],
         'retrieved':r['retrieved'],'reviewer':None,'correctness_0_to_2':None,'faithfulness_claim_judgments':None}
        for r in records]}
    (ROOT/'docs/evidence/phase3_review_queue.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
    template={'approved':False,'plan_sha256':plan_digest(plan_path),'approval_reference':None,
              'provider_key_spend_limit_confirmed':False,'note':'Operator completes only AFTER explicit user approval; never supply credentials here.'}
    (ROOT/'docs/evidence/phase3_approval_request.json').write_text(json.dumps(template,indent=2))
    print(json.dumps(prepared['summary'],indent=2))
    print(json.dumps(prepared['proposed_cost'],indent=2))
    try:
        if args.execute_live:
            live_run(plan_path,args.approval_file,service,index,chunks,cases,args.output)
        else:
            print('Prepared only. STOPPED before any external LLM call; explicit approval and credentials required.')
    finally:
        index.close()


if __name__=='__main__': main()
