"""Real scoped retrieval and source citations; generation explicitly scripted."""
import hashlib
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2];RUN=ROOT/'.local/engineering_faculty_20261107'
P=ROOT/'data/processed/engineering_faculty_20261107';INDEX=ROOT/'data/index/engineering_faculty_20261107_v1'
from datetime import datetime,timezone
OUT=Path(os.environ.get('RAG_FACULTY_EVAL_OUTPUT',str(ROOT/'.local'/('faculty_retrieval_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')))))
OUT.mkdir(parents=True,exist_ok=False)
sys.path.insert(0,str(ROOT/'src'))
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',
                  ALLOW_FREE_API_CALLS='false',ALLOW_PAID_API_CALLS='false')
from rag_hackathon.workspace import cached_encoder,open_index
from rag_hackathon.retrieval.scoped import ScopedIndex
from rag_hackathon.service import RAGService,RAGPolicy
from rag_hackathon.generation.providers import DeterministicMockProvider
from rag_hackathon.generation.contracts import RAGResponse

def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
catalog=load(P/'program_catalog.json');programs=[p for p in catalog if p['indexed']]
docs=load(P/'documents.json');by_id={d['document_id']:d for d in docs}
pages={p['document_id']:p for p in load(P/'inputs/faculty_pages.json')['pages']}
courses=load(P/'courses.json');quality=load(P/'data_quality.json')
frequency=Counter(c['course_code'] for c in courses)
cases=[]

def positive(question,language,selected,program=None,version=None,category=None):
    case={'id':f'Q{len(cases)+1:02}','question':question,'language':language,'program_id':program,'plan_version':version,
          'expected_status':'answered','selections':[{'document_id':d['document_id'],'page':d['engine_page_number'],
           'excerpt':d['reference_quote']} for d in selected], 'category':category,
          'label_basis':'Exact published table fields or previously visually verified policy transcript; frozen before retrieval.'}
    for s in case['selections']:assert s['excerpt'] in pages[s['document_id']]['text'] and len(s['excerpt'])<=1500
    cases.append(case)

def negative(q,reason,category,program=None,version=None):
    cases.append({'id':f'Q{len(cases)+1:02}','question':q,'language':'ar','program_id':program,'plan_version':version,
        'expected_status':'insufficient_evidence','refusal_reason':reason,'category':category,
        'label_basis':'Manual scope/missing/conflict label. Mock refusal is not autonomous semantic-detection evidence.'})

# Two questions per collected program. Prefer branch-specific courses; do not
# select a row with unknown AND/OR or colored prerequisite semantics for an
# authoritative prerequisite question.
for i,p in enumerate(programs):
    pid=p['program_id'];v=p['selected_version']
    eligible=[c for c in courses if c['program_id']==pid and not c['quarantined'] and c['ar']['group_index']==2]
    eligible.sort(key=lambda c:(frequency[c['course_code']],bool(c['quality_flags']),c['course_code']))
    credit=eligible[0];code=credit['course_code'];name=credit['ar']['name']
    lang='en' if i%4==0 else 'ar'
    d=by_id[f'eng_{pid}_{v}_{code}_{lang}']
    q=f"In {p['name_en']} published plan {v}, how many credits is {credit['en']['name']} ({code})?" if lang=='en' else f"أنا بدرس {p['name_ar']} حسب الخطة {v}، كم ساعة مساق {name} ({code})؟"
    positive(q,lang,[d],pid,v,'course credits / Palestinian Arabic or English')
    pre=[c for c in eligible if c['ar']['prerequisite_text'] and not c['quality_flags']
         and len(c['ar']['prerequisites']['groups'])==1]
    assert pre,('No unambiguous prerequisite row for reference',pid)
    chosen=pre[0];code=chosen['course_code'];d=by_id[f'eng_{pid}_{v}_{code}_ar']
    positive(f"بخطة {p['name_ar']} {v}، شو المتطلب السابق لمساق {chosen['ar']['name']} ({code})؟",'ar',[d],pid,v,'prerequisite / Palestinian Arabic')

for name,q in [('add_drop','متى بقدر أضيف أو أسحب مساق بأول الفصل العادي والصيفي؟'),
 ('late_withdrawal','إذا بدي أسحب مادة بعد أسبوع السحب والإضافة، لحد إمتى بقدر؟ وهل برجعولي المصاري؟'),
 ('absence_penalty','إذا غبت أكثر من 12.5% بدون عذر، بقدر أقدم النهائي؟'),
 ('engineering_warning','أنا طالب هندسة، إمتى بنزل علي إنذار بسبب معدلي التراكمي؟')]:
    selected=[by_id['policy_'+name]]
    if name=='engineering_warning':selected.append(by_id['policy_first_semester_warning'])
    positive(q,'ar',selected,category='general Engineering regulations')

for pid in ('architectural-engineering','geomatics-engineering','telecommunication-engineering'):
    p=next(p for p in programs if p['program_id']==pid);v=p['selected_version']
    assert not p['graduation_conflict']
    positive(f"حسب الخطة المنشورة {v}، كم مجموع ساعات التخرج في {p['name_ar']}؟",'ar',
        [by_id[f'eng_{pid}_{v}_summary_ar']],pid,v,'graduation requirement with matching handbook total')

# Real source collisions: identical course code, different credits by plan.
# Freeze one question for each distinct credit variant to test actual isolation.
for difference in load(P/'cross_program_differences.json'):
    picked={}
    for variant in difference['variants']:
        picked.setdefault(variant['credit_hours'],variant)
    for variant in picked.values():
        pid=variant['program_id'];v=variant['plan_version'];code=difference['course_code']
        p=next(p for p in programs if p['program_id']==pid)
        d=by_id[f'eng_{pid}_{v}_{code}_ar']
        positive(f"بخطة {p['name_ar']} {v}، كم ساعة معتمدة مساق رمز {code}؟",'ar',[d],pid,v,
                 'same code with differing credits across programs; isolation regression')

negative('كم ساعة لازم أخلص عشان أتخرج؟','ambiguous','program and plan both unspecified')
negative('أنا طالب هندسة مدنية جديد، أي نسخة خطة بتنطبق علي؟','ambiguous','intake-to-plan mapping absent')
negative('شو التاريخ المحدد باليوم والشهر لآخر موعد لسحب المساق بالفصل الحالي؟','missing_evidence','calendar not collected')
negative('شو متطلب المادة؟','ambiguous','course and program unspecified')
negative('شو خطة علم الحاسوب في كلية تكنولوجيا المعلومات والذكاء الاصطناعي؟','out_of_scope','IT faculty excluded by official directory')
negative('شو متطلبات مواد هندسة علوم المواد في أحدث خطة؟','missing_evidence','Materials Science plan currently unavailable')
negative('أنا طالب هندسة حاسوب جديد، كم ساعة لازم أخلص حتى أتخرج؟','conflicting_sources',
         '162 vs 163 credits; conflicted summary withheld','computer-engineering','2021-1')
baseline_cases=RUN/'evaluation_dense_baseline/cases.json'
if baseline_cases.exists():
    assert load(baseline_cases)==cases,'Do not silently change frozen references after failure analysis'
save(OUT/'cases.json',cases)
print('Frozen reference questions:',len(cases),flush=True)

if __name__=='__main__':
    manifest=load(INDEX/'dataset_manifest.json')
    # Evaluation requires an already guarded store and never repairs metadata.
    if not manifest.get('requires_scoped_retrieval'):
        raise ValueError('Missing scope guard marker; evaluation never modifies an existing index')
    binding=load(INDEX/'scope_manifest.json');assert binding['documents']==docs
    assert hashlib.sha256((P/'inputs/faculty_pages.json').read_bytes()).hexdigest()==manifest['files'][0]['sha256']
    with patch('socket.socket.connect',side_effect=RuntimeError('Faculty evaluation forbids network')):
        try:open_index(INDEX)
        except ValueError as e:assert 'ScopedIndex' in str(e)
        else:raise AssertionError('Unscoped open of mixed faculty data must be blocked')
        encoder=cached_encoder();owner=ScopedIndex.open(INDEX,encoder=encoder)
        try:
            for p in programs:
                for bad in (None,'1900-1'):
                    try:owner.for_program(p['program_id'],bad)
                    except ValueError:pass
                    else:raise AssertionError('Missing or unknown plan accepted')
            retrieval=[];leaks=[];withheld_leaks=[]
            views={}
            def view(case):
                key=(case['program_id'],case['plan_version'])
                if key not in views:views[key]=owner.for_program(*key) if key[0] else owner.for_regulations()
                return views[key]
            for c in cases:
                tick=time.perf_counter();hits=view(c).search(c['question'],10);elapsed=(time.perf_counter()-tick)*1000
                for h in hits:
                    d=by_id[h.chunk.document_id]
                    if d['scope']!='regulations' and (d['program_id']!=c['program_id'] or d['plan_version']!=c['plan_version']):leaks.append(c['id'])
                    if not d['retrieval_enabled']:withheld_leaks.append(c['id'])
                metrics=[];refs=c.get('selections',[])
                for k in (1,3,5,10):
                    found=sum(any(h.chunk.document_id==s['document_id'] and s['excerpt'] in h.chunk.text for h in hits[:k]) for s in refs)
                    relevant={s['document_id'] for s in refs}
                    metrics.append({'k':k,'reference_recall':found/len(refs) if refs else None,
                       'all_reference_excerpts_available':found==len(refs) if refs else None,
                       'precision_at_k':sum(h.chunk.document_id in relevant for h in hits[:k])/k if refs else None})
                retrieval.append({'case_id':c['id'],'program_id':c['program_id'],'plan_version':c['plan_version'],
                    'retrieval_ms':elapsed,'metrics':metrics,'hits':[h.as_dict() for h in hits]})
            assert not leaks and not withheld_leaks
            # Adversarial foreign course-code probes for every program. These
            # test vector filtering, separately from scripted negative answers.
            isolation=[]
            for p in programs:
                pid=p['program_id'];v=p['selected_version'];local_codes={c['course_code'] for c in courses if c['program_id']==pid}
                foreign=next(c for c in courses if c['program_id']!=pid and c['course_code'] not in local_codes)
                q=f"{foreign['ar']['name']} {foreign['course_code']} {foreign['program_name_ar']}"
                hits=owner.for_program(pid,v).search(q,20)
                assert all(by_id[h.chunk.document_id]['scope']=='regulations' or
                    (by_id[h.chunk.document_id]['program_id']==pid and by_id[h.chunk.document_id]['plan_version']==v) for h in hits)
                isolation.append({'selected_program':pid,'selected_plan':v,'foreign_course':foreign['course_code'],
                  'foreign_program':foreign['program_id'],'hits':[h.chunk.document_id for h in hits],'foreign_hits':0})
            save(OUT/'retrieval_results.json',retrieval);save(OUT/'isolation_checks.json',isolation)
            rules=[{'question':c['question'],**({'selections':c['selections']} if 'selections' in c else {'refusal_reason':c['refusal_reason']})} for c in cases]
            provider=DeterministicMockProvider(rules);results=[];summaries=[]
            for k in (3,5,10):
                engines={}
                for c in cases:
                    key=(c['program_id'],c['plan_version'])
                    if key not in engines:engines[key]=RAGService(view(c),provider,policy=RAGPolicy(top_k=k))
                    payload=engines[key](c['question'],language=c['language']);RAGResponse.model_validate(payload)
                    assert payload['contract_version']=='1.0.0' and payload['mode']=='mock'
                    assert payload['validation']['semantic_faithfulness']=='not_evaluated'
                    for s in payload['sources']:
                        d=by_id[s['document_id']];page=pages[s['document_id']]
                        assert s['document_name']==page['source'] and s['page_number']==page['page']
                        assert s['supporting_excerpt'] in page['text'] and d['retrieval_enabled']
                        assert d['scope']=='regulations' or (d['program_id']==c['program_id'] and d['plan_version']==c['plan_version'])
                    if payload['status']!='answered':assert not payload['sources'] and not payload['claims']
                    results.append({'case_id':c['id'],'k':k,'expected_status':c['expected_status'],
                        'status_matches_scripted_expectation':payload['status']==c['expected_status'],'payload':payload,
                        'resolved_locators':[by_id[s['document_id']] for s in payload['sources']]})
                pos=[c for c in cases if c['expected_status']=='answered'];neg=len(cases)-len(pos)
                metrics=[next(m for m in r['metrics'] if m['k']==k) for r in retrieval if next(c for c in cases if c['id']==r['case_id'])['expected_status']=='answered']
                rows=[r for r in results if r['k']==k]
                summaries.append({'k':k,'positive_questions':len(pos),'negative_questions':neg,
                    'all_reference_evidence_found':sum(m['all_reference_excerpts_available'] for m in metrics),
                    'mean_reference_recall':sum(m['reference_recall'] for m in metrics)/len(metrics),
                    'mean_precision_at_k':sum(m['precision_at_k'] for m in metrics)/len(metrics),
                    'scripted_positive_answers':sum(r['payload']['status']=='answered' for r in rows),
                    'scripted_negative_refusals':sum(r['payload']['status']=='insufficient_evidence' and r['expected_status']=='insufficient_evidence' for r in rows),
                    'citation_failures':0,'schema_failures':0})
            save(OUT/'contract_results.json',results)
            summary={'status':'PARTIALLY READY','plans_collected':len(programs),'current_directory_programs':quality['current_directory_count'],
                'missing_handbook_programs':quality['missing_programs'],'course_program_pairs':len(courses),
                'unique_course_codes':len({c['course_code'] for c in courses}),'chunks':manifest['chunks'],
                'question_count':len(cases),'programs_with_reference_questions':len({c['program_id'] for c in cases if c['program_id']}),
                'results':summaries,'foreign_program_or_version_hits':len(leaks),'withheld_summary_hits':len(withheld_leaks),
                'adversarial_foreign_course_probes':len(isolation),'unknown_plan_bindings_rejected':len(programs)*2,
                'index_path':str(INDEX),'live_llm_calls':0,'paid_calls':0,
                'evaluation_type':'Real scoped CPU dense retrieval plus exact-course-code metadata priority; explicit scripted offline provider for citation path only.',
                'regression_suite':'pending','frozen_cases_sha256':hashlib.sha256((OUT/'cases.json').read_bytes()).hexdigest()}
            save(OUT/'summary.json',summary);print(json.dumps(summary,ensure_ascii=False),flush=True)
        finally:owner.close()
