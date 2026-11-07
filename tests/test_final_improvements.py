from types import SimpleNamespace

import numpy as np
import pytest
from qdrant_client import QdrantClient, models

from rag_hackathon.faculty_runtime import FacultyRuntime
from rag_hackathon.generation.academic_extractive import LocalAcademicEvidenceProvider
from rag_hackathon.retrieval.scoped import ScopedIndex
from rag_hackathon.runtime_catalog import RuntimeCatalog
from rag_hackathon.schema import Chunk


@pytest.mark.parametrize('language',['ar','en'])
def test_catalog_counts_programs_not_versions_and_quotes_metadata(language):
    programs=[{'program_id':'x','plan_version':v,'name_ar':'تخصص موثق','name_en':'Verified program'} for v in ('2020-1','2025-1')]
    programs.append({'program_id':'y','plan_version':'2025-1','name_ar':'تخصص آخر','name_en':'Another program'})
    catalog=RuntimeCatalog(programs,[])
    q='كم تخصص موجود؟' if language=='ar' else 'How many engineering programs are listed?'
    result=catalog.ask(q,language)
    assert result.status=='answered' and ': 2.' in result.answer
    assert result.answer.count('1. ')==1 and result.answer.count('2. ')==1
    assert result.validation.support_check=='exact_quote'
    locator=catalog.locators[result.sources[0].document_id]
    assert locator['source_type']=='runtime_catalog' and locator['physical_pdf_page'] is None
    assert locator['source_url'] is None  # Never forge an official directory URL.


@pytest.mark.parametrize('question',['لو زادت غياباتي شو بصير؟','كم غياب بقدر أغيب؟','What happens if I miss too many classes?'])
@pytest.mark.parametrize('selected',[False,True])
def test_attendance_prefilter_covers_conditions_in_either_scope(question,selected):
    client=QdrantClient(':memory:');client.create_collection('test',vectors_config=models.VectorParams(size=2,distance=models.Distance.COSINE))
    docs=[]
    for i,article in enumerate(('10/ب','10/ج','10/د','10/أ','14/ج'),1):
        chunk=Chunk(str(i),str(i),'synthetic',1,'Synthetic evidence '+article,0,20,'v1')
        client.upsert('test',points=[models.PointStruct(id=i,vector=[0.,1.] if i<4 else [1.,0.],payload=chunk.payload())])
        docs.append({'document_id':str(i),'scope':'regulations','program_id':None,'plan_version':None,'article':article})
    docs.append({'document_id':'foreign','scope':'program','program_id':'foreign','plan_version':'2025-1'})
    owner=SimpleNamespace(client=client,collection='test',encoder=SimpleNamespace(queries=lambda q:np.array([[1.,0.]])),close=client.close)
    index=ScopedIndex(owner,docs)
    try:
        view=index.for_program('foreign','2025-1') if selected else index.for_regulations()
        hits=view.search(question,5)
        assert {'1','2','3'} <= {h.chunk.document_id for h in hits}
        assert all(h.chunk.document_id in ('1','2','3','4') for h in hits)
    finally:index.close()


@pytest.mark.parametrize('selected_language',['ar','en'])
def test_no_generation_translation_when_policy_language_unavailable(selected_language):
    # Runtime localizes a missing-language result; original Arabic evidence is never translated.
    from rag_hackathon.schema import Hit
    text='دليل | حد الغياب دون عذر\nاقتباس عربي موثق.'
    row=Chunk('a','a','source',1,text,0,len(text),'v1')
    docs=[{'document_id':'a','scope':'regulations','program_id':None,'plan_version':None,'language':'ar'}]
    view=SimpleNamespace(search=lambda q,k:[Hit(row,.9)])
    index=SimpleNamespace(for_regulations=lambda:view)
    runtime=FacultyRuntime(index,docs,LocalAcademicEvidenceProvider())
    response=runtime.ask('What happens with excessive absence?',language=selected_language)
    assert response.language==selected_language and not response.sources
    if selected_language=='en':assert 'not available in English' in response.answer
