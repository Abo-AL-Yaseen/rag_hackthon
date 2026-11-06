from dataclasses import replace

from fastapi.testclient import TestClient
import pytest

from examples.backend_integration import make_app
from rag_hackathon.rag_evaluation import audit_sources, reference_scores
from rag_hackathon.generation.contracts import RAGResponse
from rag_hackathon.service import RAGService
from test_grounded_service import FixedProvider,FixedRetriever,draft,hit


def test_reference_diagnostics_hand_calculated():
    assert reference_scores('one two',['one three'])=={'normalized_exact_match':0.0,'token_f1':0.5}
    assert reference_scores('Two books.',['two books'])=={'normalized_exact_match':1.0,'token_f1':1.0}
    assert reference_scores('كِتاب',['كتاب'])['normalized_exact_match']==1
    assert reference_scores('',['a'])['token_f1']==0
    with pytest.raises(ValueError):
        reference_scores('answer',[])


def test_citation_audit_not_semantic_score():
    hits=[hit()]
    response=RAGService(FixedRetriever(hits),FixedProvider(draft())).ask('loan?')
    good=audit_sources(response,hits)
    assert good['source_reference_accuracy']==1 and good['semantic_faithfulness'] is None
    tampered=response.model_copy(update={'sources':[response.sources[0].model_copy(update={'page_number':2})]})
    assert audit_sources(tampered,hits)['source_reference_accuracy']==0


def test_backend_example_contract_and_input_validation():
    service=RAGService(FixedRetriever([hit()]),FixedProvider(draft()))
    with TestClient(make_app(service)) as client:
        response=client.post('/rag/answer',json={'question':'loan?','language':'en'})
        assert response.status_code==200
        parsed=RAGResponse.model_validate(response.json())
        assert parsed.status=='answered' and parsed.sources[0].page_number==1
        assert client.post('/rag/answer',json={'question':'loan?','api_key':'forbidden'}).status_code==422
        assert client.post('/rag/answer',json={'question':'loan?','language':'unsupported'}).status_code==422
