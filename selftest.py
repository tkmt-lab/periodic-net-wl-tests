#!/usr/bin/env python3
"""Real CLI rejection checks and a small synthetic exhaustive-proof test.

Requires an already verified core work directory. All copied RCSR-derived
fixtures stay in the caller's runtime directory, never in the package.
"""
import argparse
import contextlib
import copy
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from unittest.mock import patch

import algorithm
import finite_check
import refutation
import source_io
import suite


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verified-work', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.verified_work = args.verified_work.resolve()
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=False)
    rows = []
    core = source_io.read(args.verified_work / 'verification.json')
    assert core['status'] == 'PASS' and core['case_counts'] == {'PASS': 6}

    def exercise(label, expected_code, mutation=None, seconds=600):
        work = args.out / label
        shutil.copytree(args.verified_work, work)
        if mutation:
            mutation(work)
        tick = time.monotonic()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = suite.main(['check', '--work', str(work), '--scope', 'core', '--seconds', str(seconds)])
        assert code == expected_code, (label, code, expected_code)
        rows.append({'test': label, 'expected_exit': expected_code, 'actual_exit': code, 'seconds': time.monotonic() - tick})

    def edit_certificate(work, edit, name='2031-V1__2032-V1'):
        path = work / 'certificates' / (name + '.json')
        value = source_io.read(path)
        edit(value)
        source_io.write(path, value)

    exercise('baseline-fresh-check', 0)
    exercise('source-byte-corruption', 2, lambda w: (w / 'inputs/3dall.txt').write_bytes((w / 'inputs/3dall.txt').read_bytes() + b'\n'))
    exercise('missing-proof-ignores-old-PASS', 3, lambda w: (w / 'certificates/565-V1__566-V1.json').unlink())
    exercise('bad-mapping', 1, lambda w: edit_certificate(w, lambda c: c['isomorphic']['mapping_a_to_b'].__setitem__(1, 0)))
    exercise('bad-invariant', 1, lambda w: edit_certificate(w, lambda c: c['proof'].__setitem__('count_a', c['proof']['count_a'] + 1)))
    exercise('bad-WL', 1, lambda w: edit_certificate(w, lambda c: c['WL_witness'][0][0].__setitem__(0, 999999)))
    exercise('unknown-schema', 1, lambda w: edit_certificate(w, lambda c: c.__setitem__('schema', 'unknown-v999')))
    def bad_graph(work):
        path = work / 'graphs/fly.json'
        graph = source_io.read(path)
        graph['adjacency'][0].pop()
        source_io.write(path, graph)
    exercise('bad-graph', 1, bad_graph)
    exercise('wall-cap-is-unverified', 3, seconds=1e-9)
    import source_check
    with patch.object(source_check, 'verify', side_effect=MemoryError('simulated; no actual allocation')):
        exercise('memory-unavailable-is-unverified', 3)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        code = suite.main(['check', '--work', str(args.verified_work), '--report', str(args.verified_work / 'inputs/3dall.txt')])
    assert code == 2
    rows.append({'test': 'report-cannot-overwrite-input', 'actual_exit': code})

    # Connected rooted graphs: cone over C6 versus cone over two C3s.
    # Stable 1-WL is equal; complete IR must refute all candidate images.
    def cone(triangles):
        adj = [set(range(1, 7))] + [{0} for _ in range(6)]
        blocks = [[1, 2, 3], [4, 5, 6]] if triangles else [list(range(1, 7))]
        for block in blocks:
            for i, u in enumerate(block):
                v = block[(i + 1) % len(block)]
                adj[u].add(v)
                adj[v].add(u)
        return adj
    left, right = cone(False), cone(True)
    distances = [0] + [1] * 6
    assert finite_check.wl((list(range(7)), distances, left), (list(range(7)), distances, right)) is None
    mapping, tree, count = refutation.isomorphism_or_refutation(left, distances, right, distances, algorithm.refine)
    assert mapping is None and tree['children']
    finite_check.check_refutation(tree, (list(range(7)), distances, left), (list(range(7)), distances, right))
    corrupt = copy.deepcopy(tree)
    corrupt['children'].pop()
    try:
        finite_check.check_refutation(corrupt, (list(range(7)), distances, left), (list(range(7)), distances, right))
    except ValueError:
        rows.append({'test': 'IR-missing-branch', 'status': 'rejected', 'complete_tree_nodes': count})
    else:
        raise AssertionError('incomplete IR proof accepted')

    local = args.verified_work / 'inputs/3dall.txt'
    offline = args.out / 'offline-empty-work'
    with patch.object(source_io, 'urlopen', side_effect=AssertionError('network must not be used')):
        with contextlib.redirect_stdout(io.StringIO()):
            code = suite.main(['run', '--work', str(offline), '--scope', 'core', '--source', str(local), '--seconds', '600'])
    assert code == 0
    rows.append({'test': 'local-source-entire-run-network-disabled', 'actual_exit': code})

    # Copy exactly the package manifest's files, no old repo data/helper paths.
    relocated = args.out / 'relocated-package'
    relocated.mkdir()
    manifest = source_io.read(suite.ROOT / 'manifest.json')
    for name in list(manifest['files']) + ['manifest.json']:
        destination = relocated / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(suite.ROOT / name, destination)
    process = subprocess.run([sys.executable, '-B', str(relocated / 'suite.py'), 'run', '--work', str(args.out / 'relocated-work'),
                              '--scope', 'main', '--seconds', '600'],
                             cwd=relocated, capture_output=True, text=True, timeout=650)
    assert process.returncode == 0, process.stderr + process.stdout
    relocated_verdict = source_io.read(args.out / 'relocated-work/verification.json')
    assert relocated_verdict['case_counts'] == {'PASS': 76}
    rows.append({'test': 'relocated-package-fresh-fixed-URL-main76', 'actual_exit': process.returncode,
                 'summary': source_io.read(args.out / 'relocated-work/run-summary-run.json')})
    (relocated / 'expected.json').write_text('{}\n')
    process = subprocess.run([sys.executable, '-B', str(relocated / 'suite.py'), 'check', '--work', str(args.out / 'relocated-work')],
                             cwd=relocated, capture_output=True, text=True, timeout=30)
    assert process.returncode == 2
    rows.append({'test': 'tampered-bundle-hash', 'actual_exit': process.returncode})
    source_io.write(args.out / 'selftest.json', {'status': 'PASS', 'tests': rows,
                    'scope': 'same-agent tests of source, proof, CLI, offline path and relocation; not external independent review'})
    print(json.dumps({'status': 'PASS', 'tests': len(rows)}), flush=True)


if __name__ == '__main__':
    main()
