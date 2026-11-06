"""Thin local-dataset lifecycle around the existing CPU encoder and retriever."""
import hashlib
import json
from pathlib import Path
import re
import time

from .ingestion import load_pages,chunk_pages
from .schema import Chunk

ROOT=Path(__file__).resolve().parents[2]


def cached_encoder():
    from .retrieval.dense import E5Encoder
    manifest=json.loads((ROOT/'docs/evidence/model_manifest.json').read_text())
    model=ROOT/'models/multilingual-e5-small'
    for item in manifest['files']:
        with (model/item['name']).open('rb') as stream:
            if hashlib.file_digest(stream,'sha256').hexdigest()!=item['sha256']:
                raise ValueError('Local model hash mismatch; no automatic download')
    return E5Encoder(model,manifest['revision'])


def read_inputs(input_path,*,include_json=False):
    source=Path(input_path)
    if source.is_file():
        files=[source]
    elif source.is_dir():
        extensions={'.pdf','.json'} if include_json else {'.pdf'}
        files=sorted(p for p in source.rglob('*') if p.is_file() and p.suffix.lower() in extensions)
    else:
        raise ValueError('Input file/directory does not exist')
    if not files:
        raise ValueError('No supported input documents; directories default to PDF only')
    pages=[]; owners={}
    for path in files:
        loaded=load_pages(path)
        if path.suffix.lower()=='.pdf' and any(re.search('[\ufb50-\ufdff\ufe70-\ufefc\ufffd]',p.text) for p in loaded):
            raise ValueError('PDF Unicode/presentation-form encoding needs manual review or re-export: '+path.name)
        for page in loaded:
            key=page.document_id.casefold()
            if key in owners and owners[key]!=path:
                raise ValueError('Duplicate document ID across files; rename ambiguous source files before indexing')
            owners[key]=path
        pages.extend(loaded)
    if len({(p.document_id.casefold(),p.page) for p in pages})!=len(pages):
        raise ValueError('Duplicate document/page identity across inputs')
    return pages,files


def ingest(input_path,index_path,*,encoder=None,include_json=False,max_tokens=240,overlap=32):
    target=Path(index_path)
    if target.exists():
        raise ValueError('Fresh index path required; existing directories are never appended to or overwritten')
    start=time.perf_counter()
    pages,files=read_inputs(input_path,include_json=include_json)
    extraction_ms=(time.perf_counter()-start)*1000
    encoder=encoder or cached_encoder()
    chunks=chunk_pages(pages,encoder.tokenizer,max_tokens=max_tokens,overlap=overlap)
    target.mkdir(parents=True,exist_ok=False)
    from .retrieval.dense import DenseRetriever
    stage=time.perf_counter()
    index=DenseRetriever(chunks,encoder,target,create=True)
    index.close()
    snapshot=json.dumps([c.payload() for c in chunks],ensure_ascii=False,indent=2).encode('utf-8')
    (target/'chunks.json').write_bytes(snapshot)
    manifest={'state':'complete','files':[{'name':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files],
              'pages':len(pages),'chunks':len(chunks),'model_revision':encoder.revision,
              'chunk_max_tokens':max_tokens,'chunk_overlap':overlap,'collection':DenseRetriever.collection,
              'chunks_sha256':hashlib.sha256(snapshot).hexdigest(),'extraction_ms':extraction_ms,
              'embedding_and_index_ms':(time.perf_counter()-stage)*1000,
              'isolation':'Independent Qdrant Local directory; same collection name in different stores does not share data.'}
    (target/'dataset_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest


def open_index(index_path,*,encoder=None):
    target=Path(index_path)
    manifest=json.loads((target/'dataset_manifest.json').read_text())
    snapshot=(target/'chunks.json').read_bytes()
    if manifest.get('state')!='complete' or hashlib.sha256(snapshot).hexdigest()!=manifest.get('chunks_sha256'):
        raise ValueError('Incomplete or changed dataset snapshot; use a fresh index')
    chunks=[Chunk(**record) for record in json.loads(snapshot)]
    from .retrieval.dense import DenseRetriever
    return DenseRetriever(chunks,encoder or cached_encoder(),target)
