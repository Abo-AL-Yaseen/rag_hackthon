"""Bounded public official university source collection; no accounts or LLMs."""
import concurrent.futures
import hashlib
import json
import sys
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse,urljoin
import requests

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'.local/engineering_faculty_20261107'
RUN.mkdir(parents=True,exist_ok=True)
RAW=ROOT/'data/raw/engineering_faculty_20261107'
P=ROOT/'data/processed/engineering_faculty_20261107'
RAW.mkdir(parents=True,exist_ok=True);P.mkdir(parents=True,exist_ok=True)
from html_tables import Tree,clean

def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

def preserve_snapshot():
    paths=['data/raw/engineering_mvp_20261107','data/processed/engineering_mvp_20261107',
           'data/index/engineering_ce_2021_1_20261107_v1','.local/engineering_mvp_20261107']
    records={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
      for folder in paths for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts and 'pytest_temp' not in p.parts}
    target=RUN/'previous_dataset_hashes.json'
    if target.exists():assert json.loads(target.read_text(encoding='utf-8'))==records,'Previous CE artifacts changed'
    else:save(target,records)

def fetch(name,url):
    assert urlparse(url).hostname.endswith('.najah.edu')
    target=RAW/name;meta=RAW/(name+'.metadata.json')
    if target.exists() and meta.exists():return json.loads(meta.read_text(encoding='utf-8'))
    try:
        with requests.get(url,stream=True,timeout=(15,45),headers={'User-Agent':'Academic-source-verification/1.0'}) as r:
            r.raise_for_status();assert urlparse(r.url).hostname.endswith('.najah.edu')
            data=bytearray()
            for chunk in r.iter_content(65536):
                data.extend(chunk)
                if len(data)>10_000_000:raise ValueError('10MB per HTML source cap')
            target.write_bytes(data)
            record={'file':name,'url':url,'final_url':r.url,'retrieved_utc':datetime.now(timezone.utc).isoformat(),
                    'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'status':'collected'}
            save(meta,record);return record
    except Exception as e:
        return {'file':name,'url':url,'status':'missing','error':type(e).__name__+': '+str(e)[:160]}

def tree(name):return Tree((RAW/name).read_text(encoding='utf-8')).root

def discover(lang):
    filename=f'program_directory_{lang}.html'
    rec=fetch(filename,f'https://www.najah.edu/{lang}/academic/undergraduate-programs/')
    assert rec['status']=='collected'
    t=tree(filename)
    # Each official directory program link embeds its faculty and bachelor label.
    cards=[]
    for a in t.find('a'):
        href=a.attrs.get('href','');text=clean(a.text())
        if '/undergraduate-programs/program/' not in href:continue
        if ('Faculty of Engineering' if lang=='en' else 'كلية الهندسة') not in text:continue
        if ('Bachelor' if lang=='en' else 'بكالوريوس') not in text:continue
        slug=href.split('/program/')[1].split('/')[0]
        # Names are in headings; preserve exact text rather than translate.
        heads=a.find('h3')+a.find('h4')+a.find('h2')
        name=clean(heads[0].text()) if heads else text.split('Faculty of Engineering' if lang=='en' else 'كلية الهندسة')[0].strip()
        cards.append({'slug':slug,'name':name,'directory_card_text':text,'program_url':urljoin(rec['url'],href),
                      'membership_source_url':rec['url']})
    unique={c['slug']:c for c in cards}
    return unique,rec

def collect_program(program):
    slug=program['slug'];plans={}
    for lang in ('ar','en'):
        lang_slug=program.get('slugs_by_language',{}).get(lang,slug)
        base=f'https://www.najah.edu/{lang}/academic/undergraduate-programs/program/{lang_slug}/study-plan/'
        default=fetch(f'{slug}_{lang}_default.html',base)
        if default['status']!='collected':plans[lang]={'acquisition':default};continue
        t=tree(default['file'])
        options=[o for s in t.find('select') if s.attrs.get('name')=='study_plan' for o in s.find('option')]
        versions=[o.attrs.get('value') for o in options if o.attrs.get('value')]
        latest=max(versions,key=lambda v:tuple(int(x) for x in v.split('-'))) if versions else None
        selected=[o.attrs['value'] for o in options if 'selected' in o.attrs]
        explicit=fetch(f'{slug}_{lang}_{latest}.html',base+'?study_plan='+latest) if latest else default
        plans[lang]={'available_versions':versions,'selected_default':selected,'latest_published_version':latest,
                    'acquisition':explicit,'default_acquisition':default}
    program['plans']=plans
    save(P/(slug+'_discovery.json'),program)
    return program

if __name__=='__main__':
    if '--collect-public' not in sys.argv:
        raise SystemExit('Historical collector: explicit --collect-public authorization required; no network performed')
    preserve_snapshot()
    en,en_source=discover('en');ar,ar_source=discover('ar')
    aliases={'chemical-engineeringpharmaceutical-engineering':'lhnds-lkymyy-fraay-hnds-sydlny',
             'mechanical-engineeringautomotive-engineering':'rysy-lhnds-lmyknyky-fraay-hnds-lmrkbt'}
    assert set(en)=={next((e for e,a in aliases.items() if a==s),s) for s in ar}
    programs=[{'slug':s,'name_en':en[s]['name'],'name_ar':ar[aliases.get(s,s)]['name'],
       'slugs_by_language':{'en':s,'ar':aliases.get(s,s)},
       'membership':'current_official_undergraduate_directory',
       'directory_en':en[s],'directory_ar':ar[aliases.get(s,s)]} for s in sorted(en)]
    # Explicit handbook-only candidate kept apart from currently listed directory programs.
    programs.append({'slug':'materials-science-engineering','name_en':None,'name_ar':'هندسة علوم المواد',
                     'membership':'latest_handbook_page_47_only; absent_from_current_undergraduate_directory',
                     'directory_en':None,'directory_ar':None})
    for name,url in [('faculty_home.html','https://eng.najah.edu/en/'),('faculty_departments.html','https://eng.najah.edu/en/study/departments/'),
                     ('faculty_directory.html','https://www.najah.edu/en/academic/faculties/')]:
        fetch(name,url)
    fetch('materials_info_card.html','https://www.najah.edu/en/academic/undergraduate-programs/program/materials-science-engineering/info-card/')
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(collect_program,programs))
    save(P/'program_discovery.json',results)
    for r in results:print(json.dumps({'slug':r['slug'],'ar':r['name_ar'],'en':r['name_en'],'membership':r['membership'],
        'versions':{l:p.get('available_versions') for l,p in r['plans'].items()},
        'status':{l:p['acquisition']['status'] for l,p in r['plans'].items()}},ensure_ascii=False),flush=True)
