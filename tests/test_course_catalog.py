import pytest
from types import SimpleNamespace

from rag_hackathon.course_catalog import CourseCatalog
from rag_hackathon.faculty_runtime import FacultyRuntime


def records(count=63):
    docs=[]
    for program in ('computer','civil'):
        for i in range(count):
            for language in ('ar','en'):
                code=str(10000000+i);credits=3 if program=='computer' else 2
                quote=f'رمز المساق: {code}؛ اسم المساق: مساق {i}؛ الساعات المعتمدة: {credits}؛ المتطلبات السابقة: غير مذكور.' if language=='ar' else f'Course Code: {code}; Course Name: Course {i}; Credit Hours: {credits}; Prerequests: Not listed.'
                docs.append({'document_id':f'{program}_{i}_{language}','kind':'course','scope':'program','program_id':program,'plan_version':'2021-1','course_code':code,'language':language,'reference_quote':quote,'retrieval_enabled':True,'table_index':2,'row_index':i+1,'source_url':'https://www.najah.edu/plan','program_name_ar':'هندسة الحاسوب' if program=='computer' else 'الهندسة المدنية','program_name_en':'Computer Engineering' if program=='computer' else 'Civil Engineering'})
    return docs


def test_complete_pagination_and_program_language_isolation():
    catalog=CourseCatalog(records(),[])
    all_rows=[];offset=0
    while True:
        page=catalog.page('computer','2021-1','en',offset,20);all_rows.extend(page['courses'])
        if page['next_offset'] is None:break
        offset=page['next_offset']
    assert len(all_rows)==63 and len({r['course_code'] for r in all_rows})==63
    assert all(r['credit_hours']==3 and r['document_id'].startswith('computer_') for r in all_rows)
    assert catalog.page('civil','2021-1','ar')['courses'][0]['credit_hours']==2
    assert page['complete_indexed_coverage'] and not page['year_grouping_verified']
    with pytest.raises(ValueError,match='year_grouping'):catalog.page('computer','2021-1','ar',year=1)
    with pytest.raises(KeyError):catalog.page('computer','2099-1','ar')


def test_list_questions_clarify_actual_versions_and_no_inferred_year():
    docs=records(2)
    index=SimpleNamespace(for_program=lambda *a,**k:None,for_regulations=lambda:None)
    runtime=FacultyRuntime(index,docs)
    result=runtime.ask('اعطيني مواد هندسة الحاسوب',language='ar')
    assert result.reason=='ambiguous' and '2021-1' in result.answer and not result.sources
    assert runtime.ask('اعطيني مواد تخصصي',language='ar').reason=='ambiguous'
    assert runtime.ask('شو مواد السنة الأولى هندسة الحاسوب؟',language='ar',program_id='computer',plan_version='2021-1').reason=='missing_evidence'
    en=runtime.ask('اعطيني مواد هندسة الحاسوب',language='en',program_id='computer',plan_version='2021-1')
    ar=runtime.ask('List all Computer Engineering courses.',language='ar',program_id='computer',plan_version='2021-1')
    assert en.status=='answered' and 'Verified course entries' in en.answer
    assert ar.status=='answered' and 'المساقات الموثقة' in ar.answer
