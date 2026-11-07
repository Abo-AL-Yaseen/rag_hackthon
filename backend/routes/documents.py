"""Bearer-protected admin PDF APIs; raw bounded body avoids multipart dependencies."""
import secrets
from typing import Literal
from uuid import UUID

from fastapi import APIRouter,HTTPException,Query,Request
from pydantic import BaseModel,ConfigDict,Field
from starlette.concurrency import run_in_threadpool

from rag_hackathon.uploaded_documents import MAX_BYTES,UploadError
from rag_hackathon.generation.contracts import RAGResponse

router=APIRouter(prefix='/api/admin/documents',tags=['admin documents'])

def authorized(request,language):
    state=request.app.state.backend
    token=state.settings.admin_document_token
    if token is None or state.uploads is None:
        raise HTTPException(503,detail='إدارة المستندات معطلة؛ يلزم إعداد رمز مسؤول خاص على الخادم.' if language=='ar' else 'Document management is disabled. Configure a private server-side administrator token.')
    supplied=request.headers.get('authorization','')
    if not secrets.compare_digest(supplied.encode('utf-8'),('Bearer '+token.get_secret_value()).encode('utf-8')):
        raise HTTPException(401,detail='يلزم تفويض المسؤول.' if language=='ar' else 'Administrator authorization required.',headers={'WWW-Authenticate':'Bearer'})
    return state.uploads

@router.get('')
def list_documents(request:Request,language:Literal['ar','en']='ar'):
    return authorized(request,language).list()

@router.post('',status_code=201)
async def upload(request:Request,filename:str=Query(...,min_length=1,max_length=100),language:Literal['ar','en']='ar'):
    store=authorized(request,language);data=bytearray()
    async for block in request.stream():
        if len(data)+len(block)>MAX_BYTES:raise HTTPException(413,detail='حجم PDF يتجاوز الحد 5 ميغابايت.' if language=='ar' else 'PDF exceeds the 5 MiB limit.')
        data.extend(block)
    try:
        record=await run_in_threadpool(store.add,bytes(data),filename)
        return {**record,'message':'تم استخراج وفهرسة المستند في نطاق مستقل غير رسمي.' if language=='ar' else 'Document extracted and indexed in a separate, unofficial scope.'}
    except UploadError as exc:
        raise HTTPException(400,detail=('تعذر قبول PDF: ' if language=='ar' else 'PDF rejected: ')+{
            'signature':'توقيع الملف ليس PDF.' if language=='ar' else 'File signature is not PDF.',
            'encrypted':'الملفات المشفرة غير مدعومة.' if language=='ar' else 'Encrypted PDFs are not supported.',
            'pages':'الحد المسموح 1–25 صفحة.' if language=='ar' else 'PDF must contain 1–25 pages.',
            'text':'يلزم PDF نصي مقروء ضمن حدود النص.' if language=='ar' else 'Readable text-based PDF within text limits required.',
        }.get(str(exc),'الاسم أو الاستخراج أو حدود المستند غير صالحة.' if language=='ar' else 'Invalid filename, extraction or document limits.')) from None

class DocumentQuestion(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    question:str=Field(min_length=1,max_length=2000)
    language:Literal['ar','en']='ar'

@router.post('/{document_id}/ask',response_model=RAGResponse)
async def ask(document_id:UUID,body:DocumentQuestion,request:Request):
    store=authorized(request,body.language)
    try:return await run_in_threadpool(store.ask,str(document_id),body.question,body.language)
    except KeyError:raise HTTPException(404,detail='المستند غير موجود.' if body.language=='ar' else 'Document not found.') from None
