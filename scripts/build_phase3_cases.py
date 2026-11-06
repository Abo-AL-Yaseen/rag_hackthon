"""Add paraphrase/dialect cases without changing any Phase 1/2 fixture."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    folder=ROOT/'data/sample'
    data=json.loads((folder/'phase2_questions.json').read_text(encoding='utf-8'))
    cases=data['questions']
    rules=json.loads((folder/'phase2_mock_rules.json').read_text(encoding='utf-8'))['rules']
    original={c['id']:c for c in cases}
    by_question={r['question']:r for r in rules}
    for ident,base,question,tag in [
        ('p301','q01','قديش بقدر أخلي الكتب المستعارة معي؟','palestinian_dialect'),
        ('p302','q08','نسيت الباسورد، كيف برجع أفوت على حسابي؟','palestinian_dialect'),
        ('p303','q09','ما الحد الأقصى لحجم الملف المرفق بطلب المساعدة؟','arabic_paraphrase'),
        ('p304','q02','At what times is the library available on Saturdays?','english_paraphrase')]:
        case={**original[base],'id':ident,'question':question,'language':'en' if base=='q02' else 'ar',
              'tags':[tag],'reference_case':base}
        cases.append(case)
        if case['language']==original[base]['language']:
            rules.append({**by_question[original[base]['question']],'question':question})
        else:
            # q08's Arabic paraphrase gets the actual Arabic source excerpt.
            pages=json.loads((folder/'synthetic_pages.json').read_text(encoding='utf-8'))['pages']
            page=next(p for p in pages if p['document_id']=='support' and p['page']==1)
            excerpt=page['text'].split('To reset')[0].strip()
            case['reference_answer']='بوابة الدعم، استعادة الحساب، ثم تأكيد البريد الإلكتروني.'
            rules.append({'question':question,'selections':[{'document_id':'support','page':1,'excerpt':excerpt}]})
    for case in cases:
        case['tags']=case.get('tags',[])
        case['supported']=True
    skipped=[{'id':'turn01','question':'And how many days is that?','supported':False,
              'reason':'Core v1 API is stateless; no conversation/session input is supported.'},
             {'id':'turn02','question':'ومتى يغلق؟','supported':False,
              'reason':'Backend must resolve the antecedent; history cannot be silently inferred.'}]
    (folder/'phase3_questions.json').write_text(json.dumps({'synthetic':True,'questions':cases,
        'unsupported_multi_turn_probes':skipped},ensure_ascii=False,indent=2),encoding='utf-8')
    (folder/'phase3_mock_rules.json').write_text(json.dumps({'synthetic':True,'scripted':True,'rules':rules},
        ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Prepared {len(cases)} standalone cases plus {len(skipped)} explicitly unsupported multi-turn probes.')


if __name__=='__main__': main()
