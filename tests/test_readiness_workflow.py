import json
from pathlib import Path

import fitz
import pytest

from rag_hackathon.ingestion import load_pages
from rag_hackathon.workspace import read_inputs,ingest,open_index
from examples.invoke_local_engine import invoke

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/sample/readiness'


def test_real_rtl_pdf_preserves_logical_word_order():
    case=json.loads((DATA/'cases.json').read_text(encoding='utf-8'))['cases'][0]
    path=DATA/'inputs'/case['file']
    with fitz.open(path) as pdf:
        assert case['excerpt'] not in pdf[0].get_text(sort=True)
    assert case['excerpt'] in load_pages(path)[0].text


@pytest.mark.integration
def test_new_pdf_full_workflow_and_fresh_store_isolation(encoder,tmp_path):
    cases=json.loads((DATA/'cases.json').read_text(encoding='utf-8'))['cases']
    rules=json.loads((DATA/'mock_rules.json').read_text(encoding='utf-8'))['rules']
    first=tmp_path/'new-pdf-store'
    manifest=ingest(DATA/'inputs',first,encoder=encoder)
    assert manifest['pages']==manifest['chunks']==4
    index=open_index(first,encoder=encoder)
    try:
        for case in cases:
            top=index.search(case['question'],1)[0]
            assert top.chunk.source==case['file'] and top.chunk.page==case['page']
            response=invoke(index,{'question':case['question'],'language':case['language']},rules)
            assert response['status']=='answered' and response['mode']=='mock'
            assert response['sources'][0]['document_name']==case['file']
            assert response['sources'][0]['page_number']==case['page']
        assert invoke(index,{'question':'unknown unsupported question'})['status']=='insufficient_evidence'
    finally: index.close()
    with pytest.raises(ValueError,match='Fresh index'): ingest(DATA/'inputs',first,encoder=encoder)
    isolated=tmp_path/'new-real-dataset-simulation'
    ingest(DATA/'inputs/readiness_english.pdf',isolated,encoder=encoder)
    index=open_index(isolated,encoder=encoder)
    try:
        points,_=index.client.scroll(index.collection,limit=100,with_payload=True)
        assert len(points)==2
        assert {p.payload['document_id'] for p in points}=={'readiness_english'}
    finally: index.close()
    (first/'chunks.json').write_text('[]')
    with pytest.raises(ValueError,match='changed dataset'): open_index(first,encoder=encoder)


def test_duplicate_document_ids_across_files_are_rejected(tmp_path):
    for folder in ('a','b'):
        dest=tmp_path/folder;dest.mkdir()
        (dest/'same.pdf').write_bytes((DATA/'inputs/readiness_english.pdf').read_bytes())
    with pytest.raises(ValueError,match='Duplicate document ID'): read_inputs(tmp_path)


def test_bad_unicode_pdf_is_blocked_before_indexing(tmp_path):
    path=tmp_path/'broken.pdf'
    with fitz.open() as doc:
        page=doc.new_page()
        page.insert_htmlbox(fitz.Rect(20,20,500,300),'<p>هذه تجربة عربية تحتاج مراجعة الترميز.</p>')
        doc.save(path)
    with pytest.raises(ValueError,match='encoding needs manual review'): read_inputs(path)


def test_backend_example_rejects_untrusted_provider_fields():
    with pytest.raises(ValueError,match='only question and language'):
        invoke(None,{'question':'q','api_key':'forbidden'})
