"""Producer algorithms; inherited lab implementation, no bundled source records."""
from collections import Counter,deque
from fractions import Fraction as Q
from math import lcm
ZERO=(0,0,0)

def parse(s):
    rows, trans = [], []
    import re
    for component in s.split(','):
        row, t = [0, 0, 0], Q(0)
        for token in re.findall(r'[+-]?[^+-]+', component):
            sign = -1 if token.startswith('-') else 1
            atom = token.lstrip('+-')
            if atom in ('x', 'y', 'z'):
                row['xyz'.index(atom)] += sign
            else:
                t += sign * Q(atom)
        rows.append(tuple(row)); trans.append(t % 1)
    return tuple(rows), tuple(trans)

def gram(cell):
    a, b, c, alpha, beta, gamma = map(Q, cell)
    assert alpha == beta == 90 and gamma in (90, 120)
    off = Q(0) if gamma == 90 else -a * b / 2
    m = ((a*a, off, 0), (off, b*b, 0), (0, 0, c*c))
    lower = min(m[i][i] - sum(abs(m[i][j]) for j in range(3) if j != i)
                for i in range(3))
    assert lower > 0
    return m, lower

def ball(graph, root, radius):
    adj = graph['adjacency']; start = (root, *ZERO)
    distance, queue = {start: 0}, deque([start])
    while queue:
        u = queue.popleft()
        if distance[u] == radius:
            continue
        for j, delta in adj[u[0]]:
            v = (j, *(u[k+1]+delta[k] for k in range(3)))
            if v not in distance:
                distance[v] = distance[u]+1; queue.append(v)
                if len(distance)>1200:raise ValueError("ball cap 1200")
    vertices = sorted(distance, key=lambda v: (distance[v], v))
    ids = {v: i for i, v in enumerate(vertices)}
    edges = []
    for u in vertices:
        edges.append(sorted(ids[v] for j, delta in adj[u[0]]
                            if (v := (j, *(u[k+1]+delta[k] for k in range(3)))) in ids))
    return edges, [distance[v] for v in vertices], [list(v) for v in vertices]

def refine(a, da, b, db, mapping=None):
    marks_a, marks_b = {}, {}
    for k, (u, v) in enumerate((mapping or {}).items(), 1):
        marks_a[u] = k; marks_b[v] = k
    labels = [(da[i], len(e), marks_a.get(i, 0)) for i, e in enumerate(a)]
    labels += [(db[i], len(e), marks_b.get(i, 0)) for i, e in enumerate(b)]
    edges = a + [[j+len(a) for j in e] for e in b]
    classes = {s: i for i, s in enumerate(sorted(set(labels)))}
    colors = [classes[s] for s in labels]
    for iteration in range(len(edges)+1):
        ha, hb = Counter(colors[:len(a)]), Counter(colors[len(a):])
        if ha != hb:
            return colors[:len(a)], colors[len(a):], iteration, ha, hb
        signatures = [(colors[i], tuple(sorted(colors[j] for j in e)))
                      for i, e in enumerate(edges)]
        classes = {s: i for i, s in enumerate(sorted(set(signatures)))}
        new = [classes[s] for s in signatures]
        if len(set(new)) == len(set(colors)):
            return new[:len(a)], new[len(a):], None, ha, hb
        colors = new
    raise AssertionError('refinement did not stabilize')

def isomorphism(a, da, b, db):
    if len(a) != len(b):
        return None, 0
    sa, sb = list(map(set, a)), list(map(set, b))
    mapping, used, nodes = {0: 0}, {0}, 0

    def search():
        nonlocal nodes
        nodes += 1
        ca, cb, difference, _, _ = refine(a, da, b, db, mapping)
        if difference is not None:
            return None
        if len(mapping) == len(a):
            return [mapping[i] for i in range(len(a))]
        options = []
        for u in range(len(a)):
            if u in mapping:
                continue
            candidates = [v for v in range(len(b)) if v not in used and ca[u] == cb[v]
                          and all((k in sa[u]) == (w in sb[v]) for k, w in mapping.items())]
            if not candidates:
                return None
            options.append((len(candidates), -sum(k in sa[u] for k in mapping), u, candidates))
        _, _, u, candidates = min(options)
        for v in candidates:
            mapping[u] = v; used.add(v)
            result = search()
            if result is not None:
                return result
            del mapping[u]; used.remove(v)
        return None

    return search(), nodes

def invariants(edges, distances):
    degrees = [len(x) for x in edges]
    profile = Counter((distances[i], degrees[i]) for i in range(len(edges)))
    walks, current = [], [int(i == 0) for i in range(len(edges))]
    for k in range(1, 17):
        current = [sum(current[j] for j in e) for e in edges]
        walks.append(current[0])
    traces = [0] * 12
    for i in range(len(edges)):
        weights = [int(j == i) for j in range(len(edges))]
        for k in range(12):
            weights = [sum(weights[j] for j in nbrs) for nbrs in edges]
            traces[k] += weights[i]
    return {'distance_degree_counts': [[list(k), v] for k, v in sorted(profile.items())],
            'root_closed_walks_lengths_1_to_16': walks,
            'all_closed_walks_lengths_1_to_12': traces}
