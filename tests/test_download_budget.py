import importlib.util
import io
import hashlib
from pathlib import Path

import pytest


@pytest.fixture
def downloader(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1]/'scripts/setup_phase1.py'
    spec = importlib.util.spec_from_file_location('budget_script',source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module,'CACHE',tmp_path/'cache')
    monkeypatch.setattr(module,'LEDGER',tmp_path/'ledger.json')
    monkeypatch.setattr(module,'LIMIT',100)
    monkeypatch.setattr(module,'RESERVE',10)
    budget = module.Budget()
    budget.data['prior_phase0_allowance_bytes'] = 0
    return module,budget


def response(data, declared=True):
    stream = io.BytesIO(data)
    stream.headers = {'Content-Length':str(len(data))} if declared else {}
    return stream


def test_known_oversize_rejected_before_payload_read(downloader, monkeypatch):
    module,budget = downloader
    stream = response(b'x'*91)
    monkeypatch.setattr(module,'urlopen',lambda *a,**k:stream)
    with pytest.raises(RuntimeError,match='authorized'):
        budget.fetch('https://example.invalid/oversize')
    assert budget.data['transferred_bytes'] == 0


def test_cache_reuse_does_not_transfer_again(downloader, monkeypatch):
    module,budget = downloader
    monkeypatch.setattr(module,'urlopen',lambda *a,**k:response(b'x'*20))
    path = budget.fetch('https://example.invalid/small')
    monkeypatch.setattr(module,'urlopen',lambda *a,**k:pytest.fail('unexpected second network access'))
    assert budget.fetch('https://example.invalid/small') == path
    assert budget.data['transferred_bytes'] == 20


def test_unknown_length_stops_at_reserve(downloader, monkeypatch):
    module,budget = downloader
    monkeypatch.setattr(module,'urlopen',lambda *a,**k:response(b'x'*120,declared=False))
    with pytest.raises(RuntimeError,match='boundary'):
        budget.fetch('https://example.invalid/unknown')
    assert budget.data['transferred_bytes'] == 90
    assert not any(p.suffix != '.part' for p in module.CACHE.iterdir())


def test_partial_resume_counts_only_new_bytes(downloader, monkeypatch):
    module,budget = downloader
    url = 'https://example.invalid/resume'
    key = hashlib.sha256(url.encode()).hexdigest()
    (module.CACHE/(key+'.part')).write_bytes(b'first')
    budget.data['transferred_bytes'] = 5
    stream = response(b'last')
    stream.status = 206
    stream.headers['Content-Range'] = 'bytes 5-8/9'
    def open_range(request, **kwargs):
        assert request.headers['Range'] == 'bytes=5-'
        return stream
    monkeypatch.setattr(module,'urlopen',open_range)
    path = budget.fetch(url)
    assert path.read_bytes() == b'firstlast'
    assert budget.data['transferred_bytes'] == 9
