# Verification record: periodic-net-wl-tests 1.0.0

Who computed and checked what, and when. Dates are 2026, JST (UTC+9). All work was done by the author with AI
systems in separate sessions; "team" below means a separate group of AI sessions with its own instructions.
No human expert review has taken place.

## 1. Input

RCSR-content commit `580316c9352b747f5c309a93acd21a3a2b4034a3`, file `public/data/3dall.txt` (4,547,394 bytes,
SHA-256 `c143e8aa…2743`), and for the optional tier `public/downloads/RCSRnets.arc` (1,754,079 bytes,
SHA-256 `8a18b5c2…6ebd6f`). The full hashes are in `source_io.py`. The repository at that commit has no licence
file, its README states no terms, and the RCSR About page states none for the data; the files are therefore
fetched by the user and not included here.

## 2. Earlier computations (23 October)

The research team built rooted balls for pairs of RCSR roots with equal 10-shell coordination sequences and
recorded `r_min` and `r_WL` with certificates. The 99 cases of `expected.json` are the rows of that table with
an exact `r_WL` larger than `r_min` (97) and two core cases with `r_WL` = `r_min`. Four pairs with
`r_WL` > 8 and all pairs without a decided `r_min` are not included.

## 3. Independent check of the core cases (23 October)

A separate verification team recomputed the core pairs from the same pinned `3dall.txt` with its own code
(Gemmi 0.7.5, NetworkX 3.7 VF2++, Python standard library). It did not read the research team's code, results
or expected values. It did read the research setup's description of the coordinate handling and of the 1-WL
initial colours.

| Pair | Research `r_min` / `r_WL` | Independent `r_min` / `r_WL` |
|---|---|---|
| sxb V1 / sxc V1 | 2 / 2 | 2 / 2 |
| fly V2 / ylf V2 | 4 / 4 | 4 / 4 |
| fly V1 / ylf V1 | 4 / 5 | 4 / 5 |
| ben V2 / cat V2 | 3 / 6 | 3 / 6 |
| tsa V1 / tsg V3 | 4 / 8 | 4 / 8 |
| acl V1 / nih V1 | 1 / 2 | 1 / 2 |

- For fly V1 / ylf V1 at radius 4, both sides found trace(A^10) of the two balls (closed walks of length 10,
  summed over all vertices of the ball) to be 2,816,008 and 2,816,168, and both found that 1-WL does not separate the balls (independent side: a common
  stable partition with 27 cells).
- The research team had built tsa/tsg from the ARC file. The independent team built it from the rounded
  coordinates, restoring special positions to 1/3 and 2/3, and checked it with two edge-finding methods.
- The independent 1-WL starts with only the root coloured. For ben/cat, tsa/tsg and acl/nih it was also run
  with the research initial colours (distance, degree); the stable result agreed at every radius.
- The independent team also checked all nine root pairs of equal degree for ben/cat, tsa/tsg and acl/nih.

This check covers the six core cases only.

## 4. This package (23 October)

The suite code in this repository was assembled from the research team's generator and checker. The checker
(`verify_run.py`, `source_check.py`, `core_check.py`, `finite_check.py`) does not import the generator
(`build_run.py`, `geometry.py`, `refutation.py`, `algorithm.py`), but both were written by the research team
and share `source_io.py` (input handling, record parser, source-model definitions). The order of source
models (printed decimals, then denominators 12 and 48) was fixed before any radius was compared.

Runs from a fresh clone of the first commit of this repository, on macOS (Apple silicon), Python 3.14, each
in a new empty work folder with the input downloaded from the pinned URL:

| Command | Result | Time (s) | Peak RSS (MB) |
|---|---|---:|---:|
| `check_claims.py` | PASS | <1 | – |
| `suite.py run --scope core` | 6 cases PASS, 10 nets PASS | 0.60 | 63 |
| `suite.py run --scope main` | 76 cases PASS, 65 nets PASS | 19.7 | 65 |
| `suite.py run --scope all --with-arc` | 99 cases PASS, 97 nets PASS (84 from coordinates, 13 from the ARC file) | 22.9 | 79 |
| `selftest.py` | 15 tests PASS | 22 | – |

Times are `elapsed_seconds` from `run-summary-run.json`; the self-test time is wall-clock. The core scope
also passed under Python 3.11 and 3.12 (working tree before the first commit).

## 5. Review of this text

README.md and claims.json were read by a fresh AI reader (Codex, read-only, no prior context) for claims
not supported by the evidence and for phrasing. Its points were applied in the second commit: the
coordination-sequence selection is stated as 10 shells; edge construction, coordinate rounding and the ARC
root choice are described as the code does them; the walk counts are stated as trace(A^10); the shared code
between generator and checker is named correctly; exit codes for size caps and the self-test composition are
corrected; the limits of the prior-work search are stated.
