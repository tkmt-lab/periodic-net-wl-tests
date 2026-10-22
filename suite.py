#!/usr/bin/env python3
"""Rooted periodic-net identification tests: fetch, build and check (Python standard library only)."""
import argparse
import contextlib
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time
from urllib.error import HTTPError, URLError

from source_io import digest, fetch, need, read, write

ROOT = Path(__file__).resolve().parent


def peak_mb():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value / (1024 ** 2 if sys.platform == 'darwin' else 1024)


class Budget:
    def __init__(self, seconds, memory_mb):
        need(0 < seconds <= 18000 and 0 < memory_mb <= 3072, 'budget outside supported limits')
        self.deadline = time.monotonic() + seconds
        self.memory_mb = memory_mb

    @contextlib.contextmanager
    def limit(self, seconds):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0 or peak_mb() > self.memory_mb:
            raise TimeoutError('wall or peak-memory budget reached')
        def expired(signum, frame):
            raise TimeoutError('per-item or command wall cap')
        previous = signal.signal(signal.SIGALRM, expired)
        signal.setitimer(signal.ITIMER_REAL, min(seconds, remaining))
        try:
            yield
            if peak_mb() > self.memory_mb:
                raise TimeoutError('peak-memory budget reached')
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous)


def validate_bundle():
    manifest = read(ROOT / 'manifest.json')
    need(manifest['schema'] == 'R019-suite-manifest-v1', 'unknown bundle manifest')
    for name, entry in manifest['files'].items():
        p = ROOT / name
        need(p.resolve().is_relative_to(ROOT) and p.is_file(), 'missing/outside bundle file')
        need(p.stat().st_size == entry['bytes'] and digest(p) == entry['sha256'], 'bundle hash mismatch: ' + name)


def selection(scope):
    data = read(ROOT / 'expected.json')
    need(data['schema'] == 'R019-suite-expected-v1', 'unknown expectation schema')
    import re
    ids = set()
    cases = []
    for c in data['cases']:
        need(re.fullmatch(r'\d+-V\d+__\d+-V\d+', c['id']) and c['id'] not in ids, 'case id/duplicate')
        ids.add(c['id'])
        need(type(c['r_min']) is int and type(c['r_WL']) is int and 1 <= c['r_min'] <= c['r_WL'] <= 8, 'expected radius domain')
        for side in ['a', 'b']:
            need(re.fullmatch(r'[a-z0-9*+_-]+', c[side]['net']) and re.fullmatch(r'V\d+', c[side]['orbit']), 'net/root syntax')
        if scope == 'all' or (scope == 'core' and c['core']) or (scope == 'main' and c['main']):
            cases.append(c)
    need(cases, 'empty scope')
    return cases


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['fetch', 'build', 'check', 'run'])
    parser.add_argument('--work', type=Path, required=True, help='runtime-only directory, never the bundle root')
    parser.add_argument('--scope', choices=['core', 'main', 'all'], default='core')
    parser.add_argument('--source', type=Path, help='existing fixed 3dall.txt; fetch/run uses no network for this file')
    parser.add_argument('--with-arc', action='store_true', help='explicit optional fixed ARC input, separate source assumption')
    parser.add_argument('--arc-source', type=Path, help='existing fixed ARC input; requires --with-arc')
    parser.add_argument('--report', type=Path, help='check verdict output; defaults to WORK/verification.json')
    parser.add_argument('--seconds', type=float, default=1800)
    parser.add_argument('--memory-mb', type=float, default=3072)
    args = parser.parse_args(argv)
    started = time.monotonic()
    code = 2
    try:
        need(not sys.flags.optimize, 'do not use Python -O; inherited verifiers contain assertions')
        need(hasattr(signal, 'SIGALRM'), 'Unix SIGALRM required; Windows unsupported')
        need(args.work.resolve() != ROOT, 'work directory cannot be the bundle root')
        if args.report is not None:
            target, work = args.report.resolve(), args.work.resolve()
            need(target.is_relative_to(work), 'report output must stay inside the work directory')
            need(not any(target.is_relative_to(work / name) for name in ['inputs', 'graphs', 'certificates']),
                 'report output must not overwrite runtime input or evidence')
        need(args.with_arc or args.arc_source is None, '--arc-source requires --with-arc')
        need(args.action in ['fetch', 'run'] or (args.source is None and args.arc_source is None), '--source/--arc-source apply to fetch or run')
        validate_bundle()
        budget = Budget(args.seconds, args.memory_mb)
        cases = selection(args.scope)
        sys.setrecursionlimit(5000)
        if hasattr(os, 'nice'):
            os.nice(15)
        if args.action in ['fetch', 'run']:
            acquisitions = [fetch(args.work, '3dall.txt', args.source)]
            if args.with_arc:
                acquisitions.append(fetch(args.work, 'RCSRnets.arc', args.arc_source))
            write(args.work / 'acquisition.json', acquisitions)
        build_code = 0
        if args.action in ['build', 'run']:
            need(not (args.work / 'graphs').exists() and not (args.work / 'certificates').exists(), 'build requires a fresh work directory (inputs alone may exist)')
            from build_run import build
            build_code = build(args.work, cases, ROOT, budget, args.with_arc)
        if args.action in ['check', 'run']:
            from verify_run import verify
            code = verify(args.work, cases, ROOT, budget, args.with_arc, args.report)
            if code == 0 and build_code:
                code = build_code
        else:
            code = build_code
    except (HTTPError, URLError) as error:
        code = 4
        print('ACQUISITION ERROR', str(error), file=sys.stderr)
    except (TimeoutError, MemoryError, RecursionError) as error:
        code = 3
        print('UNVERIFIED', str(error), file=sys.stderr)
    except (ValueError, KeyError, TypeError, IndexError, OSError, AssertionError) as error:
        code = 2
        print('INPUT/CONFIG ERROR', str(error), file=sys.stderr)
    summary = {'action': args.action, 'scope': args.scope, 'exit_code': code,
               'elapsed_seconds': round(time.monotonic() - started, 6), 'peak_rss_mb': round(peak_mb(), 3),
               'scientific_processes': 1, 'external_cost_usd': 0,
               'memory_guard': 'bounded quotient/ball/CS/proof sizes; peak RSS checked between bounded items, not an OS hard RSS limit'}
    if args.work.is_dir():
        write(args.work / ('run-summary-' + args.action + '.json'), summary)
    print(json.dumps(summary), flush=True)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
