import pytest

from scripts.prepare_manual_mock_cases import CASES, prepare_rules


def documents():
    return [{'document_id': ident, 'reference_quote': f'verified quote {ident}',
             'engine_page_number': 85, 'retrieval_enabled': True, 'quality_flags': []}
            for _, identifiers in CASES for ident in identifiers]


def test_demo_rules_use_only_manifest_quotes_and_preserve_other_cases():
    existing = [{'question': 'other', 'refusal_reason': 'ambiguous'},
                {'question': CASES[1][0], 'selections': []}]
    rules = prepare_rules(documents(), existing)
    assert rules[0] == existing[0]
    assert len(rules) == 4
    withdrawal = next(r for r in rules if r['question'] == CASES[1][0])
    assert len(withdrawal['selections']) == 3
    assert all(s['excerpt'] == f"verified quote {s['document_id']}" for s in withdrawal['selections'])


def test_missing_or_uncertain_evidence_is_not_scripted():
    with pytest.raises(KeyError):
        prepare_rules([])
    rows = documents()
    rows[0]['quality_flags'] = ['intergroup_AND_OR_not_explicit']
    with pytest.raises(ValueError):
        prepare_rules(rows)
