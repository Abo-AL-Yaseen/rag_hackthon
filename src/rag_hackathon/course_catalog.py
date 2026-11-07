"""Complete, paginated queries over bound indexed rows, never top-k results."""
import json
import re
from pathlib import Path
from types import SimpleNamespace

from .schema import Chunk, Hit
from .service import RAGService, RAGPolicy
from .generation.contracts import ProviderResult


class _Quote:
    is_mock=True
    def generate(self,request):
        hit=request.evidence[0];text=hit.chunk.text
        return ProviderResult(json.dumps({'status':'answered','reason':'supported','claims':[
            {'text':text,'evidence':[{'chunk_id':hit.chunk.chunk_id,'excerpt':text}]}]},ensure_ascii=False))


class CourseCatalog:
    def __init__(self,documents,programs,reviewed=()):
        self.rows={};self.expected={};self.locators={};self.services={}
        reviewed={(r['program_id'],r['plan_version'],r['course_code']):r for r in reviewed}
        names={(p['program_id'],p['plan_version']):p for p in programs}
        for d in documents:
            if d.get('kind')!='course':continue
            key=(d['program_id'],d['plan_version'],d.get('language'))
            self.expected.setdefault(key,set()).add(d['course_code'])
            if d.get('retrieval_enabled',True) is not True:continue
            language=key[2];quote=d.get('reference_quote','')
            pattern=(r'رمز المساق:\s*(\d+)؛ اسم المساق:\s*(.*?)؛ الساعات المعتمدة:\s*(\d+(?:\.\d+)?)؛' if language=='ar' else
                     r'Course Code:\s*(\d+); Course Name:\s*(.*?); Credit Hours:\s*(\d+(?:\.\d+)?);')
            match=re.search(pattern,quote)
            if not match or match[1]!=d['course_code']:continue
            code,name,credits=match.groups();credits=float(credits);credits=int(credits) if credits.is_integer() else credits
            row={'course_code':code,'name':name,'credit_hours':credits,'classification':None,'year':None,'semester':None,
                 'document_id':d['document_id'],'source_url':d.get('source_url'),'document_title':d.get('document_title'),
                 'table_index':d.get('table_index'),'row_index':d.get('row_index'),'reference_quote':quote,
                 'quality_flags':d.get('quality_flags',[])}
            extra=reviewed.get((key[0],key[1],code),{}).get(language,{})
            # Supplemental grouping is used only when reviewed structured values
            # agree with the bound official row and its table/row locator.
            if (extra.get('name')==name and extra.get('credit_hours')==credits and
                    extra.get('table_index')==d.get('table_index') and extra.get('row_index')==d.get('row_index')):
                row['classification']=extra.get('group_heading')
                row['year']=extra.get('year');row['semester']=extra.get('semester')
            self.rows.setdefault(key,{})[code]=row
        for key,rows in self.rows.items():
            program,version,language=key;name=names.get(key[:2],{}).get('name_'+language) or program
            total=len(rows);complete=total==len(self.expected[key])
            text=(f'المساقات الموثقة في خطة {name} {version}: {total}. القائمة مرقمة الصفحات أدناه؛ عدد المساقات لا يعني أن جميعها إلزامية.' if language=='ar' else
                  f'Verified course entries in {name}, plan {version}: {total}. The full paginated list is below; not all listed courses are compulsory.')
            if not complete:text+=(' القائمة مجموعة جزئية من الصفوف المفهرسة.' if language=='ar' else ' This is an incomplete subset of indexed rows.')
            ident=f'course_catalog_{program}_{version}_{language}'
            chunk=Chunk(ident,ident,'verified_indexed_course_catalog',1,text,0,len(text),'bound-course-catalog-v1')
            retriever=SimpleNamespace(search=lambda q,k,h=Hit(chunk,1.):[h])
            self.services[key]=RAGService(retriever,_Quote(),policy=RAGPolicy(top_k=1))
            self.locators[ident]={'source_type':'course_catalog','source_url':None,'document_title':name+' / '+version,
                'physical_pdf_page':None,'engine_page_number':1,'table_index':None,'row_index':None,'article':None,
                'program_id':program,'plan_version':version,'language':language}

    def page(self,program,version,language,offset=0,limit=20,year=None):
        if not 0<=offset or not 1<=limit<=50 or language not in ('ar','en'):raise ValueError('Invalid pagination/language')
        key=(program,version,language)
        if key not in self.expected:raise KeyError(key)
        rows=sorted(self.rows.get(key,{}).values(),key=lambda r:(r['table_index'] or 0,r['row_index'] or 0,r['course_code']))
        grouping=bool(rows) and all(r['year'] is not None for r in rows)
        if year is not None and not grouping:raise ValueError('year_grouping_unavailable')
        if year is not None:rows=[r for r in rows if r['year']==year]
        total=len(rows)
        return {'program_id':program,'plan_version':version,'language':language,'total':total,'offset':offset,'limit':limit,
            'next_offset':offset+limit if offset+limit<total else None,'complete_indexed_coverage':len(self.rows.get(key,{}))==len(self.expected[key]),
            'year_grouping_verified':grouping,'coverage':'verified indexed plan rows; electives are included, not all mandatory',
            'courses':rows[offset:offset+limit]}

    def ask(self,question,program,version,language):
        service=self.services.get((program,version,language))
        return service.ask(question,language=language) if service else None
