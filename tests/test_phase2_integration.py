import json
from pathlib import Path

import pytest

from rag_hackathon.generation.providers import DeterministicMockProvider
from rag_hackathon.retrieval.dense import DenseRetriever
from rag_hackathon.service import RAGService


@pytest.mark.integration
def test_cpu_retrieval_to_grounded_mock_contract(encoder,chunks,tmp_path):
    root=Path(__file__).resolve().parents[1]
    data=json.loads((root/'data/sample/phase2_mock_rules.json').read_text(encoding='utf-8'))
    index=DenseRetriever(chunks,encoder,tmp_path,create=True)
    try:
        service=RAGService(index,DeterministicMockProvider(data['rules']))
        ar=service.ask('كم يوماً يمكن استعارة الكتب؟',language='ar')
        en=service.ask('How do I recover access after forgetting my password?',language='en')
        assert ar.status==en.status=='answered'
        assert ar.sources[0].document_id=='library' and ar.sources[0].page_number==1
        assert en.sources[0].document_id=='support' and en.sources[0].page_number==1
        assert service.ask('Why does the library allow borrowing for thirty days?').reason=='false_assumption'
        assert service.ask('Unregistered question despite dense neighbors').status=='insufficient_evidence'
    finally:
        index.close()
