"""Citable in-memory view of verified runtime metadata, explicitly not a PDF.

Counts programs once across plan versions. No university-wide completeness claim,
question fixtures, translations, embedding writes or remote generation.
"""
from types import SimpleNamespace

from .schema import Chunk, Hit
from .service import RAGService, RAGPolicy
from .generation.academic_extractive import LocalAcademicEvidenceProvider


class RuntimeCatalog:
    def __init__(self, programs, documents):
        grouped={}
        for p in programs:
            row=grouped.setdefault(p['program_id'],dict(p))
            for key in ('name_ar','name_en'):
                if not row.get(key) and p.get(key):row[key]=p[key]
        self.locators={};self.services={}
        refs={}
        for doc in documents:
            if doc.get('scope')=='program' and doc.get('source_url'):
                key=(doc['program_id'],doc['plan_version'],doc['source_url'])
                refs[key]={'program_id':doc['program_id'],'plan_version':doc['plan_version'],
                           'source_url':doc['source_url'],'document_title':doc.get('document_title')}
        for language in ('ar','en'):
            names=[grouped[key].get('name_'+language) for key in sorted(grouped)]
            if not names or any(not n for n in names):continue
            heading=(f'البرامج الهندسية المتوفرة حاليًا في النظام: {len(grouped)}.' if language=='ar' else
                     f'Engineering programs currently available in this system: {len(grouped)}.')
            text=heading+'\n'+'\n'.join(f'{i}. {name}' for i,name in enumerate(names,1))
            ident='runtime_catalog_'+language
            chunk=Chunk(ident,ident,'verified_runtime_program_metadata',1,text,0,len(text),'runtime-catalog-v1')
            retriever=SimpleNamespace(search=lambda q,k,h=Hit(chunk,1.0):[h])
            self.services[language]=RAGService(retriever,LocalAcademicEvidenceProvider(),policy=RAGPolicy(top_k=1))
            self.locators[ident]={'source_type':'runtime_catalog','source_url':None,
                'document_title':'فهرس برامج النظام — بيانات موثقة، ليس ملف PDF' if language=='ar' else 'Verified runtime program catalog — metadata, not a PDF',
                'physical_pdf_page':None,'engine_page_number':1,'table_index':None,'row_index':None,
                'article':None,'program_id':None,'plan_version':None,'official_plan_sources':list(refs.values())}

    def ask(self, question, language):
        service=self.services.get(language)
        return service.ask(question,language=language) if service else None
