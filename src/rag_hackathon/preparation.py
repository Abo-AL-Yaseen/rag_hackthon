"""Explicitly synthetic factory for offline examples/evaluation, not production."""
import hashlib
import json
from pathlib import Path

from .generation.providers import DeterministicMockProvider
from .service import RAGPolicy, RAGService


def build_preparation_service(root, *, index_path=None):
    from .ingestion import load_pages, chunk_pages
    from .retrieval.dense import DenseRetriever, E5Encoder
    root = Path(root)
    manifest = json.loads((root/'docs/evidence/model_manifest.json').read_text())
    model = root/'models/multilingual-e5-small'
    for entry in manifest['files']:
        with (model/entry['name']).open('rb') as stream:
            if hashlib.file_digest(stream,'sha256').hexdigest() != entry['sha256']:
                raise ValueError('Cached model failed hash validation')
    encoder = E5Encoder(model,manifest['revision'])
    pages = load_pages(root/'data/sample/synthetic_pages.json')
    for path in sorted((root/'data/sample/phase2_documents').glob('*.json')):
        pages.extend(load_pages(path))
    chunks = chunk_pages(pages,encoder.tokenizer)
    index_path = Path(index_path) if index_path else root/'data/index/phase2'
    index = DenseRetriever(chunks,encoder,index_path,
                           create=not (index_path/'retrieval_manifest.json').exists())
    try:
        data = json.loads((root/'data/sample/phase2_mock_rules.json').read_text(encoding='utf-8'))
        if not data.get('synthetic') or not data.get('scripted'):
            raise ValueError('Expected explicitly scripted synthetic mock rules')
        provider = DeterministicMockProvider(data['rules'])
        service = RAGService(index,provider,policy=RAGPolicy(current_versions={'retired_desk':'2026'}))
        return service,index,chunks
    except Exception:
        index.close()
        raise
