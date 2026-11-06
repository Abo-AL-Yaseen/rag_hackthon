"""Offline end-to-end MOCK evaluation; never a semantic LLM benchmark."""
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from rag_hackathon.generation.contracts import ProviderResult,RAGResponse
from rag_hackathon.preparation import build_preparation_service
from rag_hackathon.rag_evaluation import RecordingRetriever,audit_sources,reference_scores
from rag_hackathon.resources import MemoryMonitor
from rag_hackathon.schema import Chunk,Hit
from rag_hackathon.service import RAGService


def fault_ablation():
    """Paired artificial before-validation vs strict validation; not Phase 1 behavior."""
    text='Loans last twelve days.'
    evidence=Hit(Chunk('c1','library','synthetic_library.json',1,text,0,len(text),'fixture'),.99)
    def payload(claim=text,ident='c1',excerpt=text):
        return json.dumps({'status':'answered','reason':'supported','claims':[
            {'text':claim,'evidence':[{'chunk_id':ident,'excerpt':excerpt}]}]})
    cases=[('valid',payload(),True),('invented_id',payload(ident='fabricated'),False),
           ('fabricated_excerpt',payload(claim='Loans last 900 days.',excerpt='Loans last 900 days.'),False),
           ('unsupported_paraphrase',payload(claim='Loans last 900 days.'),False),
           ('uncited_extra_field',payload()[:-1]+',"answer":"invented tail"}',False),
           ('irrelevant_but_exact_quote',payload(),True)]
    class Retriever:
        def search(self,*args): return [evidence]
    results=[]
    for name,content,structurally_valid in cases:
        class Provider:
            is_mock=True
            def generate(self,request): return ProviderResult(content)
        question='What is the capital of Mars?' if name=='irrelevant_but_exact_quote' else 'loan?'
        response=RAGService(Retriever(),Provider()).ask(question)
        results.append({'case':name,'structurally_valid':structurally_valid,
                        'before_validation':'unvalidated draft would be displayed',
                        'after_status':response.status,'after_reason':response.reason,
                        'response':response.model_dump(mode='json'),
                        'known_semantic_limitation':name=='irrelevant_but_exact_quote'})
    return {'label':'Artificial paired validation ablation, NOT historical Phase 1 generation or LLM quality.',
            'cases':results,'invalid_drafts_displayed_before':sum(not x['structurally_valid'] for x in results),
            'invalid_drafts_answered_after':sum(not x['structurally_valid'] and x['after_status']=='answered' for x in results)}


def main():
    import numpy as np
    from rag_hackathon.ingestion import corpus_hash
    evidence_dir=ROOT/'docs/evidence'
    questions=json.loads((ROOT/'data/sample/phase2_questions.json').read_text(encoding='utf-8'))['questions']
    records=[]
    init=time.perf_counter()
    with patch('socket.socket.connect',side_effect=RuntimeError('Offline evaluation: external calls disabled')),MemoryMonitor() as memory:
        service,index,chunks=build_preparation_service(ROOT)
        init_seconds=time.perf_counter()-init
        recording=RecordingRetriever(service.retriever)
        service.retriever=recording
        try:
            for _ in range(3):
                service.ask(questions[0]['question'],language=questions[0]['language'])
            for case in questions:
                repeats=[]
                for _ in range(3):
                    start=time.perf_counter()
                    response=service.ask(case['question'],language=case['language'])
                    repeats.append((time.perf_counter()-start)*1000)
                claim_text='\n'.join(c.text for c in response.claims)
                lexical=reference_scores(claim_text,[case['reference_answer']]) if case['answerable'] else None
                audit=audit_sources(response,recording.last_hits)
                records.append({**case,'response':response.model_dump(mode='json'),
                                'retrieved':[h.as_dict() for h in recording.last_hits],
                                'latency_samples_ms':repeats,'reference_diagnostics':lexical,'citation_audit':audit,
                                'status_matches_fixture':response.status==case['expected_status']})
        finally:
            index.close()
        ablation=fault_ablation()
    positives=[r for r in records if r['answerable']]
    negatives=[r for r in records if not r['answerable']]
    answered=[r for r in records if r['response']['status']=='answered']
    latencies=[n for r in records for n in r['latency_samples_ms']]
    checked=sum(r['citation_audit']['source_references_checked'] for r in records)
    correct=sum(r['citation_audit']['source_references_correct'] for r in records)
    result={'created_utc':datetime.now(timezone.utc).isoformat(),'synthetic':True,'mock_provider':True,
            'notice':'Scripted fixture lookup proves integration only, NOT semantic faithfulness or real LLM performance.',
            'corpus_sha256':corpus_hash(chunks),'chunks':len(chunks),'initialization_seconds':init_seconds,
            'summary':{'questions':len(records),'positive_questions':len(positives),'negative_questions':len(negatives),
                       'status_matches_fixture':sum(r['status_matches_fixture'] for r in records),
                       'positive_answered':sum(r['response']['status']=='answered' for r in positives),
                       'false_refusals':sum(r['response']['status']=='insufficient_evidence' for r in positives),
                       'negative_refused':sum(r['response']['status']=='insufficient_evidence' for r in negatives),
                       'negative_answered':sum(r['response']['status']=='answered' for r in negatives),
                       'errors':sum(r['response']['status']=='error' for r in records),
                       'citation_references_checked':checked,'citation_reference_accuracy':correct/checked if checked else None,
                       'normalized_exact_match_reference_diagnostic':float(np.mean([r['reference_diagnostics']['normalized_exact_match'] for r in positives])),
                       'token_f1_reference_diagnostic':float(np.mean([r['reference_diagnostics']['token_f1'] for r in positives])),
                       'semantic_correctness':None,'semantic_faithfulness':None,
                       'latency_n':len(latencies),'latency_ms_p50':float(np.percentile(latencies,50)),
                       'latency_ms_p95':float(np.percentile(latencies,95)),'percentile_method':'numpy linear'},
            'memory':memory.result(),'cases':records,'validation_ablation':ablation,
            'phase1_comparison':{'generation':'not available in Phase 1; no numeric before/after generation-quality comparison is valid',
                                 'retrieval':'original Phase 1 benchmark preserved; Phase 2 includes three extra version fixtures, so retrieval scores are not a direct ablation'},
            'real_provider_calls':0,'new_download_bytes':0}
    (evidence_dir/'phase2_evaluation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    review={'status':'pending independent human review','semantic_faithfulness':None,
            'cases':[{'id':r['id'],'question':r['question'],'reference_answer':r['reference_answer'],
                      'response':r['response'],'retrieved':r['retrieved'],
                      'reviewer':None,'correctness_0_to_2':None,'claims':[
                          {'text':c['text'],'source_ids':c['source_ids'],'support_judgment':None,'reason':None}
                          for c in r['response']['claims']]} for r in records]}
    (evidence_dir/'phase2_review_queue.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'docs/rag_response.schema.json').write_text(json.dumps(RAGResponse.model_json_schema(),indent=2))
    examples={key:records[position]['response'] for key,position in (
        ('answered_ar',0),('answered_en',1),('out_of_scope_ar',12),('ambiguous_ar',15))}
    examples['invalid_citation_error']=ablation['cases'][1]['response']
    (evidence_dir/'phase2_contract_examples.json').write_text(json.dumps(examples,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result['summary'],indent=2))
    print(json.dumps(result['memory'],indent=2))
    if result['summary']['errors']:
        raise SystemExit('Evaluation runtime errors; inspect evidence')


if __name__=='__main__':
    main()
