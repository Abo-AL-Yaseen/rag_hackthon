"""Budgeted, cached downloads and offline install; run with existing .venv Python.

Counts HTTP response payload bytes (including indexes/metadata), not TLS headers.
Keeps a 50 MB safety reserve below the user's decimal 2 GB cap. Cached responses
are reused without network transfers. No automatic retry of failed large files.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
from urllib.parse import quote, unquote, urljoin, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 2_000_000_000
RESERVE = 50_000_000
PINNED_MODEL_REVISION = '614241f622f53c4eeff9890bdc4f31cfecc418b3'
LEDGER = ROOT / 'docs/evidence/download_ledger.json'
CACHE = ROOT / '.cache/downloads'


class Budget:
    def __init__(self):
        CACHE.mkdir(parents=True, exist_ok=True)
        self.data = json.loads(LEDGER.read_text()) if LEDGER.exists() else {
            'cap_bytes': LIMIT, 'safety_reserve_bytes': RESERVE,
            'accounting': 'HTTP response payload bytes; TLS/header overhead excluded; no paid calls',
            'prior_phase0_allowance_bytes': 18_500_000, 'transferred_bytes': 0, 'requests': []}

    def save(self):
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        LEDGER.write_text(json.dumps(self.data, indent=2), encoding='utf-8')

    def fetch(self, url):
        # No credentials, auth headers or signed redirect URLs are saved.
        key = hashlib.sha256(url.encode()).hexdigest()
        target = CACHE / key
        if target.exists():
            return target
        partial = target.with_suffix('.part')
        offset = partial.stat().st_size if partial.exists() else 0
        remaining = LIMIT - RESERVE - self.data['prior_phase0_allowance_bytes'] - self.data['transferred_bytes']
        if remaining <= 0:
            raise RuntimeError('Download budget exhausted; approval required')
        headers = {'Accept': 'text/html' if '/simple/' in url else '*/*',
                   'Accept-Encoding': 'identity', 'User-Agent': 'rag-phase1-budget/1.0'}
        if offset:
            headers['Range'] = f'bytes={offset}-'
        request = Request(url, headers=headers)
        record = {'url': url.split('?')[0], 'bytes': 0, 'complete': False}
        try:
            with urlopen(request, timeout=90) as response:
                resumed = offset > 0 and getattr(response, 'status', 200) == 206
                if resumed and not response.headers.get('Content-Range', '').startswith(f'bytes {offset}-'):
                    raise RuntimeError('Invalid range response; refusing to append')
                record['resumed_from_bytes'] = offset if resumed else 0
                length = response.headers.get('Content-Length')
                if length is not None and int(length) > remaining:
                    raise RuntimeError(f'File requires {length} bytes, only {remaining} authorized bytes remain')
                record['declared_bytes'] = int(length) if length is not None else None
                with partial.open('ab' if resumed else 'wb') as out:
                    while True:
                        remaining = LIMIT - RESERVE - self.data['prior_phase0_allowance_bytes'] - self.data['transferred_bytes']
                        if remaining <= 0:
                            raise RuntimeError('Budget boundary reached; refusing further reads')
                        block = response.read(min(1024 * 1024, remaining))
                        if not block:
                            break
                        out.write(block)
                        self.data['transferred_bytes'] += len(block)
                        record['bytes'] += len(block)
                        self.save()
                if length is not None and record['bytes'] != int(length):
                    raise RuntimeError('Incomplete HTTP response; not caching')
            record['sha256'] = hashlib.file_digest(partial.open('rb'), 'sha256').hexdigest()
            partial.replace(target)
            record['complete'] = True
            print(f"Downloaded {record['bytes']:,} bytes: {url.split('?')[0]}", flush=True)
            return target
        finally:
            self.data['requests'].append(record)
            self.save()


def install(budget):
    wheel_dir = ROOT / '.cache/wheels'
    wheel_dir.mkdir(parents=True, exist_ok=True)

    class Mirror(BaseHTTPRequestHandler):
        def do_GET(self):
            try:
                if self.path.startswith('/simple/'):
                    upstream = 'https://pypi.org' + self.path
                    raw = budget.fetch(upstream).read_text(encoding='utf-8')
                    def replace(match):
                        original = urljoin(upstream, html.unescape(match.group(1)))
                        token = base64.urlsafe_b64encode(original.split('#')[0].encode()).decode()
                        name = urlsplit(original).path.rsplit('/', 1)[-1]
                        suffix = '#' + original.split('#', 1)[1] if '#' in original else ''
                        return f'href="/file/{token}/{name}{suffix}"'
                    body = re.sub(r'href="([^"]+)"', replace, raw).encode()
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html')
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                elif self.path.startswith('/file/'):
                    _, _, token, name = self.path.split('/', 3)
                    upstream = base64.urlsafe_b64decode(unquote(token)).decode()
                    if name.endswith('.metadata') and not upstream.endswith('.metadata'):
                        upstream += '.metadata'
                    if any(x in name.lower() for x in ('nvidia', 'cuda', 'triton', 'torchvision', 'torchaudio')):
                        raise RuntimeError('GPU/unneeded package blocked')
                    path = budget.fetch(upstream)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/octet-stream')
                    self.send_header('Content-Length', str(path.stat().st_size))
                    self.end_headers()
                    with path.open('rb') as f:
                        shutil.copyfileobj(f, self.wfile)
                else:
                    self.send_error(404)
            except Exception as exc:
                print(f'Mirror error: {exc}', flush=True)
                self.send_error(503, str(exc))

        def log_message(self, *args):
            pass

    # Select exactly the Windows cp311 CPU artifact from the official PyTorch index.
    index_url = 'https://download.pytorch.org/whl/cpu/torch/'
    index = budget.fetch(index_url).read_text()
    links = [html.unescape(x) for x in re.findall(r'href="([^"]+)"', index)]
    candidates = [urljoin(index_url, u) for u in links if
                  'torch-2.8.0%2Bcpu-cp311-cp311-win_amd64.whl' in u or
                  'torch-2.8.0+cpu-cp311-cp311-win_amd64.whl' in u]
    if len(candidates) != 1:
        raise RuntimeError(f'Expected one CPU wheel, found {len(candidates)}')
    url = candidates[0].split('#')[0]
    token = base64.urlsafe_b64encode(url.encode()).decode()
    name = urlsplit(url).path.rsplit('/', 1)[-1]
    with HTTPServer(('127.0.0.1', 0), Mirror) as server:
        port = server.server_port
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        lock = ROOT / 'requirements-phase1.lock.txt'
        requirements = lock if lock.exists() else ROOT / 'requirements-phase1.in'
        text = requirements.read_text()
        text = text.replace('torch==2.8.0+cpu', f'torch @ http://127.0.0.1:{port}/file/{token}/{name}')
        req = ROOT / 'tmp/phase1-download.txt'
        req.parent.mkdir(exist_ok=True)
        req.write_text(text)
        try:
            subprocess.run([sys.executable, '-m', 'pip', '--isolated', '--disable-pip-version-check',
                            'download', '--no-cache-dir', '--only-binary=:all:', '--retries', '0', '--timeout', '300',
                            '--index-url', f'http://127.0.0.1:{port}/simple/', '--trusted-host', '127.0.0.1',
                            '--dest', str(wheel_dir), '-r', str(req)], check=True)
        finally:
            server.shutdown()
            thread.join()
    subprocess.run([sys.executable, '-m', 'pip', '--isolated', '--disable-pip-version-check',
                    'install', '--no-index', '--find-links', str(wheel_dir),
                    '-r', str(requirements)], check=True)


def model(budget):
    model_id = 'intfloat/multilingual-e5-small'
    metadata = json.loads(budget.fetch(
        f'https://huggingface.co/api/models/{model_id}/revision/{PINNED_MODEL_REVISION}?blobs=true').read_text())
    revision = metadata['sha']
    if revision != PINNED_MODEL_REVISION:
        raise RuntimeError('Model revision mismatch')
    wanted = ['config.json', 'model.safetensors', 'modules.json', 'sentence_bert_config.json',
              '1_Pooling/config.json', 'sentencepiece.bpe.model', 'special_tokens_map.json',
              'tokenizer.json', 'tokenizer_config.json', 'README.md']
    entries = {e['rfilename']: e for e in metadata['siblings']}
    if not set(wanted) <= entries.keys():
        raise RuntimeError('Model manifest changed; inspect required files')
    size = sum(entries[n]['size'] for n in wanted)
    remaining = LIMIT - RESERVE - budget.data['prior_phase0_allowance_bytes'] - budget.data['transferred_bytes']
    print(f'Model pinned revision {revision}; selected files {size:,} bytes; remaining {remaining:,}', flush=True)
    if size > remaining:
        raise RuntimeError('Selected model cannot fit approved remaining budget')
    target = ROOT / 'models/multilingual-e5-small'
    manifest = {'model_id': model_id, 'revision': revision, 'files': [], 'selected_bytes': size}
    for name in wanted:
        source = budget.fetch(f'https://huggingface.co/{model_id}/resolve/{revision}/{quote(name, safe="/")}')
        digest = hashlib.file_digest(source.open('rb'), 'sha256').hexdigest()
        if entries[name].get('lfs', {}).get('sha256') not in (None, digest):
            raise RuntimeError(f'Upstream LFS hash mismatch for {name}')
        if source.stat().st_size != entries[name]['size']:
            raise RuntimeError(f'Upstream size mismatch for {name}')
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        manifest['files'].append({'name': name, 'bytes': source.stat().st_size, 'sha256': digest})
    (ROOT / 'docs/evidence/model_manifest.json').write_text(json.dumps(manifest, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['install', 'model'])
    action = parser.parse_args().action
    if Path(sys.prefix).resolve() != (ROOT / '.venv').resolve() or sys.version_info[:3] != (3, 11, 9):
        raise RuntimeError('Use existing .venv Python 3.11.9 only')
    budget = Budget()
    budget.save()
    {'install': install, 'model': model}[action](budget)
    print(f"HTTP payload transferred: {budget.data['transferred_bytes']:,} bytes; cap {LIMIT:,}")


if __name__ == '__main__':
    main()
