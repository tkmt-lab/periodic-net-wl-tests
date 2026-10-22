#!/usr/bin/env python3
"""Check claims.json: required fields, file hashes, and case counts against expected.json (standard library)."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    claims = json.loads((ROOT / 'claims.json').read_text())
    schema = json.loads((ROOT / 'claims.schema.json').read_text())
    for key in schema['required']:
        assert key in claims, key
    kinds = set(schema['properties']['kinds']['propertyNames']['enum'])
    assert set(claims['kinds']) <= kinds
    assert not any(claims['scope'].values()), 'scope flags record what is absent and must all be false'
    assert claims['data_source']['redistributed'] is False
    cases = json.loads((ROOT / 'expected.json').read_text())['cases']
    counts = {'core': sum(c['core'] for c in cases), 'main': sum(c['main'] for c in cases), 'all': len(cases)}
    for claim in claims['claims']:
        for key in schema['properties']['claims']['items']['required']:
            assert key in claim, (claim.get('id'), key)
        assert claim['kind'] in claims['kinds'], claim['id']
        for entry in claim['evidence']:
            data = (ROOT / entry['path']).read_bytes()
            assert len(data) == entry['bytes'] and hashlib.sha256(data).hexdigest() == entry['sha256'], entry['path']
        scope = claim.get('numbers', {}).get('scope')
        if scope:
            assert claim['cases'] == counts[scope], (claim['id'], claim['cases'], counts[scope])
    print(json.dumps({'status': 'PASS', 'claims': len(claims['claims']), 'cases': counts}))


if __name__ == '__main__':
    main()
