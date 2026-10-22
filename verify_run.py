"""Fresh verification; never imports the producer or consumes saved PASS verdicts."""
import time
from collections import Counter
from pathlib import Path

import core_check
import finite_check
import source_check
from source_io import (SOURCES, arc_catalogue, checked_effective, digest, need,
                       read, records, spacegroups, write)


def graph_shape(g):
    need(g['schema'] == 'R019-periodic-graph-v1', 'unknown graph schema')
    n = len(g['adjacency'])
    need(0 < n <= 1200 and len(g['vertices']) == n, 'graph vertex count/cap')
    for row in g['adjacency']:
        for j, shift in row:
            need(type(j) is int and 0 <= j < n and len(shift) == 3, 'invalid graph index or shift')
            need(all(type(t) is int and abs(t) <= 100 for t in shift), 'invalid integer shift')
    for root in g['source_roots'].values():
        need(type(root) is int and 0 <= root < n, 'invalid source root')


def check_source(g, raw, groups, catalogue):
    graph_shape(g)
    need(g['net'] == raw['name'] and g['record_id'] == raw['record_id'], 'source identity')
    binding = g['source_binding']
    need(binding['3dall_sha256'] == SOURCES['3dall.txt']['sha256'] and binding['record_sha256'] == raw['record_sha256'], 'source byte binding')
    if g['model']['kind'] == 'coordinate':
        need(not g['source_mode'].startswith('ARC'), 'coordinate/ARC model mismatch')
        effective = checked_effective(raw, g['model'], groups)
        return source_check.verify(g, effective, groups, {})
    need(g['model']['kind'] == 'arc' and g['source_mode'] == 'ARC-catalogue-CS10-correspondence', 'unknown source model')
    need(catalogue is not None and binding['arc_sha256'] == SOURCES['RCSRnets.arc']['sha256'], 'ARC input not authorized/present')
    return source_check.verify(g, raw, groups, {raw['name']: catalogue[raw['name']]})


def check_case(case, cert, graphs):
    need(cert['schema'] == 'R019-suite-certificate-v1', 'unknown certificate schema')
    need(cert['case'] == case['id'], 'wrong case identity')
    r, wr = cert['r_min'], cert['r_WL']
    need(type(r) is int and type(wr) is int and 1 <= r <= wr <= 8, 'radius domain')
    cache = {}
    def ball(side, radius):
        key = side, radius
        if key not in cache:
            g = graphs[case[side]['net']]
            adj = [{(j, *shift) for j, shift in row} for row in g['adjacency']]
            cache[key] = core_check.independent_ball(adj, g['source_roots'][case[side]['orbit']], radius)
        return cache[key]
    mapping = cert['isomorphic']['mapping_a_to_b']
    need(cert['isomorphic']['radius'] == r - 1, 'preceding radius')
    need(all(type(x) is int for x in mapping), 'mapping requires integer vertices')
    core_check.check_mapping(mapping, ball('a', r - 1)[2], ball('b', r - 1)[2])
    a, b = ball('a', r), ball('b', r)
    proof = cert['proof']
    method = proof['method']
    if method == '1-WL':
        need(finite_check.wl(a, b) is not None, 'false WL nonisomorphism')
    elif method == 'individualization-refinement-refutation':
        finite_check.check_refutation(proof['tree'], a, b)
    elif method in ['root-closed-walk-count', 'closed-walk-trace']:
        k = proof['walk_length']
        need(type(k) is int and 1 <= k <= 16, 'walk length')
        counts = [core_check.walk_invariant(data[2], proof) for data in [a, b]]
        need(counts == [proof['count_a'], proof['count_b']] and counts[0] != counts[1], 'walk nonisomorphism certificate')
    else:
        raise ValueError('unknown proof method')
    history = cert['WL_by_radius']
    need([x['radius'] for x in history] == list(range(1, wr + 1)), 'WL radius coverage')
    for row in history:
        radius = row['radius']
        result = finite_check.wl(ball('a', radius), ball('b', radius))
        need(result == row['first_differing_round'] and (result is not None) == (radius == wr), 'first WL difference')
    finite_check.check_witness(cert['WL_witness'], ball('a', wr), ball('b', wr))
    need((r, wr) == (case['r_min'], case['r_WL']), 'verified radii disagree with expected table')
    summary = {k: v for k, v in proof.items() if k in ['method', 'walk_length', 'count_a', 'count_b']}
    need(summary == case['proof_summary'], 'verified proof summary disagrees with expected table')
    return {'r_min': r, 'r_WL': wr, 'delay': wr - r, 'proof_summary': summary}


def verify(work, cases, root, budget, allow_arc=False, report=None):
    work = Path(work)
    names = {c[s]['net'] for c in cases for s in ['a', 'b']}
    raw = records(work / 'inputs/3dall.txt', names)
    groups = spacegroups(root / 'third-party/sgtable.data')
    catalogue = arc_catalogue(work / 'inputs/RCSRnets.arc') if allow_arc else None
    graphs, source_results = {}, {}
    for name in sorted(names):
        tick = time.monotonic()
        try:
            with budget.limit(90):
                path = work / 'graphs' / (name + '.json')
                if not path.exists():
                    raise FileNotFoundError('graph not produced')
                need(path.stat().st_size <= 20000000, 'graph size cap')
                g = read(path)
                detail = check_source(g, raw[name], groups, catalogue)
                graphs[name] = g
                source_results[name] = {'status': 'PASS', 'kind': g['model']['kind'], 'denominator': g['model'].get('denominator'),
                                        'graph_sha256': digest(path), 'detail': detail}
        except (FileNotFoundError, TimeoutError, MemoryError, RecursionError) as error:
            source_results[name] = {'status': 'UNVERIFIED', 'reason': repr(error)}
        except Exception as error:
            source_results[name] = {'status': 'FAIL', 'reason': repr(error)}
        source_results[name]['seconds'] = round(time.monotonic() - tick, 6)
        print('SOURCE-CHECK', name, source_results[name]['status'], flush=True)
    results = {}
    for case in cases:
        tick = time.monotonic()
        try:
            with budget.limit(90):
                statuses = [source_results[case[s]['net']]['status'] for s in ['a', 'b']]
                if 'FAIL' in statuses:
                    raise ValueError('fresh source verification failed')
                if 'UNVERIFIED' in statuses:
                    raise FileNotFoundError('fresh source verification unavailable')
                if any(case[s]['orbit'] not in graphs[case[s]['net']]['source_roots'] for s in ['a', 'b']):
                    raise FileNotFoundError('source root correspondence unavailable')
                path = work / 'certificates' / (case['id'] + '.json')
                if not path.exists():
                    raise FileNotFoundError('certificate not produced')
                need(path.stat().st_size <= 30000000, 'certificate size cap')
                cert = read(path)
                for s in ['a', 'b']:
                    need(cert['graph_sha256'][s] == source_results[case[s]['net']]['graph_sha256'], 'graph byte binding in certificate')
                detail = check_case(case, cert, graphs)
                results[case['id']] = dict(status='PASS', **detail)
        except (FileNotFoundError, TimeoutError, MemoryError, RecursionError) as error:
            results[case['id']] = {'status': 'UNVERIFIED', 'reason': repr(error)}
        except Exception as error:
            results[case['id']] = {'status': 'FAIL', 'reason': repr(error)}
        results[case['id']]['seconds'] = round(time.monotonic() - tick, 6)
        print('CHECK', case['id'], results[case['id']]['status'], flush=True)
    counts = dict(Counter(r['status'] for r in results.values()))
    source_counts = dict(Counter(r['status'] for r in source_results.values()))
    code = 1 if counts.get('FAIL') or source_counts.get('FAIL') else 3 if counts.get('UNVERIFIED') or source_counts.get('UNVERIFIED') else 0
    output = {'schema': 'R019-suite-verdict-v1', 'status': 'PASS' if code == 0 else 'FAIL' if code == 1 else 'UNVERIFIED',
              'exit_code': code, 'sources': source_results, 'cases': results, 'case_counts': counts,
              'source_counts': source_counts, 'saved_PASS_receipts_used': False,
              'verification': 'fresh source checks and separate finite-proof algorithms; shared definitions and parser; not another-agent review'}
    write(report or work / 'verification.json', output)
    return code
