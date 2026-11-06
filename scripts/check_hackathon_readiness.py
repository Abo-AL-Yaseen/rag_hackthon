"""New-PDF end-to-end readiness audit. CPU/local only, scripted generation."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from rag_hackathon.workspace import cached_encoder,ingest,open_index
from rag_hackathon.ingestion import load_pages
from rag_hackathon.resources import MemoryMonitor
from examples.invoke_local_engine import invoke


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index',type=Path,default=ROOT/'data/index/readiness-audit')
    parser.add_argument('--isolation-index',type=Path,default=ROOT/'data/index/readiness-isolation')
    args=parser.parse_args()
    data=ROOT/'data/sample/readiness'
    cases=json.loads((data/'cases.json').read_text(encoding='utf-8'))['cases']
    rules=json.loads((data/'mock_rules.json').read_text(encoding='utf-8'))['rules']
    previous=ROOT/'data/index/phase3/retrieval_manifest.json'
    prior_hash=hashlib.sha256(previous.read_bytes()).hexdigest() if previous.exists() else None
    start=time.perf_counter()
    with patch('socket.socket.connect',side_effect=AssertionError('Readiness audit forbids network')),MemoryMonitor() as memory:
        encoder=cached_encoder()
        loaded_s=time.perf_counter()-start
        manifest=ingest(data/'inputs',args.index,encoder=encoder)
        index=open_index(args.index,encoder=encoder)
        records=[]
        try:
            for case in cases:
                hits=index.search(case['question'],3)
                request={'question':case['question'],'language':case['language']}
                response=invoke(index,request,rules)
                original=load_pages(data/'inputs'/case['file'])[case['page']-1]
                assert case['excerpt'] in original.text
                assert hits[0].chunk.source==case['file'] and hits[0].chunk.page==case['page']
                assert response['status']=='answered' and response['mode']=='mock'
                assert len(response['sources'])==1
                source=response['sources'][0]
                assert source['document_name']==case['file'] and source['page_number']==case['page']
                assert source['supporting_excerpt']==case['excerpt']
                records.append({'id':case['id'],'request':request,'response':response,
                    'retrieved':[{'chunk_id':h.chunk.chunk_id,'file':h.chunk.source,'page':h.chunk.page,'score':h.score} for h in hits],
                    'source_quote_verified_against_pdf_extraction':True})
            chunk_ids={str(p.id) for p in index.client.scroll(index.collection,limit=100)[0]}
            assert len(chunk_ids)==4
        finally: index.close()
        isolated=ingest(data/'inputs/readiness_english.pdf',args.isolation_index,encoder=encoder)
        other=open_index(args.isolation_index,encoder=encoder)
        try:
            points,_=other.client.scroll(other.collection,limit=100,with_payload=True)
            assert len(points)==2 and {p.payload['document_id'] for p in points}=={'readiness_english'}
        finally: other.close()
    if prior_hash is not None:
        assert hashlib.sha256(previous.read_bytes()).hexdigest()==prior_hash
    report={'synthetic':True,'mode':'CPU retrieval + scripted offline generation; no LLM capability claim',
            'real_llm_calls':0,'new_pdfs':2,'physical_pages':4,'indexed_chunks':manifest['chunks'],
            'embedding_dimension':384,'device':'cpu','model_load_and_hash_check_seconds':loaded_s,
            'dataset_manifest':manifest,'cases':records,'correct_top1_retrieval_cases':len(records),
            'correct_document_page_citations':len(records),'separate_store_chunks':isolated['chunks'],
            'fresh_store_has_only_explicit_inputs':True,'previous_synthetic_manifest_unchanged':True,
            'memory':memory.result()}
    (ROOT/'docs/evidence/phase4_workflow.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'docs/evidence/phase4_contract_examples.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('new_pdfs','physical_pages','indexed_chunks','correct_top1_retrieval_cases','correct_document_page_citations','real_llm_calls')}))


if __name__=='__main__': main()
