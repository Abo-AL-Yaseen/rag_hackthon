from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
import secrets

import fitz
from fastapi.testclient import TestClient
from pydantic import SecretStr
import pytest

from backend.app import create_app
from backend.config import BackendSettings
from backend.lifecycle import AppState
from rag_hackathon.uploaded_documents import UploadedDocuments,MAX_BYTES


def pdf_bytes(text='The telescope reservation lasts ninety minutes.',pages=1,encrypted=False):
    with fitz.open() as doc:
        for _ in range(pages):
            page=doc.new_page()
            if text:page.insert_text((50,70),text)
        return doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256,owner_pw='test-owner',user_pw='test-user') if encrypted else doc.tobytes()


@pytest.fixture
def admin(tmp_path,encoder):
    token=secrets.token_urlsafe(40)
    settings=BackendSettings(index_path=None,catalog_path=tmp_path/'catalog',mock_rules_path=None,cors_origins=('http://127.0.0.1:5173',),load_dotenv_file=None,host='127.0.0.1',port=8000,allow_paid_api_calls=False,allow_free_api_calls=False,llm_provider='mock',admin_document_token=SecretStr(token),admin_upload_root=tmp_path/'raw',admin_index_root=tmp_path/'index')
    class Runtime:
        service=object()
        @contextmanager
        def embedding_session(self):yield encoder
        def close(self):pass
        def programs(self):return []
    runtime=Runtime();store=UploadedDocuments(runtime,settings.admin_upload_root,settings.admin_index_root)
    state=AppState(settings=settings,runtime=runtime,service=runtime.service,index_open=True,uploads=store)
    with TestClient(create_app(settings,state=state)) as client:yield client,{'Authorization':'Bearer '+token},store


def test_valid_upload_index_question_cites_real_filename_and_page(admin):
    client,headers,store=admin
    uploaded=client.post('/api/admin/documents?filename=reservation.pdf&language=en',content=pdf_bytes(),headers=headers)
    assert uploaded.status_code==201,uploaded.text
    record=uploaded.json();assert record['pages']==1 and record['chunks']>=1 and record['official'] is False
    result=client.post('/api/admin/documents/'+record['id']+'/ask',headers=headers,json={'question':'How long is the telescope reservation?','language':'en'})
    assert result.status_code==200
    answer=result.json();assert answer['status']=='answered',answer
    assert 'ninety minutes' in answer['answer']
    assert answer['sources'][0]['document_name']=='reservation.pdf' and answer['sources'][0]['page_number']==1
    assert answer['validation']['support_check']=='exact_quote' and answer['mode']=='mock'
    refused=client.post('/api/admin/documents/'+record['id']+'/ask',headers=headers,json={'question':'How long is the telescope reservation?','language':'ar'}).json()
    assert refused['status']=='insufficient_evidence' and not refused['sources']


@pytest.mark.parametrize('name,data,status',[
 ('image.pdf',b'PNG not PDF',400),('../escape.pdf',pdf_bytes(),400),('encrypted.pdf',pdf_bytes(encrypted=True),400),
 ('blank.pdf',pdf_bytes(text=''),400),('many.pdf',pdf_bytes(pages=26),400),('large.pdf',b'%PDF-'+b'x'*MAX_BYTES,413),
],ids=['signature','path','encrypted','blank','pages','oversized'])
def test_invalid_uploads_rejected_before_index(admin,name,data,status):
    client,headers,store=admin
    assert client.post('/api/admin/documents',params={'filename':name,'language':'en'},content=data,headers=headers).status_code==status
    assert not store.list()


def test_backend_authorization_protects_upload_list_and_questions(admin):
    client,headers,store=admin
    assert client.get('/api/admin/documents').status_code==401
    assert client.post('/api/admin/documents?filename=valid.pdf',content=pdf_bytes()).status_code==401
    assert client.post('/api/admin/documents/00000000-0000-0000-0000-000000000000/ask',json={'question':'x','language':'en'}).status_code==401
    assert client.get('/api/admin/documents',headers={'Authorization':'Bearer incorrect'}).status_code==401


def test_two_uploaded_document_scopes_do_not_mix(admin):
    client,headers,store=admin
    a=client.post('/api/admin/documents?filename=first.pdf',content=pdf_bytes(),headers=headers).json()
    b=client.post('/api/admin/documents?filename=second.pdf',content=pdf_bytes('The microscope reservation lasts seventy minutes.'),headers=headers).json()
    result=client.post('/api/admin/documents/'+a['id']+'/ask',headers=headers,json={'question':'How long is the telescope reservation?','language':'en'}).json()
    assert 'ninety' in result['answer'] and 'seventy' not in result['answer']
    assert all(s['document_name']=='first.pdf' for s in result['sources'])


def test_arabic_pdf_answer_keeps_original_physical_page(admin):
    client,headers,store=admin
    data=(Path(__file__).resolve().parents[1]/'data/sample/readiness/inputs/readiness_arabic.pdf').read_bytes()
    record=client.post('/api/admin/documents?filename=arabic_fixture.pdf&language=ar',content=data,headers=headers).json()
    result=client.post('/api/admin/documents/'+record['id']+'/ask',headers=headers,json={'question':'متى تبدأ جولة المتحف؟','language':'ar'}).json()
    assert result['status']=='answered' and 'جولة المتحف' in result['answer'],result
    assert result['language']=='ar' and result['sources'][0]['page_number']==2
