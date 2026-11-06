"""Materialize the fixture's named sources as actual local document files."""
from collections import defaultdict
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    fixture = json.loads((ROOT/'data/sample/synthetic_pages.json').read_text(encoding='utf-8'))
    grouped = defaultdict(list)
    for page in fixture['pages']:
        grouped[page['source']].append(page)
    target = ROOT/'data/sample/documents'
    target.mkdir(exist_ok=True)
    for name,pages in grouped.items():
        if Path(name).name != name:
            raise ValueError('Fixture source must be a basename')
        content = {k:fixture[k] for k in ('synthetic','version','notice')}
        content['pages'] = pages
        (target/name).write_text(json.dumps(content,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Materialized {len(grouped)} explicitly synthetic JSON source documents.')


if __name__ == '__main__':
    main()
