"""Conservative, non-scripted local excerpt selection. This is NOT an LLM.

Only supported intent families are handled. Actual retrieved headings/rows must
cover the requested fact; no reference answers, numeric rules or question bank.
Contract mode remains mock because v1.0.0 permits only mock/remote modes.
"""
import json
import re

from ..academic_decisions import intent, normalize
from .contracts import ProviderResult


class LocalAcademicEvidenceProvider:
    is_mock = True

    def generate(self, request):
        need=intent(request.question)
        q=normalize(request.question)
        rows=[]
        for hit in request.evidence:
            text=hit.chunk.text
            header,_,body=text.partition('\n')
            # Never translate evidence or pretend Arabic policy text is English.
            ar=bool(re.search(r'[\u0600-\u06ff]', text))
            if (request.language=='ar') != ar: continue
            rows.append((hit,normalize(header),body or header))
        chosen=[]
        def matching(pattern):
            return [row for row in rows if re.search(pattern,row[1])]
        if need=='catalog':
            chosen=[(hit,header,hit.chunk.text) for hit,header,body in rows
                    if hit.chunk.document_id=='runtime_catalog_'+request.language][:1]
        elif need=='attendance':
            limits=matching(r'حد الغياب')
            penalties=matching(r'عقوبه.*غياب')
            if limits and penalties:
                chosen=limits[:1]+penalties[:1]+matching(r'الغياب بعذر')[:1]
        elif need=='withdrawal':
            late=matching(r'الانسحاب من المساق.*نهايه')
            finance=matching(r'الحق المالي')
            if late and finance:
                chosen=late[:1]+finance[:1]+matching(r'السحب والاضافه')[:1]
        elif need=='add_drop':
            chosen=matching(r'السحب والاضافه')[:1]
        elif need=='warning':
            threshold=matching(r'الانذار.*الهندسه')
            exception=matching(r'الانذار في الفصل الاول')
            if threshold and exception: chosen=threshold[:1]+exception[:1]
        elif need=='graduation':
            for hit,header,body in rows:
                if re.search(r'مجموع الساعات المعتمده|total required credits',header):
                    # Summary's full first line includes program, plan and total.
                    chosen=[(hit,header,hit.chunk.text.split('\n')[0])];break
        elif need=='course':
            codes=set(re.findall(r'(?<!\d)\d{6,10}(?!\d)',q))
            if len(codes)==1:
                code=next(iter(codes))
                for row in rows:
                    hit,header,body=row
                    if not re.search(r'(?:رمز المساق|Course Code):\s*'+re.escape(code)+r'(?!\d)',body): continue
                    # Full course row preserves its subject and conditions.
                    chosen=[row];break
        claims=[]
        for hit,header,quote in chosen[:4]:
            if not quote or len(quote)>1500 or quote not in hit.chunk.text: continue
            claims.append({'text':quote,'evidence':[{'chunk_id':hit.chunk.chunk_id,'excerpt':quote}]})
        return ProviderResult(json.dumps({'status':'answered' if claims else 'insufficient_evidence',
            'reason':'supported' if claims else 'missing_evidence','claims':claims},ensure_ascii=False))
