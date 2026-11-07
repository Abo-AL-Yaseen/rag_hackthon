"""Admin-only, explicitly selected PDF stores. Never joins official retrieval."""
import hashlib
import json
import re
import threading
import uuid

import fitz

from .academic_decisions import normalize
from .generation.contracts import ProviderResult
from .generation.selections import candidate_spans
from .ingestion import load_pages,chunk_pages
from .service import RAGService,RAGPolicy
from .workspace import ingest,open_index

MAX_BYTES=5*1024*1024
MAX_PAGES=25


class UploadError(ValueError):
    pass


class PassageProvider:
    """Select a topical exact passage, not a synthesized or translated answer."""
    is_mock=True
    def generate(self,request):
        def words(text):
            stop={'what','when','where','which','does','this','that','with','from','about','the','how','many','long',
                  'ماذا','هذا','هذه','الذي','التي','كيف','متي','كم','علي','في','من','عن','هل','شو'}
            return {w[:-1] if w.endswith('s') and len(w)>4 else w for w in re.findall(r'\w+',normalize(text)) if len(w)>2 and w not in stop}
        query=words(request.question);choices=[]
        for span in candidate_spans(request.evidence).values():
            ar=bool(re.search(r'[\u0600-\u06ff]',span.excerpt))
            if ar != (request.language=='ar'):continue
            overlap=len(query & words(span.excerpt))
            score=next(h.score for h in request.evidence if h.chunk.chunk_id==span.chunk_id)
            if overlap>=min(2,len(query)) and query and score>=.65:choices.append((overlap,len(span.excerpt),span))
        if not choices:return ProviderResult('{"status":"insufficient_evidence","reason":"missing_evidence","claims":[]}')
        span=max(choices,key=lambda r:(r[0],r[1]))[2]
        return ProviderResult(json.dumps({'status':'answered','reason':'supported','claims':[
            {'text':span.excerpt,'evidence':[{'chunk_id':span.chunk_id,'excerpt':span.excerpt}]}]},ensure_ascii=False))


class UploadedDocuments:
    def __init__(self,runtime,raw_root,index_root):
        self.runtime=runtime;self.raw_root=raw_root;self.index_root=index_root
        self._lock=threading.RLock();self._stores={};self._records={}
        if index_root.exists():
            for path in index_root.glob('*/upload_manifest.json'):
                ident=path.parent.name
                try:
                    if str(uuid.UUID(ident))!=ident:continue
                    record=json.loads(path.read_text(encoding='utf8'))
                    if record['id']==ident:self._records[ident]=record
                except (ValueError,KeyError,TypeError,OSError):continue

    def list(self):
        with self._lock:return [dict(r) for r in self._records.values()]

    def add(self,data,filename):
        if not 0<len(data)<=MAX_BYTES:raise UploadError('size')
        if (not re.fullmatch(r'[\w][\w .()-]{0,95}\.pdf',filename,re.IGNORECASE) or
                filename.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}):raise UploadError('filename')
        if not data.startswith(b'%PDF-'):raise UploadError('signature')
        try:
            with fitz.open(stream=data,filetype='pdf') as pdf:
                if pdf.is_encrypted or pdf.needs_pass or pdf.metadata.get('encryption'):raise UploadError('encrypted')
                if not 1<=len(pdf)<=MAX_PAGES:raise UploadError('pages')
                texts=[p.get_text().strip() for p in pdf]
                if any(not t for t in texts) or sum(map(len,texts))>50000:raise UploadError('text')
        except UploadError:raise
        except Exception:raise UploadError('invalid_pdf') from None
        with self._lock:
            if len(self._records)>=10:raise UploadError('document_limit')
            ident=str(uuid.uuid4());folder=self.raw_root/ident;folder.mkdir(parents=True,exist_ok=False)
            source=folder/filename
            assert source.resolve().parent==folder.resolve()
            source.write_bytes(data);target=self.index_root/ident
            try:
                with self.runtime.embedding_session() as encoder:
                    pages=load_pages(source)
                    if len(chunk_pages(pages,encoder.tokenizer))>128:raise UploadError('chunks')
                    manifest=ingest(source,target,encoder=encoder)
            except UploadError:raise
            except Exception:raise UploadError('extraction_or_index') from None
            record={'id':ident,'filename':filename,'pages':manifest['pages'],'chunks':manifest['chunks'],
                    'sha256':hashlib.sha256(data).hexdigest(),'scope':'uploaded_document_only','official':False}
            (target/'upload_manifest.json').write_text(json.dumps(record),encoding='utf8')
            self._records[ident]=record
            return dict(record)

    def ask(self,ident,question,language):
        with self._lock:
            if ident not in self._records:raise KeyError(ident)
            with self.runtime.embedding_session() as encoder:
                if ident not in self._stores:
                    index=open_index(self.index_root/ident,encoder=encoder)
                    provider=PassageProvider()
                    service=RAGService(index,provider,policy=RAGPolicy(top_k=3,refusal_messages={
                        'ar':'ما لقيت اقتباسًا كافيًا باللغة المختارة في المستند المحدد. وضّح الموضوع أو اختر لغة النص الأصلي.',
                        'en':'No sufficient passage in the selected language was found in this document. Please clarify the topic or select the source language.'}))
                    self._stores[ident]=(index,service)
                return self._stores[ident][1].ask(question,language=language)

    def close(self):
        with self._lock:
            for index,service in self._stores.values():index.close()
            self._stores.clear()
