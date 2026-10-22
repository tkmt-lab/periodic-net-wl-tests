"""Pinned inputs and runtime-only record parsing. No RCSR data are bundled."""
import copy
import hashlib
import json
import re
from fractions import Fraction as Q
from pathlib import Path
from urllib.request import Request, urlopen

RCSR_COMMIT = '580316c9352b747f5c309a93acd21a3a2b4034a3'
SOURCES = {
    '3dall.txt': {'url': f'https://raw.githubusercontent.com/rcsr-net/RCSR-content/{RCSR_COMMIT}/public/data/3dall.txt',
                  'sha256': 'c143e8aa98a94fbec9f7ff30571269494b6e42895e2b57b219a40512801d2743', 'bytes': 4547394},
    'RCSRnets.arc': {'url': f'https://raw.githubusercontent.com/rcsr-net/RCSR-content/{RCSR_COMMIT}/public/downloads/RCSRnets.arc',
                    'sha256': '8a18b5c2307c0383524a54a74b7499cfa3222a12e23743dd95d6eed07b6ebd6f', 'bytes': 1754079},
}
SG_SHA256 = '19f54403accd6b0feeff0f4c14a9f9004c5d8ac25186b43ee1eb1eaebb23dad9'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + '\n')
    temporary.replace(path)


def validate_input(path, name):
    path = Path(path)
    spec = SOURCES[name]
    need(path.is_file(), f'missing input: {name}')
    need(path.stat().st_size == spec['bytes'] and digest(path) == spec['sha256'], f'fixed input hash mismatch: {name}')
    return path


def fetch(work, name, local=None):
    destination = Path(work) / 'inputs' / name
    spec = SOURCES[name]
    if local is None and destination.exists():
        validate_input(destination, name)
        return {'input': name, 'method': 'existing verified file', 'sha256': spec['sha256']}
    if local is not None:
        data = validate_input(local, name).read_bytes()
        method = 'caller-supplied file; no network'
    else:
        with urlopen(Request(spec['url'], headers={'User-Agent': 'periodic-net-wl-tests/1.0.0'}), timeout=30) as response:
            data = response.read(spec['bytes'] + 1)
        method = 'fixed URL GET'
    need(len(data) == spec['bytes'] and hashlib.sha256(data).hexdigest() == spec['sha256'], f'fixed input hash mismatch: {name}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_name(name + '.tmp')
    tmp.write_bytes(data)
    tmp.replace(destination)
    return {'input': name, 'method': method, 'sha256': spec['sha256'], 'bytes': len(data)}


def spacegroups(path):
    need(digest(path) == SG_SHA256, 'Gavrog table hash mismatch')
    lines = Path(path).read_text().splitlines()
    result = {}
    for i, line in enumerate(lines):
        if line and line[0] not in ' #\t' and line.endswith(' x,y,z'):
            ops, j = [], i + 1
            while j < len(lines) and lines[j].startswith(' '):
                ops.append(lines[j].strip())
                j += 1
            result[line.split()[0]] = ops
    return result


def records(path, names):
    """Adapted from the previous lab inventory parser; only requested nets."""
    raw = validate_input(path, '3dall.txt').read_bytes()
    out = {}
    for block in re.split(r'(?m)^[ \t]*start[ \t]*\n', raw.decode().replace('\r\n', '\n')):
        lines = [s.strip() for s in block.strip('\n').splitlines()]
        if len(lines) < 3 or lines[1] not in names:
            continue
        rid, name, kind = int(lines[0]), lines[1], lines[2]
        idx = next(i - 1 for i, s in enumerate(lines) if re.fullmatch(r'[+-]?[\d.]+(?:\s+[+-]?[\d.]+){5,}', s))
        cell = lines[idx + 1].split()[:6]
        vertices, centers = [], []
        pos, nv = idx + 3, int(lines[idx + 2])
        for prefix, count in [('V', nv), ('E', None)]:
            if prefix == 'E':
                count = int(lines[pos])
                pos += 1
            for k in range(count):
                coordinate = lines[pos + 1].split()
                need(len(coordinate) == 3, 'coordinate field count')
                item = {'label': prefix + str(k + 1), 'degree': int(lines[pos].split()[-1]),
                        'coordinate': coordinate, 'multiplicity': int(re.match(r'\d+', lines[pos + 3]).group())}
                (vertices if prefix == 'V' else centers).append(item)
                pos += 6 if prefix == 'V' else 5
        sequences = [list(map(int, s.split())) for s in lines if re.fullmatch(r'(?:\d+\s+){10}\d+', s)]
        need(len(sequences) == len(vertices), 'CS to source vertex correspondence')
        for vertex, seq in zip(vertices, sequences):
            need(vertex['degree'] == seq[0] and seq[10] == 1 + sum(seq[:10]), 'source CS order or cumulative count')
            vertex['cs10'] = seq[:10]
        need(name not in out, 'duplicate source net name')
        out[name] = {'record_id': rid, 'name': name, 'embed_type': kind, 'spacegroup': lines[idx],
                     'cell': cell, 'vertices': vertices, 'edge_centers': centers,
                     'estimated_quotient_vertices': sum(v['multiplicity'] for v in vertices),
                     'record_sha256': hashlib.sha256(block.strip('\n').encode()).hexdigest()}
    need(set(out) == set(names), 'requested net absent from fixed input')
    return out


def settings(rec, groups):
    key = rec['spacegroup'].split()[0].replace('(', '').replace(')', '')
    if key in groups:
        return [key]
    if key + ':H' in groups and list(map(Q, rec['cell'][3:])) == [90, 90, 120]:
        return [key + ':H']
    return sorted(k for k in groups if k.split(':')[0] == key and k.endswith((':1', ':2')))


def normalized(rec, denominator):
    result = copy.deepcopy(rec)
    if denominator:
        for row in result['vertices'] + result['edge_centers']:
            for k, text in enumerate(row['coordinate']):
                if '.' not in text:
                    continue
                value = Q(text)
                eps = Q(1, 2 * 10 ** len(text.split('.')[1]))
                candidates = set()
                for d in range(1, denominator + 1):
                    n = (value * d).numerator // (value * d).denominator
                    for numerator in [n, n + 1]:
                        q = Q(numerator, d)
                        if abs(q - value) <= eps:
                            candidates.add(q)
                if len(candidates) == 1:
                    row['coordinate'][k] = str(candidates.pop())
    return result


def checked_effective(raw, model, groups):
    """Re-derive normalized coordinates by another denominator enumeration."""
    dmax = model['denominator']
    need(type(dmax) is int and dmax in [0, 12, 48], 'unknown coordinate model')
    need(model['setting'] in settings(raw, groups), 'setting not an explicit pinned-table choice')
    out = copy.deepcopy(raw)
    if dmax:
        for row in out['vertices'] + out['edge_centers']:
            for k, text in enumerate(row['coordinate']):
                if '.' not in text:
                    continue
                value = Q(text)
                eps = Q(1, 2 * 10 ** len(text.split('.')[1]))
                choices = set()
                for d in range(1, dmax + 1):
                    lo, hi = (value - eps) * d, (value + eps) * d
                    low = -((-lo.numerator) // lo.denominator)
                    high = hi.numerator // hi.denominator
                    choices.update(Q(n, d) for n in range(low, high + 1))
                if len(choices) == 1:
                    row['coordinate'][k] = str(choices.pop())
    out['spacegroup_table_key'] = model['setting']
    return out


def arc_catalogue(path):
    text = validate_input(path, 'RCSRnets.arc').read_text()
    out = {}
    for block in re.split(r'(?im)^end\s*$', text):
        ids = re.findall(r'(?im)^id\s+(\S+)', block)
        keys = re.findall(r'(?im)^key\s+(.+)', block)
        if len(ids) == len(keys) == 1:
            key = list(map(int, keys[0].split()))
            if key[0] == 3:
                # An unrelated duplicate must not invalidate all other records.
                # Keep an ambiguous name unavailable; never pick the last key.
                if ids[0] in out and out[ids[0]] != key:
                    out[ids[0]] = None
                else:
                    out[ids[0]] = key
    return out
