"""Prepare three explicitly scripted OFFLINE demo cases from local verified evidence.

This does not generate answers or change retrieval. The mock still requires each
selected excerpt in the actual scoped top-k evidence and validates citations.
No source text, private reports, or indexes are distributed with this script.
"""
import argparse
import json
from pathlib import Path


CASES = (
    ('شو المتطلب السابق لتركيب بيانات وخوارزميات 10636211؟',
     ('eng_computer-engineering_2021-1_10636211_ar',)),
    ('لحد إمتى بقدر أسحب مادة؟ وهل بحتفظ بالحق المالي؟',
     ('policy_late_withdrawal', 'policy_financial_withdrawal', 'policy_add_drop')),
    ('إمتى بنزل علي إنذار بسبب معدلي التراكمي؟',
     ('policy_engineering_warning', 'policy_first_semester_warning')),
)


def prepare_rules(documents, existing=()):
    documents = {d['document_id']: d for d in documents}
    rules = {r['question']: dict(r) for r in existing}
    for question, identifiers in CASES:
        selections = []
        for ident in identifiers:
            doc = documents[ident]  # Missing evidence is an error, never invented.
            quote = doc['reference_quote']
            if not quote or doc.get('retrieval_enabled', True) is not True or doc.get('quality_flags'):
                raise ValueError(f'Unverified mock evidence: {ident}')
            selections.append({'document_id': ident, 'page': doc['engine_page_number'], 'excerpt': quote})
        rules[question] = {'question': question, 'selections': selections}
    return list(rules.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    documents = json.loads((args.index/'scope_manifest.json').read_text(encoding='utf-8'))['documents']
    existing = json.loads(args.output.read_text(encoding='utf-8')) if args.output.exists() else []
    if not isinstance(existing, list):
        raise ValueError('Expected local mock rule list')
    rules = prepare_rules(documents, existing)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Prepared {len(rules)} offline scripted cases; no remote calls or index changes.')


if __name__ == '__main__':
    main()
