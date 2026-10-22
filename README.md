# Rooted periodic-net identification tests (RCSR, 1-WL)

Test cases built from crystal nets in a pinned version of the RCSR database. Each case is a pair of nets
with a chosen root vertex in each. For radius r, the rooted ball is the finite subgraph induced by all vertices
within r edges of the root. Each case records two radii:

- `r_min`: the smallest r at which the two rooted balls are not isomorphic;
- `r_WL`: the smallest r at which 1-WL colour refinement, run to a stable partition, tells the two balls apart.

There are 99 cases. In 97 of them `r_WL` is larger than `r_min`: the balls already differ, but colour refinement does not
yet see it. The largest gap is 4 (tsa V1 / tsg V3: `r_min` = 4, `r_WL` = 8).

The tests are for people who test graph-isomorphism heuristics or the expressive power of message passing
on graphs built from RCSR net records. The input is the bare graph: vertices, edges and a root. Methods
that also use atomic species, coordinates, distances, angles or periodic labels receive different input, and
these tests say nothing about them.

The repository contains code and expected values only. The RCSR file is downloaded by the user and checked
against a fixed SHA-256; graphs, balls and certificates are built in a local work folder.

## Quick start

Python 3.11 or later, standard library only, on macOS or Linux (the time limits use `SIGALRM`, so Windows is
not supported). Do not run with `python -O`: the checks use `assert`.

From the repository root:

```sh
python3 -B suite.py run --work work/core --scope core   # 6 cases, about 1 s plus the 4.5 MB download
python3 -B suite.py run --work work/main --scope main   # 76 cases, about 20 s
python3 -B selftest.py --verified-work work/core --out work/selftest   # 15 tests, about 25 s
```

Success is exit code 0 and a last line with `"exit_code": 0`; `work/core/verification.json` then has
`"status": "PASS"` and `"case_counts": {"PASS": 6}`. Times were measured on an Apple-silicon laptop; peak memory
stayed below 100 MB.

`run` downloads `3dall.txt` from the pinned URL into `WORK/inputs/`, builds the graphs and certificates, and
checks them. The `--work` folder of `run` or `build` must be new or contain only `inputs/`, and the `--out`
folder of the self-test must not exist. To use a copy of `3dall.txt` you already have, without network access:

```sh
python3 -B suite.py run --work work/main-local --scope main --source /absolute/path/to/3dall.txt
```

The steps can also be run separately: `fetch`, `build`, then `check`. To re-check an existing work folder, run
`python3 -B suite.py check --work work/core --scope core`. `check` uses no network; it reads the work folder
and the repository files (`expected.json`, `manifest.json`, the Gavrog table), recomputes everything from the
inputs and certificates, and ignores earlier verdicts.

The self-test needs network access: one of its runs downloads the input again. CI runs the three commands
above and `python3 -B check_claims.py`, which checks the fields and file hashes in `claims.json`.

## Scopes

| Scope | Cases | Content |
|---|---:|---|
| `core` | 6 | the six cases below, each also computed by a separate implementation |
| `main` | 76 | the six core cases and 70 further cases with `r_WL` > `r_min`; every graph is built from coordinates |
| `all` | 99 | `main` and 23 further cases; some of them need `RCSRnets.arc` (`--with-arc`) |

Core cases (net and RCSR vertex label of each root):

| Left root | Right root | `r_min` | `r_WL` | Non-isomorphism at `r_min` shown by |
|---|---|---:|---:|---|
| sxb V1 | sxc V1 | 2 | 2 | 1-WL |
| fly V2 | ylf V2 | 4 | 4 | 1-WL |
| fly V1 | ylf V1 | 4 | 5 | number of closed walks of length 10 in the ball, trace(A^10): 2,816,008 vs 2,816,168 |
| ben V2 | cat V2 | 3 | 6 | exhaustive individualization-refinement tree |
| tsa V1 | tsg V3 | 4 | 8 | exhaustive individualization-refinement tree |
| acl V1 | nih V1 | 1 | 2 | exhaustive individualization-refinement tree |

The `all` scope:

```sh
python3 -B suite.py run --work work/all --scope all --with-arc
```

`--with-arc` downloads `RCSRnets.arc` from the same pinned commit. For each net, coordinates are tried first.
If they do not give a graph (see below), the ARC entry of the same name is used. In our runs 10 of the 99
cases used a graph built from the ARC file. The ARC graph must have the same coordination sequences to 10
shells as the RCSR record, with the same weights. An RCSR orbit is used as a root only if its 10-shell sequence
differs from those of the other orbits of the record; the root is then the first ARC vertex with that sequence.
That this vertex lies in the orbit RCSR labels V1, V2, ... is an assumption, not something the code proves.
Without `--with-arc`, cases that need the ARC file end as `UNVERIFIED`.

All expected values are in [expected.json](expected.json). Case identifiers have the form
`<record>-V<k>__<record>-V<k>`, with RCSR record numbers in `3dall.txt`.

## Definitions

- **Net.** The periodic graph built from one RCSR record (or, with `--with-arc`, from the ARC entry; see above).
  From coordinates: the vertices of the unit cell are generated with the space group from the bundled Gavrog
  table. Edges are found either as the nearest neighbours of each vertex up to its listed coordination number
  (net types 1*), or as the vertex pair nearest to each listed edge midpoint, which must match the midpoint
  within the rounding of the printed coordinates. In both cases the nearest candidates must be separated from
  the next ones, and the graph must reproduce the record's coordination sequences. Graphs are simple and
  undirected and carry no labels.
- **Root.** A representative of the listed vertex orbit (V1, V2, ...) of the record.
- **Ball** `B(v, r)`: all vertices at graph distance at most r from v, and every edge between them.
- **Isomorphism** of rooted balls: a bijection of vertices preserving edges and mapping root to root. Vertex
  labels, species, coordinates and symmetry are not required to be preserved.
- **1-WL.** Initial colour of each vertex: (distance from the root, degree inside the ball). Both balls are
  refined together with the same colour names until the partition is stable. The balls are told apart when
  some colour has different counts in the two balls. `r_WL` is a ball radius, not a number of refinement
  rounds.

## Coordinates and space groups

The source models were fixed before the radii were compared. The printed decimals in the record are first
used as exact rationals. If the record's checks fail (orbit sizes, coordination numbers, edge midpoints, a
bound on how far edges reach, coordination sequence to 10 shells), the printed coordinates are tried again
with each entry replaced by a rational of denominator at most 12 within half a unit of the last printed digit,
when exactly one such rational exists (otherwise the entry is kept), and then the same with denominator at
most 48. Cell lengths stay as printed. Space-group settings are tried only as the exact symbol, an explicit
hexagonal setting, or the `:1`/`:2` choices of the same symbol; if two admissible settings give different
graphs, the coordinate route is rejected (and the ARC file is tried if `--with-arc` is given). The chosen
model is written into each graph file.

This defines the graphs used here. It does not show that these are the coordinates the RCSR authors intended.

## What `check` verifies

The checker does not import the generator. For each case it:

1. checks the hash of `3dall.txt` (and the ARC file, if used) and of the Gavrog table, and rebuilds each net's
   source model from the record;
2. rebuilds the balls with a separate algorithm and checks a complete root-preserving isomorphism at radius
   `r_min` − 1;
3. checks the certificate of non-isomorphism at `r_min`: a 1-WL colour sequence, an integer count of closed
   walks (with a different matrix method from the generator), or an individualization-refinement tree that
   covers every branch;
4. recomputes stable 1-WL at every radius from 1 to `r_WL`;
5. compares the results with `expected.json`.

Results go to `WORK/verification.json` (`PASS`, `FAIL` or `UNVERIFIED` per case and per net) and
`WORK/run-summary-<action>.json`. Exit codes:

| Code | Meaning |
|---:|---|
| 0 | for `check` and `run`: every case passed. For `fetch` and `build`: the step finished |
| 1 | a graph, certificate or value disagrees (`FAIL`) |
| 2 | invalid input, hash mismatch, manifest mismatch or bad arguments |
| 3 | a case could not be decided: missing graph or certificate, time limit, memory or recursion limit (`UNVERIFIED`) |
| 4 | download error; the tool does not switch to another URL or version |

Default limits: 1800 s per command, 90 s per net or case, 1200 vertices per ball, 3072 MB peak RSS. The
memory limit is checked between items; it is not enforced by the operating system. A graph, ball or
certificate that `check` finds over a size cap counts as `FAIL`.

`selftest.py` has 12 rejection tests: it corrupts the input bytes, a graph, an isomorphism, a walk count, a
WL sequence, a schema field, a branch of a refutation tree and `expected.json`, removes a certificate, sets an
impossible time limit, simulates a memory error, and points the report at the input file; each must give the
documented exit code. Three further runs must pass: a re-check of the core folder, a run without network from
a local file, and a run of `main` from a copy of only the files in [manifest.json](manifest.json). The
refutation-tree test uses two small hand-made graphs, not RCSR data.

## What was checked independently

The six `core` cases were computed by a separate implementation (Gemmi 0.7.5 and NetworkX 3.7 with the
standard library), written by a separate team of AI agents that had not seen these results. That team shared the
problem definition, the RCSR data and a description of the coordinate handling, and built tsa/tsg from coordinates
without the ARC file. It found the same `r_min` and `r_WL` in all six, and the same trace(A^10) values for
fly V1 / ylf V1. Its 1-WL starts with only the root coloured. The stable partition is the same as with the
initial colours above, because refinement from the root recovers distances and degrees; for ben/cat, tsa/tsg
and acl/nih the team also ran both versions and got the same results.

The other 70 cases of `main` and 93 of `all` were checked only by this package's checker. It is separate code
from the generator, but written by the same team, and it shares the parser and definitions. The values come
from our earlier computations on the same pinned data.

Details: [VERIFICATION-RECORD.md](VERIFICATION-RECORD.md). Claims and their evidence: [claims.json](claims.json).

## What is not claimed

- Nothing about graph neural networks in general. 1-WL bounds what plain message passing can distinguish
  with these initial features on these finite balls; no model was trained or tested.
- A ball radius is not a number of GNN layers, and `r_WL` − `r_min` is not a count of missing layers.
- Nothing about models that use species, coordinates, distances, angles or periodic labels.
- No maximum over the RCSR database. The 99 cases are a selection from a larger table of root pairs whose
  coordination sequences agree for the first 10 shells (agreement beyond 10 shells was not checked). Four
  further pairs with `r_WL` > 8 are not included, and many pairs were not resolved.
- No claim that the graphs are the structures the RCSR authors intended, beyond the source models above, or
  that two nets with isomorphic balls up to some radius are the same net.
- No priority. The idea of comparing growing shells as graphs, and WL counterexamples for periodic point
  clouds, come from the work cited below. No new isomorphism algorithm is claimed. Our search for earlier
  tables of this kind was limited: the supplementary files of Blatov and Proserpio (2009), the ToposPro TTD
  collections and the later literature were not checked in full.
- No human expert review, no formal proof.

## Data source

RCSR-content, commit [`580316c9352b747f5c309a93acd21a3a2b4034a3`](https://github.com/rcsr-net/RCSR-content/tree/580316c9352b747f5c309a93acd21a3a2b4034a3)
(28 January 2026):

| File | Bytes | SHA-256 |
|---|---:|---|
| `public/data/3dall.txt` | 4,547,394 | `c143e8aa98a94fbec9f7ff30571269494b6e42895e2b57b219a40512801d2743` |
| `public/downloads/RCSRnets.arc` (only `--with-arc`) | 1,754,079 | `8a18b5c2307c0383524a54a74b7499cfa3222a12e23743dd95d6eed07b6ebd6f` |

We found no licence file or redistribution terms in that repository at the pinned commit, so no RCSR data,
and no graphs, balls or figures derived from them, are included here. The user downloads the files. Whether
and how the downloaded data may be used is for the user to check; downloading does not settle it.

`third-party/sgtable.data` is Olaf Delgado-Friedrichs's space-group table from Gavrog (Apache-2.0), unchanged;
see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Research and verification

The author is Tatsuhiko Takimoto, Independent researcher. AI systems wrote the code, ran the computations,
carried out the independent check of the core cases, organized the literature and drafted this text; the
author is responsible for the claims and their stated scope.

## Built on prior work

- The Reticular Chemistry Structure Resource and its authors, M. O'Keeffe, M. A. Peskov, S. J. Ramsden and
  O. M. Yaghi ([Acc. Chem. Res. 41 (2008) 1782–1789](https://doi.org/10.1021/ar800124u)), and the
  researchers who first described each net: every net, vertex orbit and coordinate used here comes from RCSR.
- V. A. Blatov and D. M. Proserpio, Topological relations between three-periodic nets. II. Binodal nets
  ([Acta Cryst. A65 (2009) 202–212](https://doi.org/10.1107/S0108767309006096)): comparing the graphs of
  growing coordination shells, and measuring the largest shell up to which they agree. `r_min` is a
  measurement of this kind.
- S. N. Pozdnyakov and M. Ceriotti, Incompleteness of graph neural networks for points clouds in three
  dimensions ([Mach. Learn.: Sci. Technol. 3 (2022) 045020](https://arxiv.org/abs/2201.07136)): pairs of point
  clouds, including periodic ones, that distance-based WL and GNNs cannot tell apart. Their setting has
  distances; ours has only graph structure.
- Olaf Delgado-Friedrichs's Gavrog, whose space-group table this code reads.

I am grateful to them, and I hope this work adds something new to the field they opened. These
acknowledgements imply no endorsement.

Code: Apache-2.0. Expected values, records and text: CC BY 4.0. Neither applies to RCSR data. See
[LICENSE](LICENSE).
Contact: GitHub Issues at the repository.
