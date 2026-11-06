"""Offline synthetic RAG contract demonstration; no remote provider option."""
import argparse
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rag_hackathon.preparation import build_preparation_service


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--question',default='كم يوماً يمكن استعارة الكتب؟')
    parser.add_argument('--language',choices=['ar','en'],default='ar')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    with patch('socket.socket.connect',side_effect=RuntimeError('Offline demo: external calls disabled')):
        service,index,_=build_preparation_service(ROOT)
        try:
            response=service(args.question,language=args.language)
        finally:
            index.close()
    text=json.dumps(response,ensure_ascii=False,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(text,encoding='utf-8')
        print('Wrote mock-only contract demonstration.')
    else:
        # ensure_ascii avoids Windows console encoding failures, preserves JSON round-trip.
        print(json.dumps(response,ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
