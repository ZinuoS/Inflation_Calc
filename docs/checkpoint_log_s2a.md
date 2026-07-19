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

## Environment notes (this session)
- naru consumed **non-editable** (naru#5 shadow bug). After naru changes:
  `uv sync --reinstall-package naru-data`; if nowcast import breaks, `uv sync --reinstall`.
- For nowcast-importing scripts, `PYTHONPATH=src .venv/bin/python` is the reliable
  invocation (uv's editable .pth for nowcast is flaky, and `uv run` auto-sync can hang
  holding the DB lock). naru CLI (`uv run naru …`) is fine.
