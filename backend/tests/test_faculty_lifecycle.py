from dataclasses import replace
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import BackendSettings
from backend.lifecycle import build_state


def settings(tmp_path):
    return BackendSettings(index_path=tmp_path/'index',catalog_path=tmp_path/'absent_catalog.json',
        mock_rules_path=None,cors_origins=('http://localhost:5173',),load_dotenv_file=None,
        host='127.0.0.1',port=8000,allow_paid_api_calls=False,allow_free_api_calls=False,llm_provider='mock')


@pytest.mark.parametrize('change',[{'allow_paid_api_calls':True},{'allow_free_api_calls':True},{'llm_provider':'groq'}])
def test_offline_startup_rejects_live_settings_before_open(tmp_path,monkeypatch,change):
    def forbidden(*args,**kwargs):pytest.fail('Unsafe settings must not open a runtime')
    monkeypatch.setattr('backend.lifecycle.FacultyRuntime.open',forbidden)
    state=build_state(replace(settings(tmp_path),**change))
    assert not state.rag_ready and state.startup_errors


def test_lifespan_owns_one_runtime_and_uses_runtime_catalog(tmp_path,monkeypatch):
    calls=[]
    class Runtime:
        service=object()
        def programs(self):return [{'program_id':'verified','plan_version':'2025-1','name_ar':'اسم موثق','name_en':'Verified'}]
        def close(self):calls.append('close')
        def source_locator(self,ident):
            if ident!='known':raise KeyError(ident)
            return {'source_url':'https://www.najah.edu/ar/','document_title':'Official'}
    def open_runtime(*args,**kwargs):calls.append('open');return Runtime()
    monkeypatch.setattr('backend.lifecycle.FacultyRuntime.open',open_runtime)
    with TestClient(create_app(settings(tmp_path))) as client:
        assert client.get('/health').json()['rag_ready']
        assert client.get('/api/programs').json()[0]['program_id']=='verified'
        assert client.get('/api/sources/known').json()['source_url'].startswith('https://www.najah.edu/')
        assert client.get('/api/sources/missing').status_code==404
        assert client.options('/api/chat',headers={'Origin':'http://localhost:5173',
            'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type'}).status_code==200
    assert calls==['open','close']


def test_source_resolver_rejects_nonofficial_urls(tmp_path,monkeypatch):
    runtime=SimpleNamespace(service=object(),programs=lambda:[],close=lambda:None,
        source_locator=lambda ident:{'source_url':'https://untrusted.example/file'})
    monkeypatch.setattr('backend.lifecycle.FacultyRuntime.open',lambda *a,**k:runtime)
    with TestClient(create_app(settings(tmp_path))) as client:
        assert client.get('/api/sources/id').status_code==404
