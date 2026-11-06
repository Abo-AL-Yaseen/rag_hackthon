"""Offline CPU retrieval/evaluation on explicitly synthetic preparation fixtures."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'

from rag_hackathon.resources import MemoryMonitor


def evaluate(retriever, questions, chunks, ks, repeats):
    from rag_hackathon.citations import cite, validate_citation
    from rag_hackathon.evaluation import precision_recall_at_k, summarize
    import numpy as np
    results, all_times = [], []
    max_k = max(ks)
    for case in questions:
        row = dict(case)
        relevant = [c.chunk_id for c in chunks if any(
            c.document_id == s['document_id'] and c.page == s['page'] for s in case['relevant_sources'])]
        if case['answerable'] and not relevant:
            raise ValueError(f"Missing reference labels for {case['id']}")
        row['relevant_chunk_ids'] = relevant
        row['error'] = None
        times = []
        try:
            previous = None
            for _ in range(repeats):
                start = time.perf_counter()
                hits = retriever.search(case['question'], max_k)
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)
                ids = [h.chunk.chunk_id for h in hits]
                if previous is not None and ids != previous:
                    raise ValueError('Nondeterministic ranking across identical repeated query')
                previous = ids
            row['retrieved'] = [h.as_dict() for h in hits]
            row['citations'] = [asdict(cite(h)) for h in hits]
            row['all_citations_valid'] = all(validate_citation(cite(h), hits) for h in hits)
            row['latency_samples_ms'] = times
            row['latency_ms'] = float(np.median(times))
            all_times.extend(times)
            for k in ks:
                scores = precision_recall_at_k(ids, relevant, k)
                row[f'precision@{k}'] = scores['precision']
                row[f'recall@{k}'] = scores['recall']
        except Exception as exc:
            row.update(error=f'{type(exc).__name__}: {exc}', latency_ms=None)
            for k in ks:
                row[f'precision@{k}'] = row[f'recall@{k}'] = None
        results.append(row)
    summaries = {}
    for k in ks:
        summary = summarize(results, k)
        summary.update(latency_n=len(all_times), repeats_per_question=repeats,
                       latency_ms_p50=float(np.percentile(all_times, 50)) if all_times else None,
                       latency_ms_p95=float(np.percentile(all_times, 95)) if all_times else None)
        summaries[str(k)] = summary
    return {'summary': summaries, 'cases': results}


def benchmark_inputs(tokenizer):
    # Bound fixture construction itself; the encoder also independently rejects >512.
    base = 'هذا نص اصطناعي لاختبار سرعة معالجة اللغة العربية في نظام الاسترجاع. '
    long_tokens = tokenizer(base * 100, add_special_tokens=False, truncation=True, max_length=450)['input_ids']
    lengths = [32, 128, 256, 450]
    return [tokenizer.decode(long_tokens[:n], skip_special_tokens=True) for n in lengths] * 2


def benchmark(encoder, questions, chunks):
    import numpy as np
    import torch
    grid = []
    texts = benchmark_inputs(encoder.tokenizer)
    actual_lengths = [len(encoder.tokenizer('passage: ' + t)['input_ids']) for t in texts]
    for threads in (1, 2, 4):
        torch.set_num_threads(threads)
        for batch in (1, 4, 8):
            encoder.batch_size = batch
            for _ in range(3):
                encoder.passages(texts)
            seconds = []
            for _ in range(5):
                start = time.perf_counter()
                encoder.passages(texts)
                seconds.append(time.perf_counter() - start)
            median = float(np.median(seconds))
            grid.append({'threads': threads, 'batch_size': batch, 'warmup_batches': 3,
                         'measured_repetitions': 5, 'passages_per_repetition': len(texts),
                         'prefixed_token_lengths': actual_lengths, 'seconds': seconds,
                         'median_seconds': median, 'chunks_per_second': len(texts) / median,
                         'prefixed_tokens_per_second': sum(actual_lengths) / median})
            print(f'Benchmark threads={threads}, batch={batch}: {len(texts)/median:.2f} chunks/s', flush=True)
    torch.set_num_threads(4)
    encoder.batch_size = 4
    times = []
    for _ in range(3):
        encoder.queries([questions[0]['question']])
    for i in range(30):
        start = time.perf_counter()
        encoder.queries([questions[i % len(questions)]['question']])
        times.append((time.perf_counter() - start) * 1000)
    return {'synthetic': True, 'grid': grid, 'single_query_encoding': {
        'threads': 4, 'batch_size': 4, 'n': len(times), 'samples_ms': times,
        'p50_ms': float(np.percentile(times, 50)), 'p95_ms': float(np.percentile(times, 95))},
        'limitations': ['Sequential laptop run; no AC/thermal control.',
                        'Synthetic repeated text throughput is not real-corpus retrieval quality.',
                        'Model OS file cache may be warm; initialization is not disk-cold guaranteed.']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pages', type=Path, default=ROOT/'data/sample/synthetic_pages.json')
    parser.add_argument('--questions', type=Path, default=ROOT/'data/sample/synthetic_questions.json')
    parser.add_argument('--model', type=Path, default=ROOT/'models/multilingual-e5-small')
    parser.add_argument('--index', type=Path, default=ROOT/'data/index/phase1')
    parser.add_argument('--output', type=Path, default=ROOT/'docs/evidence/phase1_evaluation.json')
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--benchmark', action='store_true')
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error('repeats must be positive')
    with patch('socket.socket.connect', side_effect=RuntimeError('Offline evaluation: network disabled')), MemoryMonitor() as memory:
        from rag_hackathon.ingestion import load_pages, chunk_pages, corpus_hash
        from rag_hackathon.retrieval import E5Encoder, DenseRetriever, BM25Retriever
        from rag_hackathon.citations import cite, validate_citation
        import numpy as np
        import torch
        if torch.version.cuda is not None or '+cpu' not in torch.__version__:
            raise RuntimeError('CPU-only PyTorch required')
        manifest = json.loads((ROOT/'docs/evidence/model_manifest.json').read_text())
        for entry in manifest['files']:
            path = args.model / entry['name']
            if hashlib.file_digest(path.open('rb'), 'sha256').hexdigest() != entry['sha256']:
                raise ValueError(f"Model hash mismatch: {entry['name']}")
        data = json.loads(args.questions.read_text(encoding='utf-8'))
        pages_data = json.loads(args.pages.read_text(encoding='utf-8'))
        if not data.get('synthetic') or not pages_data.get('synthetic'):
            raise ValueError('This preparation runner requires explicitly synthetic fixtures')
        questions = data['questions']
        if sum(q['answerable'] for q in questions) < 10 or len({q['id'] for q in questions}) != len(questions):
            raise ValueError('At least ten unique answerable questions required')
        init_start = time.perf_counter()
        encoder = E5Encoder(args.model, manifest['revision'])
        load_seconds = time.perf_counter() - init_start
        pages = load_pages(args.pages)
        chunks = chunk_pages(pages, encoder.tokenizer)
        print(f'Loaded CPU E5 in {load_seconds:.3f}s; {len(pages)} pages -> {len(chunks)} chunks', flush=True)
        qs = ['كيف أعيد تعيين كلمة المرور؟', 'When can I borrow books?']
        ps = ['Reset your password using account recovery in the support portal.',
              'The library lets members borrow books for twelve days.']
        qv, pv = encoder.queries(qs), encoder.passages(ps)
        similarity = qv @ pv.T
        if not np.isfinite(qv).all() or not np.allclose(np.linalg.norm(qv, axis=1), 1, atol=1e-5):
            raise ValueError('Invalid/non-normalized query embeddings')
        if not (similarity[0, 0] > similarity[0, 1] and similarity[1, 1] > similarity[1, 0]):
            raise ValueError('Arabic/English embedding alignment smoke failed')
        build_start = time.perf_counter()
        index_existing = (args.index/'retrieval_manifest.json').exists()
        dense = DenseRetriever(chunks, encoder, args.index, create=not index_existing)
        build_seconds = time.perf_counter() - build_start
        try:
            for _ in range(3):
                dense.search(questions[0]['question'])
            dense_results = evaluate(dense, questions, chunks, (1, 3), args.repeats)
        finally:
            dense.close()
        reopen_start = time.perf_counter()
        reopened = DenseRetriever(chunks, encoder, args.index)
        try:
            persisted = reopened.search(questions[0]['question'], 1)
            if persisted[0].chunk.document_id != 'library' or persisted[0].chunk.page != 1:
                raise ValueError('Persisted Qdrant retrieval smoke failed')
            if not validate_citation(cite(persisted[0]), persisted):
                raise ValueError('Persisted citation smoke failed')
        finally:
            reopened.close()
        reopen_seconds = time.perf_counter() - reopen_start
        bm_start = time.perf_counter()
        bm25 = BM25Retriever(chunks)
        bm_build_seconds = time.perf_counter() - bm_start
        for _ in range(3):
            bm25.search(questions[0]['question'])
        bm_results = evaluate(bm25, questions, chunks, (1, 3), args.repeats)
        bench = benchmark(encoder, questions, chunks) if args.benchmark else None
        output = {
            'synthetic': True, 'notice': 'Preparation fixtures only; not hackathon performance or held-out validation.',
            'created_utc': datetime.now(timezone.utc).isoformat(),
            'python': platform.python_version(), 'platform': platform.platform(),
            'packages': {n: importlib.metadata.version(n) for n in (
                'torch','sentence-transformers','transformers','qdrant-client','rank-bm25','pytest',
                'scikit-learn','python-dotenv','fastapi','numpy','scipy','psutil','PyMuPDF')},
            'cpu_only': {'torch_cuda_build': torch.version.cuda, 'cuda_available': torch.cuda.is_available(),
                         'model_device': str(encoder.model.device), 'torch_threads': torch.get_num_threads()},
            'model_revision': manifest['revision'], 'embedding_dimension': encoder.dimension,
            'prefixes': {'query': 'query: ', 'passage': 'passage: '}, 'max_sequence_length': 512,
            'config': {'chunk_tokens':240,'overlap_tokens':32,'threads':4,'batch_size':4,'k':[1,3]},
            'corpus_sha256': corpus_hash(chunks), 'pages':len(pages), 'chunks':len(chunks),
            'embedding_smoke': {'queries':qs,'passages':ps,'cosine_matrix':similarity.tolist(),'passed':True},
            'model_initialization_seconds':load_seconds, 'dense_index_build_or_open_seconds':build_seconds,
            'index_was_existing': index_existing, 'qdrant_reopen_and_query_seconds':reopen_seconds,
            'bm25_build_seconds':bm_build_seconds, 'dense':dense_results,'bm25':bm_results,
            'benchmark':bench,
            'faithfulness': {'status':'not evaluated','reason':'Retrieval and exact-quote citations only; no generated answers.'},
            'refusal': {'status':'not implemented','reason':'Dense nearest neighbors do not establish answerability. Unanswerable cases excluded from P/R.'},
            'limitations': ['12 bilingual passages and 12 answerable questions; easy self-authored synthetic data.',
                            'Two unanswerable probes have N/A retrieval relevance metrics, not passing refusal scores.',
                            'All relevant passages are page-level labels on short one-chunk pages.',
                            'Latency includes query encoding for dense and tokenization for BM25; excludes citations/report serialization.',
                            'No hybrid/reranker/base model, generation API, or real challenge evaluation.']}
    output['memory'] = memory.result()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({m:output[m]['summary'] for m in ('dense','bm25')}, indent=2))
    print(json.dumps(output['memory'], indent=2))
    if any(c['error'] for m in ('dense','bm25') for c in output[m]['cases']):
        raise SystemExit('Evaluation errors recorded; inspect report')


if __name__ == '__main__':
    main()
