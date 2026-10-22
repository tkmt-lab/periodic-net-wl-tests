# Entry point for a computational reader

Read README.md (definitions, scopes, what is not claimed), claims.json and VERIFICATION-RECORD.md.

What the repository holds: code (Python standard library) and expected values (`expected.json`). It holds no
RCSR data. `suite.py run` downloads `3dall.txt` from a pinned RCSR-content commit, checks its SHA-256, builds
periodic graphs and certificates in the `--work` folder, and checks them.

Commands (macOS or Linux, Python 3.11+, never `python -O`; each `--work` folder must be new):
- `python3 -B suite.py run --work work/core --scope core` (about 1 s after the download): 6 cases.
- `python3 -B suite.py run --work work/main --scope main` (about 20 s): 76 cases. This is what CI runs.
- `python3 -B suite.py run --work work/all --scope all --with-arc` (about 25 s): 99 cases; also downloads RCSRnets.arc.
- `python3 -B selftest.py --verified-work work/core --out work/selftest` (about 25 s, needs network): 15 rejection tests.
- `python3 -B check_claims.py` (instant): claims.json fields and hashes.
- Add `--source /path/to/3dall.txt` to `run` to work offline from a copy you already have.

Reading the output: `WORK/verification.json` has `status` (`PASS`, `FAIL`, `UNVERIFIED`), `case_counts`, and per
case `r_min`, `r_WL`, `delay` (= `r_WL - r_min`) and the kind of non-isomorphism certificate. Exit code 0 means every
case passed; 1 a mismatch; 2 bad input or hash; 3 undecided (counted as not passed); 4 download error.

Terms: a case is a pair (net, vertex orbit) vs (net, vertex orbit), e.g. `1790-V1__2089-V3` = tsa V1 vs tsg V3
(RCSR record numbers). A ball is the subgraph induced by all vertices within r edges of the root. `r_min` is the
first radius with non-isomorphic balls; `r_WL` the first radius at which stable 1-WL, started from (distance
from root, degree in ball), gives different colour counts.

Do not infer:
- anything about GNNs in general, or about models that use species, coordinates, distances or angles;
- that a radius, or `r_WL - r_min`, is a number of message-passing layers or WL rounds;
- a maximum over the RCSR database (the 99 cases are a selection);
- independent checking beyond the six core cases;
- that the graphs are the geometry intended by RCSR, or that RCSR data may be redistributed;
- human review, formal proof, priority or endorsement by the cited authors.
