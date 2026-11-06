"""Replay synthetic failure classes against frozen smoke evidence, no network/keys."""
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rag_hackathon.diagnostics import LocalDiagnostics
from rag_hackathon.generation.contracts import ProviderResult
from rag_hackathon.generation.prompts import messages_for,PROMPT_VERSION
from rag_hackathon.generation.selections import candidate_spans
from rag_hackathon.schema import Hit,Chunk
from rag_hackathon.service import RAGService


class FrozenRetriever:
    def __init__(self,hits): self.hits=hits
    def search(self,*args): return self.hits


class FixtureProvider:
    is_mock=True
    def __init__(self,make_draft): self.make_draft=make_draft; self.calls=0; self.input_bytes=None
    def generate(self,request):
        self.calls+=1
        self.input_bytes=len(json.dumps(messages_for(request),ensure_ascii=False).encode('utf-8'))
        return ProviderResult(self.make_draft(request))


def legacy(claim,excerpt,chunk_id):
    return json.dumps({'status':'answered','reason':'supported','claims':[{'text':claim,
        'evidence':[{'chunk_id':chunk_id,'excerpt':excerpt}]}]},ensure_ascii=False)


def selected(request):
    return json.dumps({'status':'answered','reason':'supported',
        'selection_ids':[next(iter(candidate_spans(request.evidence)))]})


def main():
    saved=ROOT/'docs/evidence/groq_live_smoke_results.json'
    smoke=json.loads(saved.read_text(encoding='utf-8'))
    item=smoke['tests'][0]['receipt']['evidence_sent'][0].copy()
    score=item.pop('score'); source=Hit(Chunk(**item),score)
    quote=next(iter(candidate_spans([source]).values())).excerpt
    chunk=source.chunk.chunk_id
    equivalent=[('literal',quote),('short_paraphrase','يمكن استعارة الكتب لمدة اثني عشر يوماً.'),
        ('arabic_case_variant',quote.replace('اثني','اثنا')),
        ('western_digits',quote.replace('اثني عشر','12')),('arabic_digits',quote.replace('اثني عشر','١٢'))]
    cases=[]
    for name,text in equivalent:
        cases.append((name,[source],lambda request,t=text:legacy(t,quote,chunk),selected,
                      'answered' if name=='literal' else 'insufficient_evidence','answered'))
    for number in ('12','١٢','۱۲'):
        text='مدة الإعارة '+number+' يوماً.'
        hit=Hit(Chunk(chunk,'fixture','synthetic_numbers.json',1,text,0,len(text),'v1'),1.0)
        cases.append(('source_digits_'+number,[hit],lambda request,t=text:legacy(t,t,chunk),selected,'answered','answered'))
    cases.extend([
        ('changed_fact',[source],lambda _:legacy('الإعارة ثلاثون يوماً.',quote,chunk),
         lambda _:json.dumps({'status':'answered','reason':'supported','selection_ids':[], 'answer':'الإعارة ثلاثون يوماً.'}),'insufficient_evidence','error'),
        ('invented_reference',[source],lambda _:legacy(quote,quote,'invented'),
         lambda _:json.dumps({'status':'answered','reason':'supported','selection_ids':['invented']}),'error','error'),
        ('out_of_scope',[source],lambda _:json.dumps({'status':'insufficient_evidence','reason':'out_of_scope','claims':[]}),
         lambda _:json.dumps({'status':'insufficient_evidence','reason':'out_of_scope','selection_ids':[]}),'insufficient_evidence','insufficient_evidence'),
        ('provider_unsupported_refusal',[source],lambda _:json.dumps({'status':'insufficient_evidence','reason':'unsupported_claim','claims':[]}),
         lambda _:json.dumps({'status':'insufficient_evidence','reason':'unsupported_claim','selection_ids':[]}),'insufficient_evidence','insufficient_evidence'),
        ('malformed_json',[source],lambda _:'invalid JSON',lambda _:'invalid JSON','error','error'),
        ('missing_evidence',[],lambda _:'unused',lambda _:'unused','insufficient_evidence','insufficient_evidence'),
    ])
    old=Hit(Chunk('old','conflict','synthetic_versions.json',1,'مدة الإعارة 12 يوماً.',0,20,'old'),1)
    new=Hit(Chunk('new','conflict','synthetic_versions.json',1,'مدة الإعارة 30 يوماً.',0,20,'new'),1)
    cases.append(('conflicting_versions',[old,new],lambda _:'unused',selected,'insufficient_evidence','insufficient_evidence'))
    results=[]
    with patch('socket.socket.connect',side_effect=AssertionError('Phase 3.1 forbids network')):
        for ident,hits,make_old,make_new,expected_old,expected_new in cases:
            record={'id':ident,'explicitly_synthetic_draft_fixture':True}
            for mode,make,expected in [('legacy',make_old,expected_old),('selection',make_new,expected_new)]:
                provider=FixtureProvider(make)
                sink=LocalDiagnostics(ROOT/'.local/phase31-diagnostics')
                response=RAGService(FrozenRetriever(hits),provider,diagnostics=sink).ask('كم يوماً يمكن استعارة الكتب؟',language='ar')
                trace=json.loads(sink.last_path.read_text(encoding='utf-8'))
                assert response.status==expected,(ident,mode,response.status)
                record[mode]={'response':response.model_dump(mode='json'),'provider_calls':provider.calls,
                              'input_messages_utf8_bytes':provider.input_bytes,'safe_diagnostic':trace}
            results.append(record)
    evidence={'synthetic':True,'generation':'scripted draft fixtures only, no LLM',
              'prompt_version':PROMPT_VERSION,'real_inference_calls':0,'input_smoke_sha256':hashlib.sha256(saved.read_bytes()).hexdigest(),
              'historical_raw_draft_available':False,'historical_root_cause_confirmed':False,
              'confirmed_failure_class':'Legacy exact text/excerpt mismatch rejects semantically equivalent wording; provider_refusal shares public reason',
              'comparison_scope':'Same frozen source; legacy versus new ID-selection fixture protocol. Not a before/after live LLM benchmark.',
              'cases':results,'cases_run':len(results),'outcomes_match_declared_expectations':True}
    output=ROOT/'docs/evidence/phase31_offline_diagnostics.json'
    output.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'cases_run':len(results),'protocol_outcomes':2*len(results),'real_inference_calls':0,
                     'historical_root_cause_confirmed':False,'fixture_expectations_passed':True}))


if __name__=='__main__': main()
