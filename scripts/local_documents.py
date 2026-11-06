"""Offline-only extraction, fresh ingestion and retrieval. Never loads .env or an LLM."""
import argparse
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rag_hackathon.workspace import read_inputs,ingest,open_index
from dataclasses import asdict


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ('extract','ingest'):
        command=sub.add_parser(name)
        command.add_argument('--input',type=Path,required=True)
        command.add_argument('--include-json',action='store_true')
        command.add_argument('--output',type=Path,required=name=='extract')
        if name=='ingest': command.add_argument('--index',type=Path,required=True)
    retrieve=sub.add_parser('retrieve')
    retrieve.add_argument('--index',type=Path,required=True)
    retrieve.add_argument('--question',required=True)
    retrieve.add_argument('--k',type=int,default=3)
    retrieve.add_argument('--output',type=Path)
    args=parser.parse_args()
    with patch('socket.socket.connect',side_effect=RuntimeError('Local document CLI forbids network calls')):
        if args.command=='extract':
            pages,files=read_inputs(args.input,include_json=args.include_json)
            value={'pages':[asdict(p) for p in pages],'files':len(files)}
        elif args.command=='ingest':
            value=ingest(args.input,args.index,include_json=args.include_json)
        else:
            index=open_index(args.index)
            try: value={'hits':[h.as_dict() for h in index.search(args.question,args.k)]}
            finally: index.close()
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
        print('Saved local result; no network or LLM call made.')
    else:
        print(json.dumps(value,ensure_ascii=True,indent=2))


if __name__=='__main__': main()
