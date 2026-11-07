import json
from types import SimpleNamespace

import pytest

from rag_hackathon.academic_decisions import intent, program_mentions
from rag_hackathon.faculty_runtime import FacultyRuntime
from rag_hackathon.generation.academic_extractive import LocalAcademicEvidenceProvider
from rag_hackathon.generation.contracts import GenerationRequest
from rag_hackathon.schema import Chunk, Hit


@pytest.mark.parametrize('q,expected',[
 ('قديش ساعات مساق ١٢٣٤٥٦٧٨؟','course'),('Which prerequisites are required?','course'),
 ('لو تغيبت عن المختبر زيادة، شو بصير؟','attendance'),('What happens if I miss classes?','attendance'),
 ('بدي انسحب من مادة وبسأل عن المصاري','withdrawal'),('When can I add a course?','add_drop'),
 ('How many total credits to graduate?','graduation'),('شو بصير مع الإنذار؟','warning'),
 ('متى موعد الامتحان؟','schedule'),('Please write a poem','out_of_scope')])
def test_intent_paraphrases(q,expected):
    assert intent(q)==expected


def test_program_resolution_uses_verified_names_and_longest_match():
    programs=[{'program_id':'chemical','name_en':'Chemical Engineering'},
              {'program_id':'pharma','name_en':'Chemical Engineering Pharmaceutical Engineering'}]
    assert program_mentions('Chemical Engineering Pharmaceutical Engineering plan',programs)=={'pharma'}
    assert not program_mentions('Computer Science',programs)


@pytest.mark.parametrize('question,key',[
 ('كم ساعة مساق 12345678؟','scope'),('What prerequisites does course 12345678 have?','scope'),
 ('إمتى بنزل علي إنذار؟','warning'),('متى امتحان الأسبوع القادم؟','schedule'),('اكتب قصيدة','out_of_scope')])
def test_early_decisions_have_no_citations_or_provider_call(question,key):
    def forbidden(*args,**kwargs):pytest.fail('Context decisions must not retrieve or generate')
    index=SimpleNamespace(for_regulations=lambda:SimpleNamespace(search=forbidden))
    runtime=FacultyRuntime(index,[],SimpleNamespace(generate=forbidden,is_mock=True))
    response=runtime.ask(question,language='ar')
    assert response.status=='insufficient_evidence' and not response.sources and not response.claims
    assert response.reason==('missing_evidence' if key=='schedule' else 'out_of_scope' if key=='out_of_scope' else 'ambiguous')


def hit(ident,text):
    return Hit(Chunk(ident,ident,'source',1,text,0,len(text),'verified'),.9)


def test_extractive_uses_actual_unseen_row_values_without_question_fixtures():
    text='Verified program | plan 2099-7\nCourse Code: 12345678; Course Name: Novel course; Credit Hours: 7; Prerequests: 87654321.'
    provider=LocalAcademicEvidenceProvider()
    result=json.loads(provider.generate(GenerationRequest('Tell me the credit hours for course 12345678','en',(hit('unseen',text),))).content)
    assert result['status']=='answered' and result['claims'][0]['text']==text.split('\n')[1]
    assert '7' in result['claims'][0]['text']
    # A different code or language cannot borrow that row.
    assert json.loads(provider.generate(GenerationRequest('Credits for course 99999999','en',(hit('unseen',text),))).content)['status']=='insufficient_evidence'
    assert json.loads(provider.generate(GenerationRequest('كم ساعة مساق 12345678؟','ar',(hit('unseen',text),))).content)['status']=='insufficient_evidence'


def test_incomplete_policy_does_not_become_complete_answer():
    row=hit('not-a-hardcoded-id','Official | الحق المالي عند الانسحاب\nA verified financial clause.')
    result=json.loads(LocalAcademicEvidenceProvider().generate(GenerationRequest('When can I withdraw and keep financial rights?','en',(row,))).content)
    assert result['status']=='insufficient_evidence'
