"""Offline synthetic drafts; no prediction of what a real provider will select."""
from dataclasses import replace
import json
from pathlib import Path

import pytest

from rag_hackathon.diagnostics import LocalDiagnostics, sanitized_raw_draft
from rag_hackathon.generation.contracts import ProviderResult,GenerationRequest,RAGResponse
from rag_hackathon.generation.prompts import messages_for
from rag_hackathon.generation.selections import candidate_spans
from rag_hackathon.schema import Chunk,Hit
from rag_hackathon.service import RAGService,RAGPolicy
from test_grounded_service import FixedRetriever,FixedProvider,hit,draft

ROOT=Path(__file__).resolve().parents[1]
SMOKE=json.loads((ROOT/'docs/evidence/groq_live_smoke_results.json').read_text(encoding='utf-8'))
AR_HIT=SMOKE['tests'][0]['receipt']['evidence_sent'][0]
AR_TEXT=AR_HIT['text'].split('. ')[0]+'.'


def original_hit():
    item=AR_HIT.copy()
    score=item.pop('score')
    return Hit(Chunk(**item),score)


class SelectFirst:
    is_mock=True
    def generate(self,request):
        ident=next(iter(candidate_spans(request.evidence)))
        return ProviderResult(json.dumps({'status':'answered','reason':'supported','selection_ids':[ident]}))


@pytest.mark.parametrize('question',['كم يوماً يمكن استعارة الكتب؟','قديش بقدر أخلي الكتب المستعارة معي؟',
                                    'هل مدة إعارة الكتب ١٢ يوماً؟','هل مدة إعارة الكتب 12 يوماً؟'])
def test_arabic_paraphrases_and_digit_queries_return_original_quote(question):
    response=RAGService(FixedRetriever([original_hit()]),SelectFirst()).ask(question,language='ar')
    assert response.status=='answered' and response.answer==AR_TEXT+' [S1]'
    assert response.sources[0].chunk_id==AR_HIT['chunk_id']
    assert response.sources[0].document_name=='synthetic_library.json' and response.sources[0].page_number==1
    assert response.validation.support_check=='exact_quote'


@pytest.mark.parametrize('number',['اثني عشر','١٢','12','۱۲'])
def test_number_styles_in_source_are_preserved_never_normalized(number):
    text='مدة الإعارة '+number+' يوماً.'
    response=RAGService(FixedRetriever([hit(text)]),SelectFirst()).ask('كم مدة الإعارة؟',language='ar')
    assert response.status=='answered' and response.claims[0].text==text


@pytest.mark.parametrize('changed',['يمكن استعارة الكتب لمدة اثني عشر يوماً.','مدة الإعارة 12 يوماً.',
                                   'مدة الإعارة ١٢ يوماً.','مدة الإعارة ثلاثون يوماً.'])
def test_legacy_paraphrases_and_changed_facts_remain_rejected(changed):
    response=RAGService(FixedRetriever([original_hit()]),FixedProvider(
        draft(text=changed,ident=AR_HIT['chunk_id'],excerpt=AR_TEXT))).ask('مدة الإعارة؟',language='ar')
    assert response.status=='insufficient_evidence' and response.reason=='unsupported_claim'
    assert not response.sources and changed not in response.answer


def test_selection_protocol_cannot_add_answer_text_or_fabricate_a_source():
    for content in [
        {'status':'answered','reason':'supported','selection_ids':['invented']},
        {'status':'answered','reason':'supported','selection_ids':[], 'answer':'الإعارة ثلاثون يوماً.'},
        {'status':'answered','reason':'supported','selection_ids':[], 'claims':[]},
        {'status':'answered','reason':'supported','selection_ids':[]}]:
        response=RAGService(FixedRetriever([original_hit()]),FixedProvider(json.dumps(content))).ask('كم يوماً؟',language='ar')
        assert response.status=='error' and not response.sources


def test_stale_selection_from_different_text_cannot_be_reused():
    ident=next(iter(candidate_spans([hit('مدة الإعارة ١٢ يوماً.')])))
    response=RAGService(FixedRetriever([hit('مدة الإعارة ٣٠ يوماً.')]),FixedProvider(json.dumps({
        'status':'answered','reason':'supported','selection_ids':[ident]}))).ask('مدة الإعارة؟',language='ar')
    assert response.reason=='invalid_citation'


@pytest.mark.parametrize('reason',['missing_evidence','out_of_scope','false_assumption','ambiguous','conflicting_sources'])
def test_selection_model_declared_refusals_remain_refusals(reason):
    response=RAGService(FixedRetriever([original_hit()]),FixedProvider(json.dumps({
        'status':'insufficient_evidence','reason':reason,'selection_ids':[]}))).ask('سؤال بلا إجابة مدعومة',language='ar')
    assert response.status=='insufficient_evidence' and response.reason==reason
    assert response.sources==response.claims==[]


def test_contradictory_versions_are_not_sent_to_provider():
    provider=SelectFirst()
    def unexpected(_): pytest.fail('Unresolved versions must refuse before generation')
    provider.generate=unexpected
    response=RAGService(FixedRetriever([hit('مدة الإعارة ١٢ يوماً.',version='v1'),
        hit('مدة الإعارة ٣٠ يوماً.',ident='new',version='v2')]),provider).ask('كم يوماً؟',language='ar')
    assert response.reason=='conflicting_sources' and not response.sources


def test_filtered_version_ids_cannot_be_cited():
    old,new=hit('مدة الإعارة ١٢ يوماً.',version='v1'),hit('مدة الإعارة ٣٠ يوماً.',ident='new',version='v2')
    old_id=next(iter(candidate_spans([old])))
    provider=FixedProvider(json.dumps({'status':'answered','reason':'supported','selection_ids':[old_id]}))
    response=RAGService(FixedRetriever([old,new]),provider,policy=RAGPolicy(current_versions={'library':'v2'})).ask('كم يوماً؟',language='ar')
    assert response.reason=='invalid_citation'


def test_candidate_ids_are_stable_exact_and_preserve_decimals_negation():
    source=hit('لا تزيد المدة عن 12.5 يوماً. A second sentence.')
    first=candidate_spans([source])
    assert first==candidate_spans([source])
    assert next(iter(first.values())).excerpt=='لا تزيد المدة عن 12.5 يوماً.'
    assert all(s.excerpt==source.chunk.text[s.start:s.end] for s in first.values())
    payload=json.loads(messages_for(GenerationRequest('مدة؟','ar',(source,)))[1]['content'])
    assert payload['output_schema']['properties'].get('selection_ids')
    assert payload['quote_candidates'][0]['excerpt']=='لا تزيد المدة عن 12.5 يوماً.'


def test_diagnostic_distinguishes_two_identical_public_reason_codes(tmp_path):
    sink=LocalDiagnostics(tmp_path)
    provider=FixedProvider(draft(text='مدة الإعارة 12 يوماً.',ident=AR_HIT['chunk_id'],excerpt=AR_TEXT))
    response=RAGService(FixedRetriever([original_hit()]),provider,diagnostics=sink).ask('كم يوماً؟',language='ar')
    failure=json.loads(sink.last_path.read_text(encoding='utf-8'))
    assert response.reason=='unsupported_claim'
    assert failure['stage']=='claim_validation' and failure['detail']=='claim_excerpt_mismatch'
    provider=FixedProvider(json.dumps({'status':'insufficient_evidence','reason':'unsupported_claim','claims':[]}))
    response=RAGService(FixedRetriever([original_hit()]),provider,diagnostics=sink).ask('كم يوماً؟',language='ar')
    declared=json.loads(sink.last_path.read_text(encoding='utf-8'))
    assert response.reason=='unsupported_claim' and declared['stage']=='provider_refusal'
    assert failure['retrieved_source_ids']==declared['supplied_source_ids']==[AR_HIT['chunk_id']]


def test_diagnostics_retain_structure_but_no_credentials_question_or_document_text(tmp_path):
    secret='fixture-api-credential-never-persist'
    sensitive='Private patient name and medical information'
    source=hit(sensitive,ident='private-patient-name')
    raw=json.dumps({'status':'answered','reason':'supported','claims':[{'text':sensitive,
        'evidence':[{'chunk_id':source.chunk.chunk_id,'excerpt':sensitive}]}],
        'api_key':secret,secret:secret,'nested':{'authorization':secret}})
    sink=LocalDiagnostics(tmp_path)
    response=RAGService(FixedRetriever([source]),FixedProvider(raw),diagnostics=sink).ask('private question '+secret)
    assert response.reason=='malformed_response'
    data=sink.last_path.read_text(encoding='utf-8')
    assert secret not in data and sensitive not in data and 'private-patient-name' not in data and 'private question' not in data
    assert 'redacted' in data and 'withheld_unknown_fields' in data


def test_digit_script_equivalence_is_diagnostic_only(tmp_path):
    a='مدة الإعارة 12 يوماً.'
    b='مدة الإعارة ١٢ يوماً.'
    raw=draft(text=a,excerpt=b)
    result=sanitized_raw_draft(raw,[hit(b)])
    assert result['comparisons'][0]['digit_script_equal'] and not result['comparisons'][0]['exact_equal']
    response=RAGService(FixedRetriever([hit(b)]),FixedProvider(raw)).ask('مدة؟',language='ar')
    assert response.reason=='unsupported_claim'


def test_successful_private_answer_text_is_also_withheld_from_diagnostics(tmp_path):
    private_text='Confidential patient record not permitted in logs.'
    sink=LocalDiagnostics(tmp_path)
    response=RAGService(FixedRetriever([hit(private_text)]),SelectFirst(),diagnostics=sink).ask('authorized question')
    assert response.status=='answered' and private_text in response.answer
    record=sink.last_path.read_text(encoding='utf-8')
    assert private_text not in record and 'authorized question' not in record
    assert json.loads(record)['stage']=='accepted'


@pytest.mark.parametrize('raw',['not JSON','{"key":"fixture-secret"','x'*65537],ids=['malformed','truncated','oversized'])
def test_bad_or_oversized_raw_drafts_are_withheld(raw):
    sanitized=json.dumps(sanitized_raw_draft(raw,[]))
    assert 'fixture-secret' not in sanitized and 'not JSON' not in sanitized
    assert 'withheld' in sanitized


def test_diagnostics_failure_does_not_change_validated_answer():
    class Broken:
        def record(self,*args,**kwargs): raise OSError('private local path')
    engine=RAGService(FixedRetriever([original_hit()]),SelectFirst(),diagnostics=Broken())
    response=engine.ask('مدة الإعارة؟',language='ar')
    assert response.status=='answered' and engine.diagnostic_failures==1
    assert 'private local path' not in response.model_dump_json()
    assert RAGResponse.model_json_schema()==json.loads((ROOT/'docs/rag_response.schema.json').read_text())
