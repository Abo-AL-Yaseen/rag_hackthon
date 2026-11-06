from dataclasses import replace

import numpy as np
import pytest
import torch

from rag_hackathon.citations import cite, validate_citation
from rag_hackathon.retrieval.bm25 import BM25Retriever, tokenize
from rag_hackathon.retrieval.dense import DenseRetriever


def test_arabic_tokenization():
    assert tokenize('إِعَادَة الـكتاب ABC_123') == ['اعادة','الكتاب','abc','123']


@pytest.mark.integration
def test_bilingual_embeddings_cpu_and_prefixes(encoder, monkeypatch):
    assert torch.version.cuda is None and not torch.cuda.is_available()
    assert '+cpu' in torch.__version__
    q = encoder.queries(['كيف أستعيد كلمة المرور؟','How do I borrow a book?'])
    p = encoder.passages(['استعادة كلمة المرور تتم في بوابة الدعم.', 'Books are borrowed from the library.'])
    assert q.shape == p.shape == (2,384)
    assert np.isfinite(q).all() and np.allclose(np.linalg.norm(q,axis=1),1,atol=1e-5)
    scores = q @ p.T
    assert scores[0,0] > scores[0,1] and scores[1,1] > scores[1,0]
    captured = []
    def encode(inputs, **kwargs):
        captured.extend(inputs)
        return np.zeros((len(inputs),384))
    monkeypatch.setattr(encoder.model,'encode',encode)
    encoder.queries(['سؤال'])
    encoder.passages(['نص'])
    assert captured == ['query: سؤال','passage: نص']


@pytest.mark.integration
def test_encoder_rejects_empty_and_truncation(encoder):
    with pytest.raises(ValueError):
        encoder.queries([''])
    with pytest.raises(ValueError, match='512'):
        encoder.passages(['hello ' * 1000])


@pytest.mark.integration
def test_benchmark_passages_stay_inside_encoder_budget(encoder):
    from scripts.evaluate_retrieval import benchmark_inputs
    texts = benchmark_inputs(encoder.tokenizer)
    sizes = [len(encoder.tokenizer('passage: '+t)['input_ids']) for t in texts]
    assert len(texts) == 8 and len(set(sizes)) == 4
    assert min(sizes) >= 32 and max(sizes) <= 512


@pytest.mark.integration
def test_dense_persistence_and_manifest_guard(chunks, encoder, tmp_path):
    index = DenseRetriever(chunks,encoder,tmp_path,create=True)
    first = index.search('كم مدة استعارة الكتب؟',1)
    index.close()
    assert first[0].chunk.document_id == 'library' and first[0].chunk.page == 1
    reopened = DenseRetriever(chunks,encoder,tmp_path)
    try:
        assert reopened.search('كم مدة استعارة الكتب؟',1)[0].chunk.chunk_id == first[0].chunk.chunk_id
    finally:
        reopened.close()
    changed = [replace(chunks[0],text='changed corpus'),*chunks[1:]]
    with pytest.raises(ValueError,match='incompatible'):
        DenseRetriever(changed,encoder,tmp_path)
    with pytest.raises(ValueError,match='already exists'):
        DenseRetriever(chunks,encoder,tmp_path,create=True)
    # Failed opens release the local file lock and do not destroy the valid collection.
    final = DenseRetriever(chunks,encoder,tmp_path)
    final.close()


@pytest.mark.integration
def test_bm25_relevant_passage_and_citations(chunks):
    index = BM25Retriever(chunks)
    hits = index.search('maximum support ticket attachment size',3)
    assert hits[0].chunk.document_id == 'support' and hits[0].chunk.page == 2
    citation = cite(hits[0],'ten megabytes')
    assert validate_citation(citation,hits)
    assert 'p. 2' in citation.label
    assert not validate_citation(replace(citation,page=999),hits)
    assert not validate_citation(replace(citation,chunk_id='fabricated'),hits)
    assert not validate_citation(replace(citation,quote='invented fact'),hits)
    with pytest.raises(ValueError):
        cite(hits[0],'invented fact')
    assert index.search('zzzzqwyx',3) == []
    with pytest.raises(ValueError):
        index.search('hello',0)
