import json
from pathlib import Path

import fitz
import pytest

from rag_hackathon.ingestion import chunk_pages, load_pages
from rag_hackathon.schema import Page


def test_pdf_physical_pages_and_table_text(tmp_path):
    path = tmp_path/'synthetic.pdf'
    with fitz.open() as pdf:
        for text in ('SYNTHETIC: Library loan period is twelve days.',
                     'SYNTHETIC TABLE\nItem     Limit\nBooks    3\nDays     12'):
            pdf.new_page().insert_text((40,60), text)
        pdf.save(path)
    pages = load_pages(path)
    assert [p.page for p in pages] == [1,2]
    assert pages[1].source == 'synthetic.pdf' and 'Books' in pages[1].text and '12' in pages[1].text


def test_textless_pdf_is_reported(tmp_path):
    path = tmp_path/'scan.pdf'
    with fitz.open() as pdf:
        pdf.new_page()
        pdf.save(path)
    with pytest.raises(ValueError, match='OCR required'):
        load_pages(path)


def test_json_arabic_and_duplicate_identity(tmp_path):
    path = tmp_path/'pages.json'
    record = {'document_id':'x','source':'invented','page':1,'text':'هذه بيانات اصطناعية باللغة العربية.'}
    path.write_text(json.dumps({'pages':[record]}, ensure_ascii=False), encoding='utf-8')
    assert load_pages(path)[0].text == record['text']
    path.write_text(json.dumps({'pages':[record,record]}), encoding='utf-8')
    with pytest.raises(ValueError, match='Duplicate'):
        load_pages(path)


@pytest.mark.parametrize('page,text', [(0,'hello'),(1,''),(1,'   ')])
def test_invalid_page(page, text):
    with pytest.raises(ValueError):
        Page('x','x.pdf',page,text)


def test_every_named_synthetic_source_resolves():
    root = Path(__file__).resolve().parents[1]/'data/sample'
    pages = load_pages(root/'synthetic_pages.json')
    for expected in pages:
        actual = load_pages(root/'documents'/expected.source)
        assert expected in actual


@pytest.mark.integration
def test_token_chunking_offsets_stability_and_boundaries(encoder):
    text = ('هذه تجربة اصطناعية لاختبار تقطيع النص مع حفظ المصدر والصفحة. ' * 30)
    pages = [Page('x','sample',1,text),Page('x','sample',2,'Different page content.')]
    chunks = chunk_pages(pages, encoder.tokenizer, max_tokens=24, overlap=4)
    assert chunks == chunk_pages(pages, encoder.tokenizer, max_tokens=24, overlap=4)
    assert len(chunks) > 2 and len({c.chunk_id for c in chunks}) == len(chunks)
    for c in chunks:
        assert c.text == pages[c.page-1].text[c.start:c.end]
        assert len(encoder.tokenizer('passage: '+c.text)['input_ids']) <= 512
    assert chunks[1].start < chunks[0].end
    assert chunks[-1].page == 2
    with pytest.raises(ValueError):
        chunk_pages(pages, encoder.tokenizer, max_tokens=512)
    with pytest.raises(ValueError):
        chunk_pages(pages, encoder.tokenizer, max_tokens=24, overlap=24)
