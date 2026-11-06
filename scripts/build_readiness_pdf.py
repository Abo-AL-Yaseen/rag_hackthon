"""Create new, explicitly synthetic bilingual PDFs using the installed PDF engine."""
import hashlib
import json
from pathlib import Path

import fitz

ROOT=Path(__file__).resolve().parents[1]
CASES=[
    {'id':'ar1','language':'ar','file':'readiness_arabic.pdf','page':1,
     'question':'كم تستمر ورشة الروبوتات؟','excerpt':'تستمر ورشة الروبوتات تسعة أيام'},
    {'id':'ar2','language':'ar','file':'readiness_arabic.pdf','page':2,
     'question':'متى تبدأ جولة المتحف يوم الجمعة؟','excerpt':'تبدأ جولة المتحف يوم الجمعة الساعة الرابعة عصراً'},
    {'id':'en1','language':'en','file':'readiness_english.pdf','page':1,
     'question':'How long is an observatory telescope reservation?',
     'excerpt':'The observatory telescope reservation lasts forty minutes.'},
    {'id':'en2','language':'en','file':'readiness_english.pdf','page':2,
     'question':'Where can I reserve the rehearsal room?','excerpt':'Reserve the rehearsal room at desk Delta.'},
]


def main():
    target=ROOT/'data/sample/readiness/inputs'
    target.mkdir(parents=True,exist_ok=True)
    render=ROOT/'tmp/pdfs/readiness'; render.mkdir(parents=True,exist_ok=True)
    hashes={}
    for name in ('readiness_arabic.pdf','readiness_english.pdf'):
        cases=[c for c in CASES if c['file']==name]
        path=target/name
        with fitz.open() as doc:
            for case in cases:
                page=doc.new_page(width=595,height=842)
                page.insert_text((48,45),'SYNTHETIC READINESS FIXTURE - NOT THE HACKATHON DATASET',fontsize=9)
                direction='rtl' if case['language']=='ar' else 'ltr'
                box=fitz.Rect(48,100,547,350)
                before=set(page.get_contents())
                result=page.insert_htmlbox(box,'<div style="font-size:16px;line-height:1.8;direction:'+direction+'">'+case['excerpt']+'</div>')
                assert result[0]>=0
                if case['language']=='ar':
                    # Standard accessible ActualText supplies original Unicode for
                    # the shaped glyphs; do not rely on presentation-form mappings.
                    actual=(b'\xfe\xff'+case['excerpt'].encode('utf-16-be')).hex().encode('ascii')
                    for xref in set(page.get_contents())-before:
                        content=doc.xref_stream(xref)
                        doc.update_stream(xref,b'/Span <</ActualText <'+actual+b'>>> BDC\n'+content+b'\nEMC')
                page.insert_text((48,790),f"Synthetic preparation | Page {case['page']}",fontsize=10)
            doc.save(path)
        with fitz.open(path) as doc:
            for case,page in zip(cases,doc):
                extracted='\n'.join(b[4].strip() for b in page.get_text('blocks',sort=True) if b[6]==0)
                if case['excerpt'] not in extracted:
                    raise RuntimeError('Fixture extraction differs from original text: '+case['id'])
                page.get_pixmap(matrix=fitz.Matrix(1.2,1.2)).save(str(render/f"{path.stem}-{case['page']}.png"))
        hashes[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    (target.parent/'cases.json').write_text(json.dumps({'synthetic':True,'cases':CASES},ensure_ascii=False,indent=2),encoding='utf-8')
    rules=[{'question':c['question'],'selections':[{'document_id':Path(c['file']).stem,'page':c['page'],'excerpt':c['excerpt']}]} for c in CASES]
    (target.parent/'mock_rules.json').write_text(json.dumps({'synthetic':True,'scripted':True,'rules':rules},ensure_ascii=False,indent=2),encoding='utf-8')
    for case in CASES:
        (target.parent/f"request_{case['id']}.json").write_text(json.dumps({'question':case['question'],'language':case['language']},ensure_ascii=False,indent=2),encoding='utf-8')
    (target.parent/'manifest.json').write_text(json.dumps({'synthetic':True,'pdf_sha256':hashes},indent=2),encoding='utf-8')
    print('Created two new PDFs, four physical pages, bilingual requests and explicitly scripted mock rules.')


if __name__=='__main__': main()
