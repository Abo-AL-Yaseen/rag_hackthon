import json
import os
import socket
from pathlib import Path

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

import pytest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='session', autouse=True)
def no_network_in_tests():
    original_connect = socket.socket.connect
    def guarded_connect(sock, address):
        # Windows asyncio uses a loopback socket pair for its internal wakeup pipe.
        if isinstance(address, tuple) and address[0] in ('127.0.0.1', '::1'):
            return original_connect(sock, address)
        raise AssertionError('External network is disabled in automated tests')
    with patch('socket.socket.connect', new=guarded_connect):
        yield


@pytest.fixture(scope='session')
def encoder():
    from rag_hackathon.retrieval.dense import E5Encoder
    manifest = json.loads((ROOT/'docs/evidence/model_manifest.json').read_text())
    return E5Encoder(ROOT/'models/multilingual-e5-small', manifest['revision'])


@pytest.fixture(scope='session')
def chunks(encoder):
    from rag_hackathon.ingestion import load_pages, chunk_pages
    return chunk_pages(load_pages(ROOT/'data/sample/synthetic_pages.json'), encoder.tokenizer)
