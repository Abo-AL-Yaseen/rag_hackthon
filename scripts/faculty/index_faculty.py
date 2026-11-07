"""Build one fresh faculty store with existing engine; network is prohibited."""
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'.local/engineering_faculty_20261107'
RUN.mkdir(parents=True,exist_ok=True)
P=ROOT/'data/processed/engineering_faculty_20261107'
INDEX=ROOT/'data/index/engineering_faculty_20261107_v1'
sys.path.insert(0,str(ROOT/'src'))
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',
                  ALLOW_PAID_API_CALLS='false',ALLOW_FREE_API_CALLS='false')
from rag_hackathon.workspace import cached_encoder,ingest

def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':
    if INDEX.exists():raise ValueError('Fresh faculty index path required; never overwrite the previous faculty or CE store')
    start=time.perf_counter()
    with patch('socket.socket.connect',side_effect=RuntimeError('Faculty indexing forbids network')):
        print('Loading verified cached CPU encoder; no downloads.',flush=True)
        encoder=cached_encoder();encoder.batch_size=8
        model_ms=(time.perf_counter()-start)*1000
        print('Encoding faculty records into a fresh independent Qdrant directory.',flush=True)
        manifest=ingest(P/'inputs',INDEX,encoder=encoder,include_json=True,max_tokens=400,overlap=60)
        documents=json.loads((P/'documents.json').read_text(encoding='utf-8'))
        binding={'format_version':1,'chunks_sha256':manifest['chunks_sha256'],'documents':documents,
          'selection_policy':'Explicit program and plan; shared regulations only when no program selected. Conflicting graduation summaries withheld.'}
        save(INDEX/'scope_manifest.json',binding)
        manifest['scope_manifest_sha256']=hashlib.sha256((INDEX/'scope_manifest.json').read_bytes()).hexdigest()
        manifest['requires_scoped_retrieval']=True
        save(INDEX/'dataset_manifest.json',manifest)
        save(RUN/'index_result.json',{'index_path':str(INDEX),'manifest':manifest,'cached_model_load_ms':model_ms,
             'encoder_batch_size':8,'live_llm_calls':0,'paid_calls':0,'network_calls':0})
        print(json.dumps({'index_path':str(INDEX),'records':manifest['pages'],'chunks':manifest['chunks'],
             'model_load_ms':model_ms,'index_ms':manifest['embedding_and_index_ms']},ensure_ascii=False),flush=True)
