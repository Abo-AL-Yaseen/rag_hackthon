import importlib.metadata
import socket
import pytest

from dotenv import dotenv_values
from fastapi import FastAPI
from fastapi.testclient import TestClient
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def test_fastapi_asgi_smoke():
    app = FastAPI()
    @app.get('/health')
    def health():
        return {'status':'ok','mode':'synthetic-preparation'}
    with TestClient(app) as client:
        response = client.get('/health')
        assert response.status_code == 200
        assert response.json()['mode'] == 'synthetic-preparation'


def test_dotenv_and_numeric_stack(tmp_path):
    path = tmp_path/'fixture.env'
    path.write_text('EMBEDDING_DEVICE=cpu\nOPENROUTER_API_KEY=\n')
    assert dotenv_values(path)['EMBEDDING_DEVICE'] == 'cpu'
    assert dotenv_values(path)['OPENROUTER_API_KEY'] == ''
    vectors = np.array([[1.,0.],[0.,1.]])
    assert np.allclose(cosine_similarity(vectors),np.eye(2))


def test_no_gpu_packages_installed():
    names = {d.metadata['Name'].lower() for d in importlib.metadata.distributions()}
    assert not any(n.startswith('nvidia-') or n in {'triton','torchvision','torchaudio'} for n in names)


def test_external_network_is_blocked():
    with socket.socket() as sock, pytest.raises(AssertionError,match='External network'):
        sock.connect(('198.51.100.1',443))
