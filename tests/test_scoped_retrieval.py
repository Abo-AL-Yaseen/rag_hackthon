"""Program/version isolation, including adversarial nearest foreign vectors."""
import json
import hashlib
from types import SimpleNamespace

import numpy as np
import pytest
from qdrant_client import QdrantClient, models

from rag_hackathon.schema import Chunk
from rag_hackathon.retrieval.scoped import ScopedIndex


@pytest.fixture
def scoped():
    client = QdrantClient(':memory:')
    client.create_collection('test', vectors_config=models.VectorParams(size=2,distance=models.Distance.COSINE))
    specs = [('civil_new','civil','2025-1',[0.7,0.3]),
             ('civil_old','civil','2018-1',[1.0,0.0]),
             ('computer_new','computer','2021-1',[1.0,0.0]),
             ('shared',None,None,[0.6,0.4]),
             ('conflicting_total','civil','2025-1',[1.0,0.0])]
    metadata=[]
    for number,(ident,program,version,vector) in enumerate(specs,1):
        chunk=Chunk(str(number),ident,'official.html',1,'Verified source row',0,19,version or 'handbook')
        client.upsert('test',points=[models.PointStruct(id=number,vector=vector,payload=chunk.payload())])
        metadata.append({'document_id':ident,'scope':'program' if program else 'regulations',
                         'program_id':program,'plan_version':version,
                         'course_code':'10871112' if ident in ('civil_new','civil_old','computer_new') else None,
                         'kind':'plan_summary' if ident=='conflicting_total' else 'course',
                         'withheld_reason':'graduation_conflict' if ident=='conflicting_total' else None,
                         'retrieval_enabled':ident!='conflicting_total'})
    owner=SimpleNamespace(client=client,collection='test',encoder=SimpleNamespace(queries=lambda q:np.array([[1.0,0.0]])),close=client.close)
    result=ScopedIndex(owner,metadata)
    yield result
    result.close()


def test_nearest_foreign_program_and_old_version_are_prefiltered(scoped):
    hits=scoped.for_program('civil','2025-1').search('same shared course code',2)
    assert {h.chunk.document_id for h in hits}=={'civil_new','shared'}


def test_explicit_old_plan_never_leaks_new_plan(scoped):
    hits=scoped.for_program('civil','2018-1').search('prerequisites',20)
    assert {h.chunk.document_id for h in hits}=={'civil_old','shared'}


def test_unselected_context_sees_only_shared_regulations(scoped):
    assert [h.chunk.document_id for h in scoped.for_regulations().search('computer graduation',20)]==['shared']


def test_conflicting_totals_are_withheld_even_for_selected_program(scoped):
    hits=scoped.for_program('civil','2025-1').search('graduation total',20)
    assert 'conflicting_total' not in {h.chunk.document_id for h in hits}


def test_explicit_matching_plan_precedence_is_opt_in_and_still_scoped(scoped):
    hits=scoped.for_program('civil','2025-1',prefer_matching_plan=True).search('graduation credits',20)
    assert {h.chunk.document_id for h in hits}=={'civil_new','shared','conflicting_total'}
    old=scoped.for_program('civil','2018-1',prefer_matching_plan=True).search('graduation credits',20)
    assert {h.chunk.document_id for h in old}=={'civil_old','shared'}


def test_selected_official_plan_summary_has_priority_for_graduation_credit_total(scoped):
    client=scoped._owner.client
    original=client.retrieve('test',ids=[5])[0]
    client.upsert('test',points=[models.PointStruct(id=5,vector=[0.0,1.0],payload=original.payload)])
    hits=scoped.for_program('civil','2025-1',prefer_matching_plan=True).search('كم مجموع ساعات التخرج؟',1)
    assert [h.chunk.document_id for h in hits]==['conflicting_total']


@pytest.mark.parametrize('code',['10871112','١٠٨٧١١١٢'])
def test_exact_course_identifier_beats_semantically_nearer_unrelated_policy(scoped,code):
    client=scoped._owner.client
    original=client.retrieve('test',ids=[1])[0]
    client.upsert('test',points=[models.PointStruct(id=1,vector=[0.0,1.0],payload=original.payload)])
    hits=scoped.for_program('civil','2025-1').search('كم ساعة مساق '+code,1)
    assert [h.chunk.document_id for h in hits]==['civil_new']


@pytest.mark.parametrize('question',['credits for 99999999','compare 10871112 and 99999999'])
def test_missing_course_identifier_never_falls_back_to_an_unrelated_course(scoped,question):
    assert scoped.for_program('civil','2025-1').search(question,5)==[]


@pytest.mark.parametrize('program,version',[('civil',None),(None,'2025-1'),('computer','2025-1'),('unknown','2021-1')])
def test_unknown_or_ambiguous_scope_fails_closed(scoped,program,version):
    with pytest.raises(ValueError,match='program/plan'):
        scoped.for_program(program,version)


def test_all_views_stop_after_owner_closes(scoped):
    view=scoped.for_program('civil','2025-1')
    scoped.close()
    with pytest.raises(RuntimeError,match='closed'):view.search('question')


def test_scope_manifest_cannot_be_rebound_to_another_snapshot(tmp_path):
    snapshot=b'[]'
    (tmp_path/'chunks.json').write_bytes(snapshot)
    (tmp_path/'scope_manifest.json').write_text(json.dumps({'format_version':1,'chunks_sha256':'wrong','documents':[]}))
    (tmp_path/'dataset_manifest.json').write_text('{}')
    with pytest.raises(ValueError,match='binding'):ScopedIndex.open(tmp_path)


def test_scope_manifest_must_classify_every_document(tmp_path):
    snapshot=json.dumps([{'document_id':'unclassified'}]).encode()
    (tmp_path/'chunks.json').write_bytes(snapshot)
    (tmp_path/'scope_manifest.json').write_text(json.dumps({'format_version':1,
        'chunks_sha256':hashlib.sha256(snapshot).hexdigest(),'documents':[]}))
    (tmp_path/'dataset_manifest.json').write_text(json.dumps({'scope_manifest_sha256':
        hashlib.sha256((tmp_path/'scope_manifest.json').read_bytes()).hexdigest()}))
    with pytest.raises(ValueError,match='cover every'):ScopedIndex.open(tmp_path)


def test_mixed_faculty_store_rejects_unscoped_open_before_model_loading(tmp_path):
    from rag_hackathon.workspace import open_index
    (tmp_path/'dataset_manifest.json').write_text(json.dumps({'requires_scoped_retrieval':True}))
    with pytest.raises(ValueError,match='ScopedIndex'):open_index(tmp_path)
