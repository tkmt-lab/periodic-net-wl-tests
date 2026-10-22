"""Runtime graph and proof production. Expectations guide target radii, not verdicts."""
import copy
import time
from collections import Counter, deque
from pathlib import Path

import algorithm
import geometry
import refutation
from source_io import (SOURCES, arc_catalogue, digest, need, normalized, read,
                       records, settings, spacegroups, write)


def cs10(adjacency, root):
    found = {(root, 0, 0, 0): 0}
    queue = deque(found)
    counts = [0] * 10
    while queue:
        u = queue.popleft()
        r = found[u]
        if r == 10:
            continue
        for j, shift in adjacency[u[0]]:
            v = (j, *(u[k + 1] + shift[k] for k in range(3)))
            if v not in found:
                found[v] = r + 1
                counts[r] += 1
                queue.append(v)
                need(len(found) <= 50000, 'CS10 cap 50000')
    return counts


def arc_graph(raw, catalogue):
    key = catalogue[raw['name']]
    need(key is not None, 'ambiguous ARC name; no arbitrary key selection')
    need(key[0] == 3 and (len(key) - 1) % 5 == 0, 'ARC key format')
    edges = [key[i:i + 5] for i in range(1, len(key), 5)]
    n = max(max(e[:2]) for e in edges)
    need(0 < n <= 1200, 'ARC quotient cap')
    adj = [set() for _ in range(n)]
    for i, j, x, y, z in edges:
        need(i > 0 and j > 0 and (i != j or (x, y, z) != (0, 0, 0)), 'ARC loop/index')
        adj[i - 1].add((j - 1, (x, y, z)))
        adj[j - 1].add((i - 1, (-x, -y, -z)))
    adj = [[[j, list(s)] for j, s in sorted(row)] for row in adj]
    sequences = [cs10(adj, i) for i in range(n)]
    actual, wanted = Counter(map(tuple, sequences)), Counter()
    for v in raw['vertices']:
        wanted[tuple(v['cs10'])] += v['multiplicity']
    need(set(actual) == set(wanted), 'ARC CS10 classes')
    need(all(actual[s] * raw['estimated_quotient_vertices'] == wanted[s] * n for s in actual), 'ARC weighted CS10')
    roots = {}
    for v in raw['vertices']:
        if sum(w['cs10'] == v['cs10'] for w in raw['vertices']) == 1:
            roots[v['label']] = sequences.index(v['cs10'])
    return {'schema': 'R019-periodic-graph-v1', 'net': raw['name'], 'record_id': raw['record_id'],
            'vertices': [{'degree': len(row)} for row in adj], 'adjacency': adj,
            'source_roots': roots, 'arc_key': key, 'arc_all_vertex_cs10': sequences,
            'source_mode': 'ARC-catalogue-CS10-correspondence',
            'model': {'kind': 'arc', 'assumption': 'fixed name, weighted CS10, unique source orbit'},
            'source_binding': {'3dall_sha256': SOURCES['3dall.txt']['sha256'],
                               'record_sha256': raw['record_sha256'], 'arc_sha256': SOURCES['RCSRnets.arc']['sha256']}}


def coordinate_graph(raw, groups):
    import re
    need(re.fullmatch(r'[1234][abc]?', raw['embed_type']) is not None, 'special embed type: coordinate model unsupported')
    choices = settings(raw, groups)
    need(choices, 'no explicit spacegroup setting')
    attempts = []
    # Fixed before execution: literals, then denominator <=12, then <=48.
    for denominator in [0, 12, 48]:
        rec = normalized(raw, denominator)
        admissible = []
        for setting in choices:
            effective = copy.deepcopy(rec)
            effective['spacegroup_table_key'] = setting
            try:
                g = geometry.build(effective, groups[setting])
                admissible.append((setting, g))
                attempts.append({'denominator': denominator, 'setting': setting, 'status': 'constraints-pass'})
            except TimeoutError:
                raise
            except (ValueError, AssertionError, KeyError) as error:
                attempts.append({'denominator': denominator, 'setting': setting, 'status': 'unverified', 'reason': str(error)})
        if admissible:
            signatures = [(g['adjacency'], g['source_roots']) for _, g in admissible]
            need(all(s == signatures[0] for s in signatures), 'multiple settings produce different graphs')
            setting, g = admissible[0]
            g['model'] = {'kind': 'coordinate', 'denominator': denominator, 'setting': setting,
                          'admissible_settings': [s for s, _ in admissible], 'attempts': attempts,
                          'assumption': 'literal or unique rational inside printed rounding interval; not a proof of source intent'}
            g['source_binding'] = {'3dall_sha256': SOURCES['3dall.txt']['sha256'], 'record_sha256': raw['record_sha256']}
            return g
    raise ValueError('coordinate constraints failed: ' + repr(attempts))


def witness(a, b):
    n = len(a['adjacency'])
    edges = a['adjacency'] + [[n + j for j in row] for row in b['adjacency']]
    labels = [(d, len(row)) for g in [a, b] for d, row in zip(g['distance'], g['adjacency'])]
    palette = {s: i for i, s in enumerate(sorted(set(labels)))}
    colors, steps = [palette[x] for x in labels], []
    for _ in range(len(edges) + 1):
        steps.append([colors[:n], colors[n:]])
        if Counter(colors[:n]) != Counter(colors[n:]):
            return steps
        signatures = [(colors[i], tuple(sorted(colors[j] for j in row))) for i, row in enumerate(edges)]
        palette = {s: i for i, s in enumerate(sorted(set(signatures)))}
        colors = [palette[x] for x in signatures]
    raise ValueError('WL witness did not distinguish the requested radius')


def walk_count(edges, proof):
    k = proof['walk_length']
    starts = [0] if proof['method'] == 'root-closed-walk-count' else range(len(edges))
    total = 0
    for start in starts:
        row = [int(i == start) for i in range(len(edges))]
        for _ in range(k):
            row = [sum(row[j] for j in neighbors) for neighbors in edges]
        total += row[start]
    return total


def make_certificate(case, graphs):
    cache = {}
    def ball(side, radius):
        key = side, radius
        if key not in cache:
            graph = graphs[case[side]['net']]
            adjacency, distance, vertices = algorithm.ball(graph, graph['source_roots'][case[side]['orbit']], radius)
            cache[key] = {'adjacency': adjacency, 'distance': distance, 'vertices': vertices}
        return cache[key]
    r, wr = case['r_min'], case['r_WL']
    a, b = ball('a', r - 1), ball('b', r - 1)
    mapping, nodes = algorithm.isomorphism(a['adjacency'], a['distance'], b['adjacency'], b['distance'])
    need(mapping is not None, 'no map at the expected preceding radius')
    a, b = ball('a', r), ball('b', r)
    method = case['proof_summary']['method']
    if method == '1-WL':
        proof = {'method': method}
    elif method in ['root-closed-walk-count', 'closed-walk-trace']:
        proof = {'method': method, 'walk_length': case['proof_summary']['walk_length']}
        proof.update(count_a=walk_count(a['adjacency'], proof), count_b=walk_count(b['adjacency'], proof))
        need(proof['count_a'] != proof['count_b'], 'selected walk invariant did not separate')
    elif method == 'individualization-refinement-refutation':
        found, tree, calls = refutation.isomorphism_or_refutation(a['adjacency'], a['distance'], b['adjacency'], b['distance'], algorithm.refine)
        need(found is None, 'map exists at expected nonisomorphic radius')
        proof = {'method': method, 'tree': tree, 'nodes': calls}
    else:
        raise ValueError('unknown expected proof method')
    history = []
    for radius in range(1, wr + 1):
        a, b = ball('a', radius), ball('b', radius)
        _, _, different, _, _ = algorithm.refine(a['adjacency'], a['distance'], b['adjacency'], b['distance'])
        history.append({'radius': radius, 'first_differing_round': different})
    colors = witness(ball('a', wr), ball('b', wr))
    return {'schema': 'R019-suite-certificate-v1', 'case': case['id'], 'r_min': r, 'r_WL': wr,
            'graph_sha256': {}, 'isomorphic': {'radius': r - 1, 'mapping_a_to_b': mapping, 'search_nodes': nodes},
            'proof': proof, 'WL_by_radius': history, 'WL_witness': colors}


def build(work, cases, root, budget, allow_arc=False):
    work = Path(work)
    groups = spacegroups(root / 'third-party/sgtable.data')
    names = {c[s]['net'] for c in cases for s in ['a', 'b']}
    raw = records(work / 'inputs/3dall.txt', names)
    catalogue = arc_catalogue(work / 'inputs/RCSRnets.arc') if allow_arc else None
    graphs, outcomes = {}, {}
    for name in sorted(names):
        tick = time.monotonic()
        try:
            with budget.limit(90):
                try:
                    g = coordinate_graph(raw[name], groups)
                except (ValueError, AssertionError) as error:
                    if not allow_arc:
                        raise
                    g = arc_graph(raw[name], catalogue)
                    g['model']['coordinate_attempt'] = str(error)
                write(work / 'graphs' / (name + '.json'), g)
                graphs[name] = g
                outcomes[name] = {'status': 'BUILT', 'model': g['model']['kind'], 'denominator': g['model'].get('denominator')}
        except Exception as error:
            outcomes[name] = {'status': 'UNVERIFIED', 'reason': repr(error)}
        outcomes[name]['seconds'] = round(time.monotonic() - tick, 6)
        print('BUILD', name, outcomes[name]['status'], outcomes[name].get('model', ''), flush=True)
    write(work / 'build-report.json', outcomes)
    produced = {}
    for case in cases:
        tick = time.monotonic()
        try:
            with budget.limit(90):
                need(all(case[s]['net'] in graphs for s in ['a', 'b']), 'source graph unavailable')
                certificate = make_certificate(case, graphs)
                certificate['graph_sha256'] = {s: digest(work / 'graphs' / (case[s]['net'] + '.json')) for s in ['a', 'b']}
                write(work / 'certificates' / (case['id'] + '.json'), certificate)
                produced[case['id']] = {'status': 'PRODUCED'}
        except Exception as error:
            produced[case['id']] = {'status': 'UNVERIFIED', 'reason': repr(error)}
        produced[case['id']]['seconds'] = round(time.monotonic() - tick, 6)
        print('CERTIFICATE', case['id'], produced[case['id']]['status'], flush=True)
    write(work / 'production-report.json', produced)
    return 0 if all(r['status'] == 'PRODUCED' for r in produced.values()) else 3
