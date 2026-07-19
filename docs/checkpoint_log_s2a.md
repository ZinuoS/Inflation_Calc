# Session 2A checkpoint log — Release calendar + ALFRED vintages (the leakage firewall)

## Pre-build decisions (approved in-session)

1. **naru gap protocol executed.** naru's runner was Excel-only and its raw registry
   lacked (url, retrieved_at). Logged as naru#1–4 in docs/naru_gaps.md.
2. **naru#1 resolved (hybrid, user-approved):** added CSV/TSV source readers to naru
   (branch `feat/csv-tsv-source-reader`, commit 35a2612, local/unpushed; naru suite
   464 green). Delimited sources now load through naru's governed path directly.
   JSON (ALFRED) still normalized to CSV at the edge.
3. **Firewall source (user-approved):** FRED `fred/release/dates` for release dates
   (deterministic, 36y, +future scheduled), release TIME imposed by BLS/BEA 08:30 ET
   convention with a documented override table; not the BLS/BEA HTML archives.
4. **Provenance shim (naru#2):** edge fetcher writes provenance.json (url REDACTED of
   api_key, retrieved_at_utc, sha256, http_status, bytes); a repo-side
   meta_fetch_provenance table will join to naru's raw_files by hash.

## CHECKPOINT 1 — release_calendar (Task 1)  ·  BUILT & LOADED

Reference-period decision (approved): month−1 for CPI/PPI/Employment now; PCE marked
`provisional_pending_vintage`; timebase.py reassigns all reference_periods from ALFRED
first-release vintages in Task 2–3.

**Built:** edge fetcher (`fetch.py`), naru artifact (`v1/`, source_format: csv),
loaded into `data/db/nowcast.sqlite` (run_id=1, **1691 rows**, all 8 validations PASS,
1691 lineage rows). Provenance shim (`src/nowcast/provenance.py`, naru#2) links every
row → CSV hash → upstream FRED URL + retrieval time (custody chain verified).
Offline tests green (`tests/test_release_calendar.py`).

Rows per print in DB: CPI 442, Employment 443, PPI 441, PCE 365 (PCE lower = month-1
gaps/collisions collapsed; corrected via vintages in Task 3). Ref range 1989-12 → 2026-11.

**Time spot-check (done):** BLS CPI schedule page confirms **08:30 AM ET** for 3 recent
prints (Dec-18-2025, Jan-13-2026, Feb-13-2026); matches the imposed convention exactly.
Evidence saved to data/raw/.../bls_cpi_schedule_spotcheck.html. Override table stays empty.

### Original CHECKPOINT 1 detail (retained)

Fetched 2026-07-19, raw JSON + provenance in
`data/raw/release_calendar/2026-07-19/` (gitignored; provenance.json has redacted URLs).

### Coverage (fred/release/dates, realtime 1990-01-01 → 9999-12-31)

| print | raw dates | range | future scheduled |
|---|---|---|---|
| CPI | 463 | 1990-01-18 → 2026-12-10 | 5 |
| PPI | 463 | 1990-01-12 → 2026-12-15 | 5 |
| Employment Situation | 451 | 1990-01-05 → 2026-12-04 | 5 |
| PCE (Personal Income & Outlays) | 456 | 1990-01-29 → 2026-12-23 | 6 |

Far exceeds the ≥10y target (36 years).

### Reference-period mapping — the finding that needs your call

Reference period assigned as release_month − 1 (monthly prints, ~1-month lag),
earliest-date-wins on collision, all collisions/gaps logged to `exceptions.json`.

- **CPI / PPI / Employment: clean.** Collisions (CPI 21, PPI 19, Emp 8) are the annual
  February seasonal-factor re-releases — earliest-wins keeps the true first release.
  Gaps (CPI 2, PPI 3, Emp 1) are **real schedule anomalies, correctly caught**: the
  1995-96 and 2025 U.S. government shutdowns (e.g., CPI Oct-2025 missing, Dec-1995
  delayed). These are logged, not smoothed — exactly per doctrine.
- **PCE: month−1 arithmetic is unreliable (82 collisions, 79 gaps).** BEA P&O releases
  land at month-end and frequently slip across the calendar boundary to the 1st–3rd,
  so a fixed offset misassigns ~18% of months. Plus the 2018-19 shutdown catch-up
  (two March-2019 releases). The release DATES are correct; only the reference-month
  *assignment by arithmetic* is fragile.

**Decision needed** (see chat): how to assign PCE (and generally) reference_period —
authoritative correction from ALFRED first-release vintages (Task 2), a self-contained
sequential heuristic, or reverse the task order. release_calendar's firewall value
(release datetime per date) is solid regardless; only the reference_period join is at issue.

### Release time
Imposed 08:30 ET for all rows (release_time_basis = convention_0830ET); override table
empty pending spot-check. Spot-check vs BLS for 3 recent prints to be done before freeze.

### Not yet built (blocked on the decision) — NOW BUILT (see above)
naru artifact (v1/), the load into nowcast.sqlite, meta_fetch_provenance table,
golden fixture, validations (one-per-print-per-ref-month; CPI precedes PCE).

## CHECKPOINT 2 — alfred_vintages (Task 2)  ·  BUILT & LOADED

Scope (approved): targets + major CPI components. **19 series**, ALFRED full realtime
span. Data finding: raw BLS major-group ids (CUSR0000SAF …) are NOT archived in ALFRED;
used FRED alias ids (CPIFABSL, CPIHOSSL, …), with `mapping_series_id` carrying the
crosswalk back to mapping.yaml.

**Loaded:** `observations` table, run_id=2, **47,945 vintage rows** (blank "." obs
dropped at edge), all validations PASS. Key (series_id, reference_period,
observed_asof_vintage) — distinct value per vintage, none supersedes another.
Views `first_release` (14,380 rows) + `latest_value` materialized by
`src/nowcast/views.py` (+ an index on the natural key; the correlated view query is
O(n²) without it). Provenance recorded (19 rows). Golden test passes; offline view
tests green (`tests/test_views.py`). Full suite 25 green.

### Vintage counts per series (rows / reference range)
CPIAUCSL 3360 (1947–2026), CPILFESL 2258 (1957–), PPIFIS 792 (2009-11–, PPI-FD start),
PCEPI 8637 · PCEPILFE 8675 (1959–, **monthly-revised → deep vintage history**),
CPIFABSL 1703, CPIHOSSL 1713, CPIAPPSL 1948, CPITRNSL 1973, CPIMEDSL 1967,
CPIRECSL 1473 (1993–), CPIEDUSL 1377 (1993–), CPIOGSSL 1578, CPIUFDSL 2534,
CPIENGSL 2685, CUSR0000SAH1 1773 (shelter), CUSR0000SEHA 1438 (rent), SETA01 1780,
SETA02 1695 (used cars).

### Spot-check: first release vs latest (6 known revision episodes)
| series | ref | first (vintage) | latest (vintage) | rev |
|---|---|---|---|---|
| CPIAUCSL | 2020-01 | 258.820 @2020-02-13 | 259.127 @2025-02-12 | +0.307 |
| CPIAUCSL | 2022-06 | 295.328 @2022-07-13 | 294.957 @2026-02-13 | −0.371 |
| CPILFESL | 2021-06 | 278.140 @2021-07-13 | 277.651 @2026-02-13 | −0.489 |
| CUSR0000SETA02 | 2021-06 | 197.227 @2021-07-13 | 194.846 @2024-02-09 | −2.381 |
| PCEPILFE | 2021-06 | 117.275 @2021-07-30 | 108.603 @2025-09-26 | −8.672* |
| PCEPILFE | 2025-01 | 124.334 @2025-02-28 | 124.587 @2025-09-26 | +0.253 |

\*PCE level shift is a BEA re-referencing (base-year change), not a data error; MoM
surprises (our target) are base-invariant. **Every first_release_vintage matches the
release_calendar release date** — the firewall cross-validates (CPI 2020-01 → 2020-02-13;
PCE 2021-06 → 2021-07-30).

### Not yet built (Task 3, next)
`src/nowcast/timebase.py` — `asof(series_id, forecast_time)` joining release_calendar +
first_release, with the adversarial leakage test (reading between reference-period end
and release_datetime must return the PRIOR print). Also: authoritative PCE
reference_period reassignment from first-release vintage dates.

## Task 3 — timebase.py + Checkpoint-2 fixes

### TASK 0 — vintage-safe MoM (first_release_mom)  ·  CHECKPOINT 1 APPROVED

Built `first_release_mom` (canonical MoM target): within-vintage rule — for reference
month t, both level_t and level_{t-1} are read from the single vintage published at
t's first release (the row whose inclusive window [observed_asof_vintage, vintage_end]
contains t's first-release vintage). `first_release` (levels) demoted to DIAGNOSTIC with
a docstring warning; it stays the source of first-release *vintage dates*. 14,346 MoM rows.

Both mandatory tests green (`tests/test_vintage_mom.py`):
- (a) synthetic 2× re-referencing: within-vintage MoM stays +1.000%/month; naive
  cross-vintage differencing fabricates −49.5% at the re-referenced month.
- (b) real: PCEPILFE and CPI SA MoM continuous through their events (no |MoM|>1%).

MoM series around both events (within-vintage vs naive):

PCEPILFE (BEA re-referencing at vintage 2023-09-29 → hits ref 2023-08):
| ref | within-vintage | naive | note |
|---|---|---|---|
| 2023-06 | +0.165% | +0.132% | |
| 2023-07 | +0.216% | +0.209% | |
| 2023-08 | **+0.145%** | **−6.966%** | naive artifact; within-vintage clean |
| 2023-09 | +0.299% | +0.266% | |

CPIAUCSL (February seasonal-factor restatement → hits Jan ref):
| ref | within-vintage | naive |
|---|---|---|
| 2023-12 | +0.303% | +0.303% |
| 2024-01 | **+0.305%** | +0.270% (3.5bp leak) |
| 2024-02 | +0.442% | +0.442% |

### Amendment A.1 — omission audit: premise corrected (FLAG)

Checkpoint-1 review assumed the 34 first_release_mom omissions were "one per series at
its minimum reference period." **That premise is off by 15.** The real, all-principled
decomposition (asserted by `test_first_release_mom_omissions_are_all_principled`, which
fails on ANY omission outside these categories):

- **19 series-start** (one per series, no t-1) — as assumed;
- **14 reference gaps** — t-1 was never released: the **2025 government shutdown** dropped
  2025-10 for most CPI series, so 2025-11 has no MoM. (Used-cars/new-vehicles were
  released in Oct-2025, so they are exempt — a nice internal consistency check.)
- **1 vintage discontinuity** — CPIAUCSL 1970-12, whose earliest ALFRED vintage (1972-07-21,
  value 119.03 on the old 1957-59=100 base) shares no vintage window with 1970-11.
  Omitting is correct: no common base to difference across.

19 + 14 + 1 = 34. Every omission is principled; none is a silent bug. The test asserts
the *principle* (categorised, series-start count == n_series), not the magic number, so
it stays valid when the DB is rebuilt with post-shutdown data.

### Amendment B — vintage leakage magnitude: why latest-vintage backtests overstate skill

The within-vintage vs naive gap is not academic; it is a direct measure of how much a
naive (latest-vintage) backtest would cheat:

- **PCE re-referencing (ref 2023-08): 711 bp.** Naive cross-vintage MoM = −6.966% vs
  within-vintage +0.145%. A latest-vintage backtest would "predict" a catastrophic
  print that never happened — pure look-ahead from the 2023 BEA base change.
- **CPI February seasonal restatement (ref 2024-01): 3.5 bp.** Within-vintage +0.305%
  vs naive +0.270%. Small per month, but it recurs every February across the whole
  sample and always in the direction of the revision, so a latest-vintage backtest
  gets a systematic, free "edge" from knowing the future seasonal factors.

Both are leakage a latest-vintage target would silently grant. `docs/sa_floor.md`
(Session 3A) will cite the 3.5 bp figure as part of the achievable-accuracy floor.

### TASK 1–3 — timebase.py + adversarial/crosswalk tests  ·  DONE

- **`src/nowcast/timebase.py`** — the only sanctioned read path. `asof(series_id, ft)`,
  `asof_mom(series_id, ft)`, `asof_mom_for_ref(series_id, ref, ft)` with `NotYetReleased`
  / `NoMomExists` / `UnknownSeries`. Observable datetime = first-release vintage date @
  release time (release_calendar join for the time, 08:30 ET convention fallback);
  strictly-before semantics. Crosswalk resolves mapping.yaml ids ↔ ALFRED alias ids.
  PCE reference periods come from the vintages, never release_calendar's provisional
  month-1 assignment.
- **`tests/test_timebase.py`** (adversarial, Task 2 + Amendment C): for every print type,
  a forecast_time between reference-period end and release returns the PRIOR print for
  asof/asof_mom and raises NotYetReleased for asof_mom_for_ref; exact-release-instant is
  strictly-before → prior; series-start → NoMomExists (asof_mom_for_ref) / skipped
  (asof_mom); 50-pair random property sweep asserts asof never leaks a
  not-yet-released value and always returns the latest observable. **If this file ever
  fails, the backtest is invalid.**
- **`tests/test_crosswalk.py`** (Task 3): FRED-alias latest values vs BLS-official series
  (BLS public API — the authoritative source; the raw CU ids are not in FRED) match to
  0.01 index points over trailing 3 years. Current max|diff| = 0.0. Fails loudly by pair.

### TASK 4 — housekeeping · DONE

- **naru pinned** to exact commit `35a26120db5db7c06e8e7e4d7238d9a2b5211311` via a git
  source in pyproject (non-editable, side-stepping naru#5). **ACTION FOR ASH: push the
  naru branch `feat/csv-tsv-source-reader`; once on GitHub, swap the source URL from
  file:// to the GitHub remote (same rev).**
- **SQLite lock hang diagnosed** (not just worked around) — root cause = default
  busy_timeout 0 + rollback-journal mode + a killed background process holding the lock;
  naru closes its own connections so it's not leaking, but is fragile under concurrency.
  Written up as **naru#6** (desired: WAL + busy_timeout + context-managed sessions).
  Minimal marked shim applied: `src/nowcast/db.connect()` (WAL + busy_timeout + always
  closes); timebase/views/provenance all route through it; WAL now persistent on the DB.

### Definition of done
pytest green (38, incl. adversarial + synthetic re-referencing + delta audit + crosswalk);
first_release_mom documented as the canonical MoM target; crosswalk test in the suite;
naru pinned; lock diagnosis written. No open questions blocking Session 2B.

## Environment notes (this session)
- naru consumed **non-editable** (naru#5 shadow bug). After naru changes:
  `uv sync --reinstall-package naru-data`; if nowcast import breaks, `uv sync --reinstall`.
- For nowcast-importing scripts, `PYTHONPATH=src .venv/bin/python` is the reliable
  invocation (uv's editable .pth for nowcast is flaky, and `uv run` auto-sync can hang
  holding the DB lock). naru CLI (`uv run naru …`) is fine.
