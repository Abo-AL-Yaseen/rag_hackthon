"""Record installed runtime versions and hashes of matching cached wheels, offline."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

from packaging.utils import canonicalize_name, parse_wheel_filename

ROOT = Path(__file__).resolve().parents[1]


def main():
    if Path(sys.prefix).resolve() != (ROOT/'.venv').resolve():
        raise RuntimeError('Use project venv')
    wheels = {}
    for path in (ROOT/'.cache/wheels').glob('*.whl'):
        name,version,_,_ = parse_wheel_filename(path.name)
        wheels[(canonicalize_name(name),str(version))] = path
    rows,manifest,packages = [],[],[]
    for dist in sorted(importlib.metadata.distributions(),key=lambda d:d.metadata['Name'].lower()):
        name,version = canonicalize_name(dist.metadata['Name']),dist.version
        packages.append({'name':name,'version':version})
        if name in {'pip','setuptools'}:
            continue
        path = wheels.get((name,version))
        if path is None:
            raise RuntimeError(f'No cached wheel for installed {name}=={version}')
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream,'sha256').hexdigest()
        rows.append(f'{name}=={version} --hash=sha256:{digest}')
        manifest.append({'name':name,'version':version,'wheel':path.name,'bytes':path.stat().st_size,'sha256':digest,
                         'license_metadata':(dist.metadata.get('License-Expression') or dist.metadata.get('License') or 'not declared')[:250]})
    (ROOT/'requirements-phase1.lock.txt').write_text(
        '# Windows x64 / Python 3.11.9 / CPU-only; generated from verified installed wheels.\n'
        '# Install offline: python -m pip install --no-index --find-links .cache/wheels --require-hashes -r requirements-phase1.lock.txt\n'
        + '\n'.join(rows)+'\n',encoding='utf-8')
    (ROOT/'docs/evidence/wheel_manifest.json').write_text(json.dumps(manifest,indent=2))
    (ROOT/'docs/evidence/phase1_packages.json').write_text(json.dumps(packages,indent=2))
    print(f'Locked {len(rows)} installed runtime packages with wheel SHA-256; bootstrap tools recorded separately.')


if __name__ == '__main__':
    main()
