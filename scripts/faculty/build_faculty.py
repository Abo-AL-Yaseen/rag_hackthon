"""Parse official bilingual tables; preserve published operators and unknowns."""
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from collect_faculty import ROOT,RUN,RAW,P,Tree,clean,save,preserve_snapshot

if '--rebuild-reviewed-local-dataset' not in sys.argv:
    raise SystemExit('Offline authoring only: explicit --rebuild-reviewed-local-dataset required; preserve validated datasets')

INPUTS=P/'inputs';INPUTS.mkdir(exist_ok=True)
OLD=ROOT/'data/processed/engineering_mvp_20261107'
PDF=ROOT/'data/raw/engineering_mvp_20261107/handbook_2026_2027.pdf'
PDF_URL='https://www-cdn.najah.edu/media/filer_public/d2/d2/d2d2c0d9-7ab5-408a-bccb-947bc667e202/dlyl_ltlb_25.pdf'
# Visually verified handbook Engineering table on physical page 48, retained
# from the previous review. Order: university, speciality, elective, free, total.
HANDBOOK={
 'civil-engineering':[12,113,12,0,137], 'geomatics-engineering':[19,126,12,2,159],
 'architectural-engineering':[19,132,12,2,165], 'building-engineering':[12,116,9,0,137],
 'urban-planning-engineering':[19,129,12,2,162], 'mechanical-engineering':[12,116,9,0,137],
 'industrial-engineering':[12,116,9,0,137], 'computer-engineering':[19,129,15,0,163],
 'electrical-engineering':[12,116,9,0,137], 'telecommunication-engineering':[19,128,12,2,161],
 'mechatronics-engineering':[12,116,9,0,137], 'energy-environmental-engineering':[12,116,9,0,137],
 'materials-science-engineering':[19,127,12,2,160],
 'mechanical-engineeringautomotive-engineering':[19,132,9,2,162],
 'chemical-engineering':[12,115,9,0,136],
 'chemical-engineeringpharmaceutical-engineering':[19,131,12,0,162]}
UNCERTAIN_HANDBOOK_NAMES={'building-engineering':'هندسة تكنولوجيا وأنظمة البناء',
                         'energy-environmental-engineering':'هندسة أنظمة الطاقة'}

def direct(n,tag):return [c for c in n.children if hasattr(c,'tag') and c.tag==tag]
def serialize(n):return {'tag':n.tag,'attrs':n.attrs,'children':[serialize(c) if hasattr(c,'tag') else c for c in n.children]}

def expression(cell):
    """No AND is invented when the website only publishes separate bullets."""
    outer=direct(cell,'ul');groups=[]
    if not outer:return {'operator':None,'groups':[],'status':'not_listed'}
    for g in direct(outer[0],'li'):
        inner=direct(g,'ul');leaves=direct(inner[0],'li') if inner else [g]
        entries=[{'text':clean(li.text()),'codes':re.findall(r'\b\d{6,10}\b',li.text()),
                  'tooltip':li.attrs.get('title'),'css_class':li.attrs.get('class')} for li in leaves]
        raw=' '.join(e['text'] for e in entries)
        explicit_or=bool(re.search(r'\bor\b|أو',raw,re.I))
        explicit_and=bool(re.search(r'\band\b|\sو\s',raw,re.I))
        op='OR' if explicit_or and not explicit_and else 'AND' if explicit_and and not explicit_or else None
        groups.append({'operator':op,'entries':entries,
                       'operator_basis':'explicit_connector' if op else 'single_entry' if len(entries)==1 else 'not_explicit'})
    return {'operator':None,'groups':groups,'status':'intergroup_operator_not_explicit' if len(groups)>1 else 'published_group',
            'note':'Group boundaries are preserved; separate bullets are not promoted into an authoritative AND rule.'}

def signature(row):
    return (row['credit_hours'],[[[e['codes'],e['css_class']] for e in g['entries']] for g in row['prerequisites']['groups']],
            [g['operator'] for g in row['prerequisites']['groups']])

def parse(program,lang):
    info=program['plans'][lang];acq=info['acquisition']
    if acq['status']!='collected':return None
    tree=Tree((RAW/acq['file']).read_text(encoding='utf-8')).root
    options=[o.attrs.get('value') for s in tree.find('select') if s.attrs.get('name')=='study_plan' for o in s.find('option') if 'selected' in o.attrs]
    assert options==[info['latest_published_version']],(program['slug'],lang,'wrong selected version',options)
    tables=tree.find('table');heads=tree.find('h4');assert len(tables)==len(heads)>0
    totals=re.findall(r'Student must complete\s+(\d+)\s+credit hours',clean(tree.text())) if lang=='en' else re.findall(r'يجب على الطالب (?:ان|أن) يكمل\s+(\d+)\s+ساعة معتمدة',clean(tree.text()))
    assert totals,(program['slug'],lang,'missing total')
    records={};groups=[];duplicates=[]
    for ti,(table,head) in enumerate(zip(tables,heads),1):
        heading=clean(head.text());required=int(re.findall(r'\d+',heading)[-1]);count=0;hours_sum=0
        for ri,row in enumerate(table.find('tr'),1):
            cells=direct(row,'td')
            if len(cells)!=4:continue
            code,name,hours,prereq=[clean(c.text()) for c in cells]
            assert re.fullmatch(r'\d{6,10}',code),(program['slug'],code)
            credit=float(hours) if re.fullmatch(r'\d+(?:\.\d+)?',hours) else None
            if credit is not None and credit.is_integer():credit=int(credit)
            record={'code':code,'name':name,'credit_hours':credit,'credit_hours_raw':hours,'prerequisite_text':prereq,
                'prerequisites':expression(cells[3]),'prerequisite_html_tree':serialize(cells[3]),'group_index':ti,'group_heading':heading,
                'table_index':ti,'row_index':ri,'source_url':acq['url'],'source_file':acq['file'],
                'document_title':clean(tree.find('title')[0].text()),'plan_version':info['latest_published_version'],
                'academic_year':None,'academic_year_note':'No academic-year span is asserted from a plan identifier alone.',
                'plan_year_label':info['latest_published_version'].split('-')[0],
                'physical_pdf_page':None,'page_kind':'HTML document','engine_page_number':1}
            if code in records:
                duplicates.append({'code':code,'same_values':signature(records[code])==signature(record),'new_row':record})
                continue
            records[code]=record;count+=1;hours_sum+=credit or 0
        groups.append({'heading':heading,'required_credits':required,'listed_course_options':count,'listed_credit_sum':hours_sum})
    return {'courses':records,'groups':groups,'total_credits':int(totals[0]),'duplicate_rows':duplicates,
            'sum_group_requirements':sum(g['required_credits'] for g in groups),'selected_version':options[0]}

programs=json.loads((P/'program_discovery.json').read_text(encoding='utf-8'))
all_courses=[];pages=[];documents=[];catalog=[];row_issues=[];conflicts=[]
for program in programs:
    pid=program['slug'].lower();program['program_id']=pid
    parsed={lang:parse(program,lang) for lang in ('ar','en')}
    if not all(parsed.values()):
        program.update(collection_status='missing_plan',indexed=False,course_count=0,handbook_credits=HANDBOOK[pid][-1],
            missing_reason='Both current official study-plan endpoints return HTTP 404.',
            name_en=program['name_en'] or 'Materials Science Engineering',
            name_en_source='Official search-indexed Info Card title; endpoint now 404, historical listing only')
        catalog.append(program);continue
    assert parsed['ar']['selected_version']==parsed['en']['selected_version']
    version=parsed['en']['selected_version'];plan_issues=[]
    if parsed['ar']['total_credits']!=parsed['en']['total_credits']:plan_issues.append('bilingual_total_mismatch')
    for lang,data in parsed.items():
        if data['sum_group_requirements']!=data['total_credits']:plan_issues.append(lang+'_requirement_sum_mismatch')
        if data['duplicate_rows']:plan_issues.append(lang+'_duplicate_course_rows')
    total=parsed['en']['total_credits'];book=HANDBOOK[pid]
    web_groups=[g['required_credits'] for g in parsed['en']['groups']]
    # A missing free-course table does not contradict an explicitly zero free
    # requirement in the handbook. Do not invent a missing table/value either.
    conflict=total!=book[-1] or any(v!=book[i] for i,v in enumerate(web_groups))
    if conflict:
        conflicts.append({'program_id':pid,'plan_version':version,'web_total':total,'web_groups':[g['required_credits'] for g in parsed['en']['groups']],
           'handbook_total':book[-1],'handbook_groups':book[:-1],'handbook_version':'2026/2027','physical_pdf_page':48,
           'source_url':PDF_URL,'name_mapping':'unconfirmed_rename_or_different_program' if pid in UNCERTAIN_HANDBOOK_NAMES else 'same_program_name_or_published_minor_variant',
           'handbook_name_ar':UNCERTAIN_HANDBOOK_NAMES.get(pid,program['name_ar']),
           'resolution':'UNRESOLVED. Summary withheld from program retrieval; no current-intake applicability or program equivalence inferred.'})
    codes=set(parsed['ar']['courses'])|set(parsed['en']['courses']);safe_count=0
    for code in sorted(codes):
        rows={l:p['courses'].get(code) for l,p in parsed.items()};flags=[];quarantine=False
        if not all(rows.values()):flags.append('missing_bilingual_course_row');quarantine=True
        elif signature(rows['ar'])!=signature(rows['en']):flags.append('bilingual_credit_or_prerequisite_mismatch');quarantine=True
        for lang,r in rows.items():
            if not r:continue
            if r['credit_hours'] is None:flags.append('missing_credit_hours');quarantine=True
            expr=r['prerequisites'];leaves=[e for g in expr['groups'] for e in g['entries']]
            refs=[c for e in leaves for c in e['codes']]
            if len(refs)!=len(set(refs)):flags.append('duplicate_published_prerequisite_code')
            if len(expr['groups'])>1:flags.append('intergroup_AND_OR_not_explicit')
            if any(e['css_class'] for e in leaves):flags.append('colored_prerequisite_semantics_unverified')
            external=sorted(set(refs)-codes)
            if external:flags.append('prerequisite_codes_outside_this_plan')
            r['external_or_legacy_prerequisite_codes']=external
            if '\ufffd' in r['name']+r['prerequisite_text'] or re.search('[\ufb50-\ufdff\ufe70-\ufefc]',r['name']+r['prerequisite_text']):
                flags.append('bad_arabic_unicode');quarantine=True
        flags=sorted(set(flags))
        if flags:row_issues.append({'program_id':pid,'version':version,'course_code':code,'flags':flags,'quarantined':quarantine})
        combined={'program_id':pid,'program_name_ar':program['name_ar'],'program_name_en':program['name_en'],
                  'plan_version':version,'course_code':code,'ar':rows['ar'],'en':rows['en'],
                  'quality_flags':flags,'quarantined':quarantine}
        all_courses.append(combined)
        if not quarantine:safe_count+=1
        for lang,r in rows.items():
            if not r:continue
            ident=f"eng_{pid}_{version}_{code}_{lang}"
            pre=r['prerequisite_text'] or ('غير مذكور في الخانة المنشورة' if lang=='ar' else 'Not listed in the published cell')
            expr=r['prerequisites']
            grouptext=' | '.join(' / '.join(e['text'] for e in g['entries']) for g in expr['groups'])
            if lang=='ar':
                quote=f"رمز المساق: {code}؛ اسم المساق: {r['name']}؛ الساعات المعتمدة: {r['credit_hours_raw']}؛ المتطلبات السابقة: {pre}."
                text=f"{program['name_ar']} | الخطة المنشورة {version}\n{quote}"
                if grouptext and len(expr['groups'])>1:text+='\nالمجموعات كما نشرت (لا يفسر الفاصل | كعلاقة AND): '+grouptext
                if flags:text+='\nتنبيه: راجع قيود الجودة؛ لا يستنتج عدم وجود متطلب من خانة فارغة، ولا تعتمد أهلية التسجيل على علاقة غير موضحة.'
            else:
                quote=f"Course Code: {code}; Course Name: {r['name']}; Credit Hours: {r['credit_hours_raw']}; Prerequests: {pre}."
                text=f"{program['name_en']} | published plan {version}\n{quote}"
                if grouptext and len(expr['groups'])>1:text+='\nPublished groups (| does not assert AND): '+grouptext
                if flags:text+='\nQuality warning: missing prerequisites and unlabelled group/color semantics do not establish registration eligibility.'
            pages.append({'document_id':ident,'source':r['source_file'],'page':1,'text':text,'version':f'published-plan-{version}'})
            documents.append({'document_id':ident,'scope':'program','program_id':pid,'plan_version':version,
                'retrieval_enabled':not quarantine,'kind':'course','language':lang,'course_code':code,
                'source_url':r['source_url'],'source_file':r['source_file'],'document_title':r['document_title'],
                'program_name_ar':program['name_ar'],'program_name_en':program['name_en'],
                'table_index':r['table_index'],'row_index':r['row_index'],'physical_pdf_page':None,'engine_page_number':1,
                'quality_flags':flags,'reference_quote':quote})
    for lang,data in parsed.items():
        r=program['plans'][lang]['acquisition'];ident=f'eng_{pid}_{version}_summary_{lang}'
        name=program['name_ar'] if lang=='ar' else program['name_en']
        quote=f'{name} | الخطة المنشورة {version} | مجموع الساعات المعتمدة: {total}.' if lang=='ar' else f'{name} | published plan {version} | Total required credits: {total}.'
        text=quote+'\n'+'\n'.join(g['heading'] for g in data['groups'])
        if conflict:text+='\nWITHHELD: unresolved discrepancy with the 2026/2027 handbook; no current-intake graduation advice.'
        pages.append({'document_id':ident,'source':r['file'],'page':1,'text':text,'version':f'published-plan-{version}'})
        documents.append({'document_id':ident,'scope':'program','program_id':pid,'plan_version':version,'language':lang,
            'kind':'plan_summary','retrieval_enabled':not conflict and not plan_issues,'withheld_reason':'graduation_conflict' if conflict else None,
            'source_url':r['url'],'source_file':r['file'],'engine_page_number':1,'physical_pdf_page':None,'reference_quote':quote,
            'document_title':clean(Tree((RAW/r['file']).read_text(encoding='utf-8')).root.find('title')[0].text())})
    program.update(collection_status='collected',indexed=True,selected_version=version,academic_year=None,
       academic_year_note='Published selector version retained; academic-year span/current intake not inferred.',
       course_count=len(codes),verified_course_count=safe_count,graduation_credits=total,
       graduation_groups=parsed['en']['groups'],handbook_credits=book[-1],handbook_groups=book[:-1],
       handbook_name_ar=UNCERTAIN_HANDBOOK_NAMES.get(pid,program['name_ar']),
       handbook_name_mapping='unconfirmed_rename_or_different_program' if pid in UNCERTAIN_HANDBOOK_NAMES else 'same_program_name_or_published_minor_variant',
       graduation_conflict=conflict,plan_quality_issues=plan_issues,
       bilingual_course_code_set_agrees=set(parsed['ar']['courses'])==set(parsed['en']['courses']))
    catalog.append(program)

# Reuse the reviewed university-wide clauses, without touching CE source/evidence.
policy_input=json.loads((OLD/'inputs/engineering_policies.json').read_text(encoding='utf-8'))['pages']
old_provenance={d['document_id']:d for d in json.loads((OLD/'provenance.json').read_text(encoding='utf-8'))}
for page in policy_input:
    pages.append(page)
    documents.append({'document_id':page['document_id'],'scope':'regulations','program_id':None,'plan_version':None,
      'kind':'policy','retrieval_enabled':True,'source_url':PDF_URL,'engine_page_number':page['page'],
      'physical_pdf_page':page['page'],'article':old_provenance[page['document_id']]['article'],'language':'ar',
      'document_title':'دليل الطالب 2027/2026','reference_quote':page['text'].split('\n',1)[1],
      'source_file':'handbook_2026_2027.pdf','reused_reviewed_transcript':True})
save(INPUTS/'faculty_pages.json',{'pages':pages})
save(P/'courses.json',all_courses);save(P/'program_catalog.json',catalog);save(P/'documents.json',documents)
save(P/'data_quality.json',{'conflicts':conflicts,'course_row_issues':row_issues,
    'quarantined_course_count':sum(c['quarantined'] for c in all_courses),
    'ambiguous_AND_OR_note':'Explicit OR/AND connectors and nested source trees preserved. Unlabelled cross-group operators remain unknown, never inferred.',
    'missing_programs':[p['program_id'] for p in catalog if not p['indexed']],
    'handbook_source_url':PDF_URL,'handbook_sha256':hashlib.sha256(PDF.read_bytes()).hexdigest(),
    'current_directory_count':sum(p['membership']=='current_official_undergraduate_directory' for p in catalog)})
with (P/'courses.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=['program_id','plan_version','course_code','name_ar','name_en','hours_ar','hours_en',
      'prerequisites_ar','prerequisites_en','source_ar','source_en','quality_flags','quarantined']);writer.writeheader()
    for c in all_courses:
        writer.writerow({'program_id':c['program_id'],'plan_version':c['plan_version'],'course_code':c['course_code'],
          **{f'{key}_{lang}':(c[lang] or {}).get(field) for lang in ('ar','en') for key,field in [('name','name'),('hours','credit_hours'),('prerequisites','prerequisite_text'),('source','source_url')]},
          'quality_flags':' | '.join(c['quality_flags']),'quarantined':c['quarantined']})
preserve_snapshot()
print(json.dumps({'plans':sum(p['indexed'] for p in catalog),'course_program_pairs':len(all_courses),
 'unique_course_codes':len({c['course_code'] for c in all_courses}),'source_records':len(pages),
 'flagged_rows':len(row_issues),'quarantined_courses':sum(c['quarantined'] for c in all_courses),'graduation_conflicts':len(conflicts),
 'per_program':[{k:p.get(k) for k in ['program_id','selected_version','course_count','verified_course_count','graduation_credits','handbook_credits','graduation_conflict','plan_quality_issues']} for p in catalog]},ensure_ascii=False),flush=True)
