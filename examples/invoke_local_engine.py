"""Executable direct engine call with explicit offline fixture rules; no server."""
import argparse
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rag_hackathon.generation.providers import DeterministicMockProvider
from rag_hackathon.generation.contracts import RAGResponse
from rag_hackathon.service import RAGService
from rag_hackathon.workspace import open_index


def invoke(index,request,rules=()):
    if set(request)-{'question','language'} or 'question' not in request:
        raise ValueError('Request allows only question and language')
    engine=RAGService(index,DeterministicMockProvider(rules))
    response=engine(request['question'],language=request.get('language','en'))
    RAGResponse.model_validate(response)
    return response


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index',type=Path,required=True)
    parser.add_argument('--request',type=Path,required=True)
    parser.add_argument('--mock-rules',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    request=json.loads(args.request.read_text(encoding='utf-8'))
    rules=[]
    if args.mock_rules:
        fixture=json.loads(args.mock_rules.read_text(encoding='utf-8'))
        if fixture.get('synthetic') is not True or fixture.get('scripted') is not True:
            raise ValueError('Explicit synthetic/scripted fixture label required')
        rules=fixture['rules']
    with patch('socket.socket.connect',side_effect=RuntimeError('Integration example is offline only')):
        index=open_index(args.index)
        try: response=invoke(index,request,rules)
        finally: index.close()
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(response,ensure_ascii=False,indent=2),encoding='utf-8')
        print('Saved contract-valid mock response. No HTTP server or live provider used.')
    else: print(json.dumps(response,ensure_ascii=True,indent=2))


if __name__=='__main__': main()
