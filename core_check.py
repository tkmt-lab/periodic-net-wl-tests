"""Verifier primitives; no producer imports."""
import ast
from fractions import Fraction
from collections import Counter

def need(condition, message):
    if not condition:
        raise ValueError(message)

def numeric(node, values):
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return Fraction(node.value)
    if isinstance(node, ast.Name) and node.id in values:
        return values[node.id]
    if isinstance(node, ast.UnaryOp):
        v = numeric(node.operand, values)
        if isinstance(node.op, ast.USub):
            return -v
        if isinstance(node.op, ast.UAdd):
            return v
    if isinstance(node, ast.BinOp):
        a, b = numeric(node.left, values), numeric(node.right, values)
        if isinstance(node.op, ast.Add):
            return a+b
        if isinstance(node.op, ast.Sub):
            return a-b
        if isinstance(node.op, ast.Div):
            return a/b
    raise ValueError('unsupported affine expression')

def independent_ball(adj, root, radius):
    # Iterated closed-neighbourhood sets, rather than producer's queue BFS.
    found, distances = {(root, 0, 0, 0)}, {(root, 0, 0, 0): 0}
    for depth in range(1, radius+1):
        expanded = found | {(j, x+u, y+v, z+w) for i, x, y, z in found
                            for j, u, v, w in adj[i]}
        distances.update({p: depth for p in expanded-found})
        found = expanded
        need(len(found)<=1200,"ball cap 1200")
    vertices = sorted(found, key=lambda p: (distances[p], p))
    edges = [set() for p in vertices]
    # Check each pair using the quotient edge relation; no producer edge loop.
    for i, p in enumerate(vertices):
        for j in range(i+1, len(vertices)):
            q = vertices[j]
            if (q[0], q[1]-p[1], q[2]-p[2], q[3]-p[3]) in adj[p[0]]:
                edges[i].add(j); edges[j].add(i)
    return vertices, [distances[p] for p in vertices], edges

def match_ball_file(saved, data):
    vertices, distances, edges = data
    need(saved['root'] == 0, 'unexpected root index')
    need(saved['vertices'] == list(map(list, vertices)), 'ball vertices differ')
    need(saved['distance'] == distances, 'ball distances differ')
    need(saved['adjacency'] == [sorted(row) for row in edges], 'ball induced edges differ')

def check_mapping(mapping, a, b):
    need(len(mapping) == len(a) == len(b), 'mapping size')
    need(sorted(mapping) == list(range(len(b))), 'mapping not a bijection')
    need(mapping[0] == 0, 'root not fixed')
    for i in range(len(a)):
        for j in range(len(a)):
            need((j in a[i]) == (mapping[j] in b[mapping[i]]), 'edge/nonedge not preserved')

def multiply(a, b):
    n = len(a); out = [[0]*n for row in a]
    for i in range(n):
        for k, value in enumerate(a[i]):
            if value:
                for j, other in enumerate(b[k]):
                    if other:
                        out[i][j] += value*other
    return out

def power(edges, exponent):
    n = len(edges)
    result = [[int(i == j) for j in range(n)] for i in range(n)]
    matrix = [[int(j in edges[i]) for j in range(n)] for i in range(n)]
    while exponent:
        if exponent & 1:
            result = multiply(result, matrix)
        exponent //= 2
        if exponent:
            matrix = multiply(matrix, matrix)
    return result

def walk_invariant(edges, proof):
    length = proof['walk_length']
    need(length % 2 == 0 and 2 <= length <= 16, 'unsupported certificate walk length')
    half = power(edges, length//2)
    # For a symmetric A, (A^(2m))[v,v] = sum_j (A^m[v,j])^2.
    # Summing over v gives trace(A^(2m)) = ||A^m||_F^2.
    if proof['method'] == 'root-closed-walk-count':
        return sum(x*x for x in half[0])
    need(proof['method'] == 'closed-walk-trace', 'unknown proof method')
    return sum(x*x for row in half for x in row)
